"""
Tracking Engine

Coordinates object detection, motion tracking, and PTZ camera control for
automated subject tracking. Main orchestration layer that brings all components together.

Example:
    from src.automation.tracking_engine import TrackingEngine
    
    engine = TrackingEngine(
        detector=detector,
        motion_tracker=motion_tracker,
        ptz_controller=ptz_controller,
        stream_handler=stream_handler,
        config=config
    )
    
    engine.start()  # Begin automated tracking
"""

import cv2
import logging
import time
import threading
from typing import Optional, Dict, List, Callable
from dataclasses import dataclass, field
from enum import Enum

from src.ai.object_detector import ObjectDetector, DetectionResult
from src.ai.motion_tracker import MotionTracker, Direction, TrackInfo
from src.camera.ptz_controller import PTZController
from src.video.stream_handler import VideoStreamHandler


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TrackingMode(Enum):
    """Tracking modes"""
    CENTER = "center"       # Center-based tracking (current default)
    QUADRANT = "quadrant"   # Multi-zone quadrant-based tracking
    AUTO = "auto"           # Fully automated tracking (legacy)
    MANUAL = "manual"       # Manual control only
    ASSISTED = "assisted"   # Auto tracking with manual override


@dataclass
class TrackingZone:
    """
    Defines a zone in the camera's field of view
    
    Attributes:
        name: Zone identifier (e.g., 'zone_left', 'zone_center')
        x_range: (min, max) as fraction of frame width (0.0 to 1.0)
        y_range: (min, max) as fraction of frame height (0.0 to 1.0)
        preset_token: PTZ preset to activate for this zone
        priority: Priority level (higher = more important)
    """
    name: str
    x_range: tuple[float, float]
    y_range: tuple[float, float]
    preset_token: str
    priority: int = 0


@dataclass
class TrackingConfig:
    """
    Configuration for tracking engine
    
    Attributes:
        zones: List of tracking zones
        target_classes: Object classes to track (e.g., ['person', 'car'])
        direction_triggers: Directions that trigger tracking
        min_confidence: Minimum detection confidence
        movement_threshold: Minimum movement to trigger action (pixels)
        cooldown_time: Seconds between PTZ movements
        max_tracking_age: Max seconds to track object without detection
        enable_recording: Whether to record tracked events
        home_preset: Preset to return to when inactive (e.g., 'Preset004')
        inactivity_timeout: Seconds before returning to home position
        quadrant_tracking: Configuration for quadrant-based tracking
    """
    zones: List[TrackingZone] = field(default_factory=list)
    target_classes: List[str] = field(default_factory=lambda: ['person'])
    direction_triggers: List[Direction] = field(default_factory=lambda: [Direction.RIGHT_TO_LEFT])
    min_confidence: float = 0.6
    movement_threshold: int = 50
    cooldown_time: float = 3.0
    max_tracking_age: float = 2.0
    enable_recording: bool = False
    home_preset: str = "Preset004"
    inactivity_timeout: float = 5.0
    quadrant_tracking: Dict = field(default_factory=dict)

@dataclass
class TrackingEvent:
    """
    Represents a tracking event (subject detected and tracked)
    
    Attributes:
        event_id: Unique event identifier
        object_id: Tracked object ID
        class_name: Object class (person, car, etc.)
        direction: Movement direction
        start_time: Event start timestamp
        end_time: Event end timestamp (None if ongoing)
        zone_transitions: List of zones object moved through
        ptz_actions: List of PTZ preset changes triggered
        frame_count: Number of frames tracked
    """
    event_id: str
    object_id: str
    class_name: str
    direction: Direction
    start_time: float
    end_time: Optional[float] = None
    zone_transitions: List[str] = field(default_factory=list)
    ptz_actions: List[str] = field(default_factory=list)
    frame_count: int = 0


