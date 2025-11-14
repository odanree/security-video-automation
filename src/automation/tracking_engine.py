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
    AUTO = "auto"           # Fully automated tracking
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
        self.home_preset: str = config.home_preset  # Load from config (Preset004)
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
        self.last_movement_time = time.time()  # Initialize inactivity timer
        self.thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self.thread.start()
        
        logger.info("✓ Tracking engine started")
    
    def stop(self) -> None:
        """Stop automated tracking"""
        if not self.running:
            return
        
        logger.info("Stopping tracking engine...")
        
        self.running = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5.0)
        
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
        
        # Step 1: Detect objects
        detections = self.detector.detect(frame, frame_number=self.frame_count)
        
        # Filter by target classes and confidence
        detections = [
            d for d in detections
            if d.class_name in self.config.target_classes
            and d.confidence >= self.config.min_confidence
        ]
        
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
        
        Args:
            current_time: Current timestamp
        """
        # Check if we have a home position configured
        if not self.home_preset:
            return
        
        # If no movement in the timeout period, return home
        time_since_last_move = current_time - self.last_movement_time
        
        if time_since_last_move >= self.inactivity_timeout:
            # Only go home if not already there
            if self.current_preset != self.home_preset:
                try:
                    logger.info(
                        f"No movement for {time_since_last_move:.1f}s - "
                        f"Returning to home preset {self.home_preset}"
                    )
                    self.ptz.goto_preset(self.home_preset, speed=0.7)
                    self.current_preset = self.home_preset
                    self.last_ptz_time = current_time
                except Exception as e:
                    logger.error(f"Failed to return to home preset: {e}")
    
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
        # For center tracking, we want faster updates (0.2s instead of 3.0s)
        center_tracking_cooldown = 0.2  # Much shorter for responsive centering
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
        frame_center_x = width / 2.0
        frame_center_y = height / 2.0
        subject_x = detection.center[0]
        subject_y = detection.center[1]
        
        # ========== PAN (Horizontal X-axis) ==========
        # Calculate offset from center (negative = left of center, positive = right)
        offset_pixels_x = subject_x - frame_center_x
        
        # Calculate normalized offset (-1.0 to 1.0, where 0 = centered)
        max_offset_x = width / 2.0
        normalized_offset_x = offset_pixels_x / max_offset_x
        
        # Small dead zone for fast response (40px instead of 80px)
        DEAD_ZONE_PIXELS_X = 40
        if abs(offset_pixels_x) < DEAD_ZONE_PIXELS_X:
            pan_velocity = 0.0
            pan_state = "CENTERED_X"
        else:
            # Faster max velocity for quicker centering
            max_pan_velocity = 1.0
            
            # Use linear mapping for faster initial response
            # (quadratic was too slow to get started)
            pan_velocity = max_pan_velocity * normalized_offset_x
            
            # Clamp to valid range
            pan_velocity = max(-1.0, min(1.0, pan_velocity))
            pan_state = "TRACKING_X"
        
        # ========== TILT (Vertical Y-axis) ==========
        # Calculate offset from center (negative = above center, positive = below)
        offset_pixels_y = subject_y - frame_center_y
        
        # Calculate normalized offset (-1.0 to 1.0, where 0 = centered)
        max_offset_y = height / 2.0
        normalized_offset_y = offset_pixels_y / max_offset_y
        
        # Small dead zone for fast response (40px instead of 80px)
        DEAD_ZONE_PIXELS_Y = 40
        if abs(offset_pixels_y) < DEAD_ZONE_PIXELS_Y:
            tilt_velocity = 0.0
            tilt_state = "CENTERED_Y"
        else:
            # Faster max velocity for quicker centering
            max_tilt_velocity = 1.0
            
            # Use linear mapping for faster initial response
            tilt_velocity = max_tilt_velocity * normalized_offset_y
            
            # Clamp to valid range
            tilt_velocity = max(-1.0, min(1.0, tilt_velocity))
            tilt_state = "TRACKING_Y"
        
        # Log tracking state
        logger.info(
            f"{detection.class_name} fast center tracking: "
            f"X offset={offset_pixels_x:+.0f}px → pan={pan_velocity:+.2f} ({pan_state}) | "
            f"Y offset={offset_pixels_y:+.0f}px → tilt={tilt_velocity:+.2f} ({tilt_state})"
        )
        
        try:
            # Execute continuous pan/tilt movement (non-blocking, shorter duration for faster updates)
            # Reduced from 0.3s to 0.15s for more responsive centering
            self.ptz.continuous_move(
                pan_velocity=pan_velocity,
                tilt_velocity=tilt_velocity,
                zoom_velocity=0.0,
                duration=0.15,  # Faster updates = faster centering
                blocking=False  # Non-blocking so we process next frame immediately
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