class TrackingEngine:
    """
    Main tracking engine coordinating detection, tracking, and PTZ control
    
    Orchestrates the entire automated tracking workflow:
    1. Read frame from video stream
    2. Detect objects using AI
    3. Track object motion and direction
    4. Determine appropriate camera action
    5. Execute PTZ movement to follow subject
    """
    
    def __init__(
        self,
        detector: ObjectDetector,
        motion_tracker: MotionTracker,
        ptz_controller: PTZController,
        stream_handler: VideoStreamHandler,
        config: TrackingConfig
    ):
        """
        Initialize tracking engine
        
        Args:
            detector: Object detector instance
            motion_tracker: Motion tracker instance
            ptz_controller: PTZ camera controller
            stream_handler: Video stream handler
            config: Tracking configuration
        """
        self.detector = detector
        self.motion_tracker = motion_tracker
        self.ptz = ptz_controller
        self.stream = stream_handler
        self.config = config
        
        # State
        self.running = False
        self.paused = False
        self.mode = TrackingMode.AUTO
        self.thread: Optional[threading.Thread] = None
        
        # Tracking state
        self.current_preset: Optional[str] = None
        self.last_ptz_time: float = 0.0
        self.last_movement_time: float = 0.0  # Track inactivity for home return
        self.home_preset: str = config.home_preset  # Load from config (e.g., Preset003)
        self.idle_preset_override: Optional[str] = None  # UI dropdown can override home preset at idle time
        self.inactivity_timeout: float = config.inactivity_timeout  # Load from config
        self.active_events: Dict[str, TrackingEvent] = {}
        self.completed_events: List[TrackingEvent] = []
        self.event_counter = 0
        
        # Centroid-based object tracking (to assign stable IDs)
        self.next_object_id = 0
        self.object_centroids: Dict[int, tuple[int, int]] = {}  # object_id -> (x, y)
        self.max_centroid_distance = 50  # pixels - max distance to associate same object
        self.centroid_max_age = 30  # frames before removing inactive track
        self.centroid_ages: Dict[int, int] = {}  # Track age in frames
        
        # Statistics
        self.frame_count = 0
        self.detection_count = 0
        self.tracking_count = 0
        self.ptz_movement_count = 0
        self.zoom_frame_counter = 0  # Skip zoom every other frame
        self.last_bbox_area = None  # Track previous frame's bbox area for distance trend
        
        # ⭐ QUADRANT TRACKING: Multi-zone tracking with preset switching
        self.quadrant_mode_enabled = False  # Toggle between center and quadrant tracking
        self.current_quadrant: Optional[str] = None  # Track which quadrant subject is in
        self.quadrant_config = config.quadrant_tracking  # Load from tracking_rules.yaml
        self.quadrant_zoom_counter = 0  # Track zoom application per quadrant entry
        
        # ⭐ ASYNC DETECTION: Run detection in background to prevent blocking
        # Detection runs on separate thread and caches results
        self.detection_thread: Optional[threading.Thread] = None
        self.detection_stop = False
        self.pending_detection_frame: Optional[cv2.Mat] = None
        self.pending_frame_lock = threading.Lock()
        self.last_detection_results = []
        self.detection_results_lock = threading.Lock()
        
        # Cache recent detections for web overlay (no latency)
        self.last_detections = []
        self.overlay_detection_frame_skip = 0  # Counter for detection sampling
        self.overlay_detection_interval = 5  # Run detection every N frames (for web overlay only)
        
        # Callbacks
        self.on_detection: Optional[Callable] = None
        self.on_tracking: Optional[Callable] = None
        self.on_ptz_move: Optional[Callable] = None
        
        logger.info("TrackingEngine initialized")
    
    def start(self) -> None:
        """Start automated tracking in background thread"""
        if self.running:
            logger.warning("Tracking engine already running")
            return
        
        logger.info("Starting tracking engine...")
        
        self.running = True
        self.paused = False
        self.detection_stop = False
        self.last_movement_time = time.time()  # Initialize inactivity timer
        
        # Start main tracking thread
        self.thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self.thread.start()
        
        # ⭐ Start async detection thread (runs on separate CPU core)
        # Prevents YOLOv8 detection from blocking frame processing
        self.detection_thread = threading.Thread(target=self._detection_worker, daemon=True)
        self.detection_thread.start()
        
        logger.info("✓ Tracking engine started (with async detection)")
    
    def stop(self) -> None:
        """Stop automated tracking"""
        if not self.running:
            return
        
        logger.info("Stopping tracking engine...")
        
        self.running = False
        self.detection_stop = True
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5.0)
        
        if self.detection_thread and self.detection_thread.is_alive():
            self.detection_thread.join(timeout=5.0)
        
        # Close any active events
        for event in self.active_events.values():
            event.end_time = time.time()
            self.completed_events.append(event)
        
        self.active_events.clear()
        
        logger.info("✓ Tracking engine stopped")
    
    def pause(self) -> None:
        """Pause tracking (keep running but don't process frames)"""
        self.paused = True
        logger.info("Tracking paused")
    
    def resume(self) -> None:
        """Resume tracking"""
        self.paused = False
        logger.info("Tracking resumed")
    
    def _tracking_loop(self) -> None:
        """Main tracking loop (runs in background thread)"""
        logger.info("Entering tracking loop...")
        
        while self.running:
            try:
                if self.paused:
                    time.sleep(0.1)
                    continue
                
                # Read frame from stream
                frame = self.stream.read(timeout=1.0)
                
                if frame is None:
                    logger.warning("No frame available from stream")
                    continue
                
                self.frame_count += 1
                
                # Process frame
                self._process_frame(frame)
                
            except Exception as e:
                logger.error(f"Error in tracking loop: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(0.1)
        
        logger.info("Exiting tracking loop")
    
    def _detection_worker(self) -> None:
        """
        ⭐ ASYNC DETECTION THREAD
        
        Runs continuously in background, performing expensive YOLOv8 detection
        on frames submitted by main tracking loop. This prevents detection from
        blocking frame processing and video streaming.
        
        Main loop: Acquire pending frame → Run detection → Cache results → Ready
        """
        logger.info("Detection worker started")
        detection_count = 0
        
        while not self.detection_stop:
            try:
                # Check if there's a frame waiting for detection
                with self.pending_frame_lock:
                    if self.pending_detection_frame is None:
                        # No frame waiting, wait a bit before checking again
                        time.sleep(0.001)
                        continue
                    
                    # Get the frame
                    detection_frame = self.pending_detection_frame.copy()
                    self.pending_detection_frame = None  # Mark frame as consumed
                
                # ⭐ RUN EXPENSIVE DETECTION (this takes 50-100ms)
                # But it runs on SEPARATE THREAD, so main loop doesn't block
                detections = self.detector.detect(detection_frame)
                
                # Filter by target classes and confidence
                detections = [
                    d for d in detections
                    if d.class_name in self.config.target_classes
                    and d.confidence >= self.config.min_confidence
                ]
                
                # Cache results for main loop to use
                with self.detection_results_lock:
                    self.last_detection_results = detections
                    detection_count += len(detections)
                    
                    # Debug log every 10 detections
                    if detection_count % 10 == 0:
                        logger.debug(f"[DETECTION_WORKER] Processed {detection_count} total detections, cached {len(detections)} for frame")
                    
            except Exception as e:
                logger.error(f"Error in detection worker: {e}")
                time.sleep(0.1)
        
        logger.info("Detection worker stopped")
    
    def _assign_object_ids(self, detections: List[DetectionResult]) -> List[tuple[int, DetectionResult]]:
        """
        Assign stable object IDs to detections using centroid tracking
        
        Uses distance-based association to match detections with existing object centroids.
        This ensures consistent IDs across frames for the same physical object.
        
        Args:
            detections: List of detected objects
            
        Returns:
            List of (object_id, detection) tuples
        """
        import math
        
        if not detections:
            # Age out old tracks
            to_remove = [oid for oid in self.centroid_ages if self.centroid_ages[oid] > self.centroid_max_age]
            for oid in to_remove:
                if oid in self.object_centroids:
                    del self.object_centroids[oid]
                del self.centroid_ages[oid]
            return []
        
        # Age all existing tracks
        for oid in self.centroid_ages:
            self.centroid_ages[oid] += 1
        
        assignments = []  # List of (object_id, detection)
        used_ids = set()  # Track which existing IDs were matched
        
        # Try to match each detection to existing centroids
        for detection in detections:
            det_x, det_y = detection.center
            best_id = None
            best_dist = self.max_centroid_distance
            
            # Find closest centroid
            for oid, (cx, cy) in self.object_centroids.items():
                if oid in used_ids:  # Already matched to another detection
                    continue
                    
                dist = math.sqrt((det_x - cx)**2 + (det_y - cy)**2)
                
                if dist < best_dist:
                    best_dist = dist
                    best_id = oid
            
            if best_id is not None:
                # Found a matching track
                self.object_centroids[best_id] = (det_x, det_y)
                self.centroid_ages[best_id] = 0  # Reset age
                used_ids.add(best_id)
                assignments.append((best_id, detection))
            else:
                # Create new track
                new_id = self.next_object_id
                self.next_object_id += 1
                self.object_centroids[new_id] = (det_x, det_y)
                self.centroid_ages[new_id] = 0
                used_ids.add(new_id)
                assignments.append((new_id, detection))
        
        return assignments
    
    def _process_frame(self, frame) -> None:
        """
        Process single frame through detection, tracking, and PTZ control pipeline
        
        Args:
            frame: OpenCV BGR image
        """
        current_time = time.time()
        
        # ⭐ OPTIMIZATION: Frame skipping for detection
        # Run detection every 3rd frame to reduce CPU usage by 40-50%
        # Added latency: ~200ms (imperceptible at 15 FPS display rate)
        # Trade-off: CPU optimization outweighs minimal lag increase
        detection_skip_interval = 3  # Process every 3rd frame (was 1 = every frame)
        
        frame_height, frame_width = frame.shape[:2]
        
        # Only submit detection frames every Nth frame
        if self.frame_count % detection_skip_interval == 0:
            # ⭐ OPTIMIZATION: Downsample frame for detection to save CPU
            if frame_width > 1280:
                scale_factor = 1280 / frame_width
                detection_frame = cv2.resize(frame, (int(frame_width * scale_factor), int(frame_height * scale_factor)), interpolation=cv2.INTER_LINEAR)
            else:
                detection_frame = frame
            
            # ⭐ Submit frame to async detection worker (NON-BLOCKING)
            # Detection runs on separate thread, main loop continues immediately
            with self.pending_frame_lock:
                self.pending_detection_frame = detection_frame.copy()
        
        # Use latest cached detection results (from detection worker)
        with self.detection_results_lock:
            detections = self.last_detection_results.copy() if self.last_detection_results else []
        
        # ⭐ Cache detections for web overlay - CRITICAL FIX
        # IMPORTANT: Clear detections immediately when none are detected to prevent lag
        # Previously kept old detections which caused bounding boxes to remain after subject left
        if detections:
            self.last_detections = detections
            logger.debug(f"[CACHE] Cached {len(detections)} detections for overlay API")
        else:
            # CRITICAL: Clear stale detections immediately to prevent visual lag
            if self.last_detections:
                logger.debug(f"[CACHE] Clearing {len(self.last_detections)} stale detections (no new detections)")
            self.last_detections = []
        
        self.detection_count += len(detections)
        
        if self.on_detection:
            self.on_detection(detections)
        
        if not detections:
            # No detections - check if we should return to home position
            self._check_inactivity_and_return_home(current_time)
            return
        
        # Step 2: Assign stable object IDs using centroid tracking
        tracked_detections = self._assign_object_ids(detections)
        
        if not tracked_detections:
            return
        
        # Step 3: Update motion tracking
        for object_id, detection in tracked_detections:
            # Update motion tracker with stable object ID (convert to string)
            object_id_str = str(object_id)
            direction = self.motion_tracker.update(
                object_id=object_id_str,
                center=detection.center,
                timestamp=current_time
            )
            
            # Get track info
            track_info = self.motion_tracker.get_track_info(object_id_str)
            
            if track_info is None:
                continue
            
            self.tracking_count += 1
            
            if self.on_tracking:
                self.on_tracking(track_info)
            
            # Step 3: Check if tracking should trigger action
            if self._should_trigger_tracking(detection, direction, track_info):
                self._handle_tracking_action(detection, direction, track_info, frame)
                self.last_movement_time = current_time  # Update last movement time
    def _check_inactivity_and_return_home(self, current_time: float) -> None:
        """
        Check if camera has been inactive and return to home position
        
        Idle behavior:
        1. Check if idle_preset_override is set (user selected from dropdown)
        2. If yes, use the override (what user selected)
        3. If no override, use the default home_preset from config
        
        Args:
            current_time: Current timestamp
        """
        # Determine which preset to use at idle time
        # PRIORITY: Override (if set) > Config default
        if self.idle_preset_override:
            preset_to_use = self.idle_preset_override
            print(f"⭐ [IDLE] Using dropdown override: {preset_to_use}")
        else:
            preset_to_use = self.home_preset  # Default: config value
            print(f"⭐ [IDLE] Using config home preset: {preset_to_use}")
        
        if not preset_to_use:
            return
        
        # If no movement in the timeout period, return home
        time_since_last_move = current_time - self.last_movement_time
        
        if time_since_last_move >= self.inactivity_timeout:
            # Allow idle return if:
            # 1. We're moving to a DIFFERENT preset than current (always allow)
            # 2. OR it's been 1+ second since last PTZ command (prevent hammering same preset)
            time_since_last_ptz = current_time - self.last_ptz_time
            
            should_move = (preset_to_use != self.current_preset) or (time_since_last_ptz > 1.0)
            
            if should_move:
                try:
                    # ⭐ DIAGNOSTIC LOG: Home return being triggered
                    print(f"⭐ [HOME RETURN] Inactivity timeout ({time_since_last_move:.1f}s >= {self.inactivity_timeout}s)")
                    print(f"⭐ [HOME RETURN] Current: {self.current_preset}, Moving to: {preset_to_use}")
                    logger.warning(f"⭐ [HOME RETURN] Inactivity timeout - Moving to preset {preset_to_use}")
                    
                    logger.info(
                        f"No movement for {time_since_last_move:.1f}s - "
                        f"Returning to preset {preset_to_use}"
                    )
                    self.ptz.goto_preset(preset_to_use, speed=0.7)
                    self.current_preset = preset_to_use
                    self.last_ptz_time = current_time
                except Exception as e:
                    logger.error(f"Failed to return to idle preset: {e}")
    
    def _should_trigger_tracking(
        self,
        detection: DetectionResult,
        direction: Direction,
        track_info: TrackInfo
    ) -> bool:
        """
        Determine if tracking action should be triggered
        
        For center-of-frame tracking: Only track MOVING objects (not stationary).
        Ignores stationary objects to save PTZ movements and power.
        
        Args:
            detection: Detection result
            direction: Movement direction
            track_info: Tracking information
            
        Returns:
            True if action should be triggered
        """
        # CRITICAL: Don't track stationary objects - waste of PTZ movements
        if direction == Direction.STATIONARY:
            return False
        
        # Check if object has been tracked long enough (avoid tracking for 1-2 frames)
        if track_info.frames_tracked < 2:
            return False
        
        # Check cooldown to avoid excessive pan commands
        # For center tracking, we want very fast updates (0.05s for responsive centering with walking people)
        center_tracking_cooldown = 0.05  # Ultra-responsive for keeping up with movement
        time_since_last_move = time.time() - self.last_ptz_time
        if time_since_last_move < center_tracking_cooldown:
            return False
        
        return True
    
    def _handle_tracking_action(
        self,
        detection: DetectionResult,
        direction: Direction,
        track_info: TrackInfo,
        frame
    ) -> None:
        """
        Execute tracking action - Fast center-of-frame continuous tracking
        
        Aggressive centering with fast pan/tilt response for quick subject acquisition.
        
        Args:
            detection: Detection result
            direction: Movement direction
            track_info: Tracking information
            frame: Current video frame
        """
        height, width = frame.shape[:2]
        
        # ⭐ QUADRANT TRACKING MODE: Dispatch to quadrant handler if enabled
        if self.quadrant_mode_enabled:
            quadrant = self._get_quadrant_for_position(
                detection.center[0],
                detection.center[1],
                width,
                height
            )
            self._handle_quadrant_tracking_action(detection, quadrant, frame)
            return
        
        # ⭐ CENTER TRACKING MODE: Continue with standard center-of-frame tracking
        frame_center_x = width / 2.0
        frame_center_y = height / 2.0
        
        # ⭐ PREDICTIVE TRACKING: Account for detection lag (conservative)
        # Detection results are 1-2 frames old (async detection takes time).
        # Predict where subject has moved to using velocity from motion tracker.
        subject_x = detection.center[0]
        subject_y = detection.center[1]
        
        # Get velocity from track info and extrapolate forward
        # For distant/low-confidence subjects, reduce prediction to avoid chasing ghosts
        if track_info and hasattr(track_info, 'velocity') and detection.confidence > 0.55:
            # Only apply prediction for medium-high confidence detections
            # Far/small subjects have unreliable velocity estimates
            
            # Scale prediction based on confidence
            # High confidence (0.9): use full prediction
            # Medium confidence (0.55): use reduced prediction
            confidence_factor = min(1.0, (detection.confidence - 0.5) / 0.4)  # 0.55→0, 0.95→1.0
            
            # Prediction: add velocity * frame_lag to current position
            # Use conservative 1 frame (~33ms at 30fps) instead of 2
            frame_lag_seconds = 0.033  # 1 frame at 30fps
            velocity_x, velocity_y = track_info.velocity  # pixels/second
            
            predicted_x = subject_x + (velocity_x * frame_lag_seconds * confidence_factor)
            predicted_y = subject_y + (velocity_y * frame_lag_seconds * confidence_factor)
            
            # Clamp predictions to frame bounds (don't chase outside frame)
            subject_x = max(0, min(width, predicted_x))
            subject_y = max(0, min(height, predicted_y))
            
            logger.debug(
                f"Predictive tracking (conf={detection.confidence:.2f}): detected at ({detection.center[0]:.0f}, {detection.center[1]:.0f}) → "
                f"predicted at ({subject_x:.0f}, {subject_y:.0f}) "
                f"(velocity: {velocity_x:+.1f}, {velocity_y:+.1f} px/s, factor: {confidence_factor:.2f})"
            )
        
        # ========== PAN (Horizontal X-axis) ==========
        # Calculate offset from center (negative = left of center, positive = right)
        offset_pixels_x = subject_x - frame_center_x
        
        # Calculate normalized offset (-1.0 to 1.0, where 0 = centered)
        max_offset_x = width / 2.0
        normalized_offset_x = offset_pixels_x / max_offset_x
        
        # Smaller dead zone for more responsive pan tracking (20px instead of 40px)
        # This ensures subjects near left/right edges trigger pan immediately
        DEAD_ZONE_PIXELS_X = 20  # Reduced from 40px for faster response near edges
        if abs(offset_pixels_x) < DEAD_ZONE_PIXELS_X:
            pan_velocity = 0.0
            pan_state = "CENTERED_X"
        else:
            # ⭐ DISTANCE-AWARE PAN: Aggressive at edges, smooth near center
            # Use exponential scaling: velocity = sign(offset) * offset_ratio^2
            # This gives: slow response near center, aggressive response at edges
            max_pan_velocity = 1.0
            
            # Calculate distance from center as fraction of half-frame width (0.0 to 1.0+)
            distance_from_center = abs(offset_pixels_x) / max_offset_x
            
            # Apply quadratic scaling: faster the farther from center
            # At center (distance=0): velocity ≈ 0
            # At edge (distance=1): velocity = 1.0
            # Beyond edge (distance>1): velocity = 1.0 (clamped)
            quadratic_velocity = min(1.0, distance_from_center ** 2)
            
            # Apply sign (direction) to velocity
            pan_velocity = max_pan_velocity * quadratic_velocity * (1 if offset_pixels_x > 0 else -1)
            
            # Clamp to valid range
            pan_velocity = max(-1.0, min(1.0, pan_velocity))
            pan_state = "TRACKING_X"
        
        # ========== TILT (Vertical Y-axis) ==========
        # Calculate offset from center (negative = above center, positive = below)
        # FIXED: Inverted Y-axis so positive offset = camera should tilt UP (negative velocity)
        offset_pixels_y = frame_center_y - subject_y
        
        # Calculate normalized offset (-1.0 to 1.0, where 0 = centered)
        max_offset_y = height / 2.0
        normalized_offset_y = offset_pixels_y / max_offset_y
        
        # Smaller dead zone for more responsive tilt tracking (20px instead of 40px)
        # This ensures subjects near top/bottom edges trigger tilt immediately
        DEAD_ZONE_PIXELS_Y = 20  # Reduced from 40px for faster response near edges
        if abs(offset_pixels_y) < DEAD_ZONE_PIXELS_Y:
            tilt_velocity = 0.0
            tilt_state = "CENTERED_Y"
        else:
            # ⭐ DISTANCE-AWARE TILT: Aggressive at edges, smooth near center
            # Use exponential scaling: velocity = sign(offset) * offset_ratio^2
            # This gives: slow response near center, aggressive response at edges
            max_tilt_velocity = 1.0
            
            # Calculate distance from center as fraction of half-frame height (0.0 to 1.0+)
            distance_from_center = abs(offset_pixels_y) / max_offset_y
            
            # Apply quadratic scaling: faster the farther from center
            # At center (distance=0): velocity ≈ 0
            # At edge (distance=1): velocity = 1.0
            # Beyond edge (distance>1): velocity = 1.0 (clamped)
            quadratic_velocity = min(1.0, distance_from_center ** 2)
            
            # FIXED: Negate tilt to correct camera firmware behavior
            # Apply sign (direction) to velocity - negative for up, positive for down
            tilt_velocity = -(max_tilt_velocity * quadratic_velocity * (1 if offset_pixels_y > 0 else -1))
            
            # ⭐ TILT DAMPING: Limit aggressive tilt (camera may not physically respond)
            # Some cameras have mechanical limits or firmware lag on tilt
            # Increase tilt velocity to 0.75 for better upward tracking response
            MAX_TILT_VELOCITY = 0.75  # Increased to 75% for better vertical tracking
            tilt_velocity = max(-MAX_TILT_VELOCITY, min(MAX_TILT_VELOCITY, tilt_velocity))
            
            # Clamp to valid range
            tilt_velocity = max(-1.0, min(1.0, tilt_velocity))
            tilt_state = "TRACKING_Y"
        
        # Log tracking state
        logger.info(
            f"{detection.class_name} fast center tracking: "
            f"X offset={offset_pixels_x:+.0f}px → pan={pan_velocity:+.2f} ({pan_state}) | "
            f"Y offset={offset_pixels_y:+.0f}px → tilt={tilt_velocity:+.2f} ({tilt_state})"
        )
        
        # ⭐ DIAGNOSTIC LOG: Show what we're about to send
        print(f"⭐ [TRACKING ENGINE] About to send continuous_move command:")
        print(f"   Subject: {detection.class_name} at ({subject_x:.0f}, {subject_y:.0f})")
        print(f"   Frame center: ({frame_center_x:.0f}, {frame_center_y:.0f})")
        print(f"   Offset: X={offset_pixels_x:+.0f}px, Y={offset_pixels_y:+.0f}px")
        print(f"   Velocity: pan={pan_velocity:+.2f}, tilt={tilt_velocity:+.2f}")
        logger.warning(f"⭐ [TRACKING ENGINE] Velocity command: pan={pan_velocity:+.2f}, tilt={tilt_velocity:+.2f}")
        
        # ========== AUTO-ZOOM BASED ON DISTANCE ==========
        # Estimate distance from bounding box size
        # Smaller box = farther away = more zoom needed
        bbox_width = detection.bbox[2] - detection.bbox[0]
        bbox_height = detection.bbox[3] - detection.bbox[1]
        bbox_area = bbox_width * bbox_height
        
        # Calibration: Assume ~40000 px² = person at ideal distance (no zoom needed)
        # Smaller area = zoom in, larger area = zoom out
        IDEAL_BBOX_AREA = 40000
        
        # ⭐ APPLY ZOOM EVERY FRAME
        # Smart zoom logic prevents aggressive zooming anyway (only zooms if approaching)
        if bbox_area > 0:
            # Check if subject is getting CLOSER (bbox_area increasing)
            getting_closer = False
            if self.last_bbox_area is not None:
                # If area increased, subject is closer
                getting_closer = bbox_area > self.last_bbox_area * 1.05  # 5% threshold to avoid noise
            
            # Only zoom if subject is getting closer
            if getting_closer:
                area_ratio = IDEAL_BBOX_AREA / bbox_area
                zoom_velocity = max(-0.2, min(0.2, (area_ratio - 1.0) * 0.05))
            else:
                zoom_velocity = 0.0  # Stop zooming if moving away
            
            self.last_bbox_area = bbox_area
        else:
            zoom_velocity = 0.0
        
        print(f"   Distance estimate: bbox_area={bbox_area:.0f}px² → zoom={zoom_velocity:+.2f}")
        logger.info(f"Auto-zoom: bbox_area={bbox_area:.0f} → zoom_velocity={zoom_velocity:+.2f}")
        
        try:
            # Execute continuous pan/tilt/zoom movement (blocking with SHORT duration)
            # CRITICAL: Must use blocking=True, otherwise camera never stops moving!
            # ⭐ TILT NOTE: Use 0.15s duration instead of 0.1s to give camera time to respond
            # to tilt commands. Dahua cameras can have mechanical lag on upward tilt.
            move_duration = 0.15  # Slightly longer for tilt responsiveness
            
            self.ptz.continuous_move(
                pan_velocity=pan_velocity,
                tilt_velocity=tilt_velocity,
                zoom_velocity=zoom_velocity,  # Auto-zoom based on distance
                duration=move_duration,  # Increased for tilt responsiveness
                blocking=True  # CRITICAL: Automatically stops after duration
            )
            
            self.last_ptz_time = time.time()
            self.ptz_movement_count += 1
            
            # Describe current state for display
            state_parts = []
            if pan_velocity > 0.1:
                state_parts.append("PAN_RIGHT")
            elif pan_velocity < -0.1:
                state_parts.append("PAN_LEFT")
            else:
                state_parts.append("CENTER_X")
            
            if tilt_velocity > 0.1:
                state_parts.append("TILT_DOWN")
            elif tilt_velocity < -0.1:
                state_parts.append("TILT_UP")
            else:
                state_parts.append("CENTER_Y")
            
            self.current_preset = "|".join(state_parts)
            

            if self.on_ptz_move:
                self.on_ptz_move(self.current_preset)
            
            # Record event
            self._record_tracking_event(
                object_id=track_info.object_id,
                class_name=detection.class_name,
                direction=direction,
                zone="tracking",
                preset=self.current_preset
            )
            
        except Exception as e:
            logger.error(f"Failed to execute center tracking pan: {e}")

    
    def _get_zone_for_position(
        self,
        position: tuple[int, int],
        frame_shape: tuple
    ) -> Optional[TrackingZone]:
        """
        Determine which zone a position falls into
        
        Args:
            position: (x, y) position in frame
            frame_shape: Frame dimensions (height, width, channels)
            
        Returns:
            TrackingZone or None
        """
        if not self.config.zones:
            return None
        
        height, width = frame_shape[:2]
        x, y = position
        
        # Normalize position to 0.0-1.0
        norm_x = x / width
        norm_y = y / height
        
        # Find matching zone (highest priority if multiple match)
        matching_zones = []
        
        for zone in self.config.zones:
            x_min, x_max = zone.x_range
            y_min, y_max = zone.y_range
            
            if x_min <= norm_x <= x_max and y_min <= norm_y <= y_max:
                matching_zones.append(zone)
        
        if not matching_zones:
            return None
        
        # Return highest priority zone
        return max(matching_zones, key=lambda z: z.priority)
    
    def _determine_target_preset(
        self,
        direction: Direction,
        current_zone: TrackingZone
    ) -> Optional[str]:
        """
        Determine which PTZ preset to move to based on direction and current zone
        
        Args:
            direction: Movement direction
            current_zone: Zone object is currently in
            
        Returns:
            Preset token or None
        """
        # For RIGHT_TO_LEFT movement, anticipate by moving camera left
        if direction == Direction.RIGHT_TO_LEFT:
            # Find leftmost zone
            left_zones = [z for z in self.config.zones if z.x_range[0] < current_zone.x_range[0]]
            
            if left_zones:
                # Get the leftmost zone
                target_zone = min(left_zones, key=lambda z: z.x_range[0])
                return target_zone.preset_token
        
        # For LEFT_TO_RIGHT movement, anticipate by moving camera right
        elif direction == Direction.LEFT_TO_RIGHT:
            # Find rightmost zone
            right_zones = [z for z in self.config.zones if z.x_range[1] > current_zone.x_range[1]]
            
            if right_zones:
                # Get the rightmost zone
                target_zone = max(right_zones, key=lambda z: z.x_range[1])
                return target_zone.preset_token
        
        # For vertical movement, could implement similar logic
        elif direction == Direction.TOP_TO_BOTTOM:
            # Move down
            pass
        
        elif direction == Direction.BOTTOM_TO_TOP:
            # Move up
            pass
        
        return None
    
    def _record_tracking_event(
        self,
        object_id: str,
        class_name: str,
        direction: Direction,
        zone: str,
        preset: str
    ) -> None:
        """
        Record tracking event for analytics
        
        Args:
            object_id: Tracked object ID
            class_name: Object class
            direction: Movement direction
            zone: Current zone
            preset: PTZ preset activated
        """
        current_time = time.time()
        
        # Check if event already exists
        if object_id in self.active_events:
            event = self.active_events[object_id]
            event.frame_count += 1
            event.zone_transitions.append(zone)
            event.ptz_actions.append(preset)
        else:
            # Create new event
            self.event_counter += 1
            event = TrackingEvent(
                event_id=f"event_{self.event_counter}",
                object_id=object_id,
                class_name=class_name,
                direction=direction,
                start_time=current_time,
                zone_transitions=[zone],
                ptz_actions=[preset],
                frame_count=1
            )
            
            self.active_events[object_id] = event
            
            logger.info(f"Started tracking event: {event.event_id}")
    
    def get_statistics(self) -> Dict:
        """
        Get tracking statistics
        
        Returns:
            Dictionary with tracking stats
        """
        return {
            'frames_processed': self.frame_count,
            'detections': self.detection_count,
            'tracks': self.tracking_count,
            'ptz_movements': self.ptz_movement_count,
            'active_events': len(self.active_events),
            'completed_events': len(self.completed_events),
            'current_preset': self.current_preset,
            'is_running': self.running,
            'is_paused': self.paused,
            'mode': self.mode.value
        }
    
    def get_active_events(self) -> List[TrackingEvent]:
        """Get currently active tracking events"""
        return list(self.active_events.values())
    
    def get_completed_events(self) -> List[TrackingEvent]:
        """Get completed tracking events"""
        return self.completed_events.copy()
    
    # ⭐ QUADRANT TRACKING METHODS
    def _get_quadrant_for_position(
        self,
        x: int,
        y: int,
        width: int,
        height: int
    ) -> str:
        """
        Determine which quadrant a position is in
        
        Args:
            x, y: Subject center position
            width, height: Frame dimensions
            
        Returns:
            Quadrant name: 'top_left', 'top_right', 'bottom_left', 'bottom_right'
        """
        mid_x = width / 2.0
        mid_y = height / 2.0
        
        if x < mid_x:
            if y < mid_y:
                return "top_left"
            else:
                return "bottom_left"
        else:
            if y < mid_y:
                return "top_right"
            else:
                return "bottom_right"
    
    def _handle_quadrant_tracking_action(
        self,
        detection: DetectionResult,
        quadrant: str,
        frame
    ) -> None:
        """
        Handle tracking within quadrant-based mode
        
        Args:
            detection: Detection result
            quadrant: Current quadrant name
            frame: Current video frame
        """
        height, width = frame.shape[:2]
        
        # ✅ Step 1: Check if quadrant changed
        if quadrant != self.current_quadrant:
            logger.info(f"Quadrant changed: {self.current_quadrant} → {quadrant}")
            
            # Calculate pan/tilt offsets for the quadrant (relative to master view)
            # Each quadrant is 25% of the master view, zoomed in
            quadrant_offsets = {
                'top_left': {'pan': -0.25, 'tilt': 0.25},      # Pan left 25%, tilt up 25%
                'top_right': {'pan': 0.25, 'tilt': 0.25},      # Pan right 25%, tilt up 25%
                'bottom_left': {'pan': -0.25, 'tilt': -0.25},  # Pan left 25%, tilt down 25%
                'bottom_right': {'pan': 0.25, 'tilt': -0.25}   # Pan right 25%, tilt down 25%
            }
            
            offset = quadrant_offsets.get(quadrant)
            
            if offset:
                logger.info(f"Moving to {quadrant} (pan={offset['pan']}, tilt={offset['tilt']})")
                try:
                    # Execute relative move to quadrant position
                    self.ptz.relative_move(
                        pan_delta=offset['pan'],
                        tilt_delta=offset['tilt'],
                        zoom_delta=0.0,
                        speed=0.5
                    )
                    
                    # Wait for movement to complete
                    time.sleep(0.5)
                    
                    # Apply zoom to focus on quadrant (zoom in 25%)
                    behavior = self.quadrant_config.get('behavior', {})
                    if behavior.get('zoom_on_entry', True):
                        zoom_level = behavior.get('zoom_level', 0.5)
                        self.ptz.continuous_move(
                            pan_velocity=0.0,
                            tilt_velocity=0.0,
                            zoom_velocity=zoom_level,
                            duration=0.8
                        )
                        logger.info(f"Quadrant zoom on entry: {zoom_level}")
                    
                    self.current_quadrant = quadrant
                    self.quadrant_zoom_counter = 0
                    
                except Exception as e:
                    logger.error(f"Failed to move to quadrant: {e}")
            else:
                logger.warning(f"Unknown quadrant: {quadrant}")
        
        # ✅ Step 2: Fine-tune pan/tilt within quadrant (similar to center tracking)
        behavior = self.quadrant_config.get('behavior', {})
        if behavior.get('fine_tune_tracking'):
            frame_center_x = width / 2.0
            frame_center_y = height / 2.0
            
            subject_x = detection.center[0]
            subject_y = detection.center[1]
            
            # Calculate offset from center
            offset_pixels_x = subject_x - frame_center_x
            offset_pixels_y = subject_y - frame_center_y
            
            # Distance-aware pan/tilt (same quadratic scaling as center mode)
            max_offset_x = frame_center_x
            max_offset_y = frame_center_y
            
            distance_from_center_x = abs(offset_pixels_x) / max_offset_x
            quadratic_velocity_x = min(1.0, distance_from_center_x ** 2)
            pan_velocity = 0.5 * quadratic_velocity_x * (1 if offset_pixels_x > 0 else -1)
            
            distance_from_center_y = abs(offset_pixels_y) / max_offset_y
            quadratic_velocity_y = min(1.0, distance_from_center_y ** 2)
            tilt_velocity = -(0.5 * quadratic_velocity_y * (1 if offset_pixels_y > 0 else -1))
            
            if abs(pan_velocity) > 0.01 or abs(tilt_velocity) > 0.01:
                try:
                    self.ptz.continuous_move(
                        pan_velocity=pan_velocity,
                        tilt_velocity=tilt_velocity,
                        zoom_velocity=0.0,
                        duration=0.1
                    )
                except Exception as e:
                    logger.error(f"Failed to fine-tune pan/tilt: {e}")
    
    def toggle_quadrant_mode(self, enabled: Optional[bool] = None) -> bool:
        """
        Toggle between center tracking and quadrant tracking
        
        Args:
            enabled: True to enable, False to disable, None to toggle
            
        Returns:
            New quadrant_mode_enabled state
        """
        if enabled is None:
            self.quadrant_mode_enabled = not self.quadrant_mode_enabled
        else:
            self.quadrant_mode_enabled = enabled
        
        if self.quadrant_mode_enabled:
            logger.info("✓ Quadrant tracking mode ENABLED")
            self.current_quadrant = None  # Reset on mode switch
            self.quadrant_zoom_counter = 0
        else:
            logger.info("✓ Quadrant tracking mode DISABLED (center tracking)")
            self.current_quadrant = None
        
        return self.quadrant_mode_enabled
    
    def get_quadrant_mode(self) -> bool:
        """Get current quadrant tracking mode state"""
        return self.quadrant_mode_enabled
    
    def set_mode(self, mode: TrackingMode) -> None:
        """Change tracking mode"""
        self.mode = mode
        logger.info(f"Tracking mode changed to: {mode.value}")
    
    def __repr__(self) -> str:
        """String representation"""
        return (
            f"TrackingEngine(running={self.running}, "
            f"frames={self.frame_count}, "
            f"detections={self.detection_count})"
        )
