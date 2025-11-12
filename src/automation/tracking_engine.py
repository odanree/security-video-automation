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
    """
    zones: List[TrackingZone] = field(default_factory=list)
    target_classes: List[str] = field(default_factory=lambda: ['person'])
    direction_triggers: List[Direction] = field(default_factory=lambda: [Direction.RIGHT_TO_LEFT])
    min_confidence: float = 0.6
    movement_threshold: int = 50
    cooldown_time: float = 3.0
    max_tracking_age: float = 2.0
    enable_recording: bool = False


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
        self.active_events: Dict[str, TrackingEvent] = {}
        self.completed_events: List[TrackingEvent] = []
        self.event_counter = 0
        
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
            return
        
        # Step 2: Update motion tracking
        for detection in detections:
            # Generate unique object ID
            object_id = f"{detection.class_name}_{detection.center[0]}_{detection.center[1]}"
            
            # Update motion tracker
            direction = self.motion_tracker.update(
                object_id=object_id,
                center=detection.center,
                timestamp=current_time
            )
            
            # Get track info
            track_info = self.motion_tracker.get_track_info(object_id)
            
            if track_info is None:
                continue
            
            self.tracking_count += 1
            
            if self.on_tracking:
                self.on_tracking(track_info)
            
            # Step 3: Check if tracking should trigger action
            if self._should_trigger_tracking(detection, direction, track_info):
                self._handle_tracking_action(detection, direction, track_info, frame)
    
    def _should_trigger_tracking(
        self,
        detection: DetectionResult,
        direction: Direction,
        track_info: TrackInfo
    ) -> bool:
        """
        Determine if tracking action should be triggered
        
        Args:
            detection: Detection result
            direction: Movement direction
            track_info: Tracking information
            
        Returns:
            True if action should be triggered
        """
        # Check if direction matches triggers
        if direction not in self.config.direction_triggers:
            return False
        
        # Check if object has moved enough
        if track_info.total_displacement < self.config.movement_threshold:
            return False
        
        # Check cooldown
        time_since_last_move = time.time() - self.last_ptz_time
        if time_since_last_move < self.config.cooldown_time:
            return False
        
        # Check if object is stationary
        if direction == Direction.STATIONARY:
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
        Execute tracking action (PTZ movement)
        
        Args:
            detection: Detection result
            direction: Movement direction
            track_info: Tracking information
            frame: Current video frame
        """
        # Determine which zone the subject is in
        zone = self._get_zone_for_position(detection.center, frame.shape)
        
        if zone is None:
            return
        
        # Determine target preset based on direction and zone
        target_preset = self._determine_target_preset(direction, zone)
        
        if target_preset is None:
            return
        
        # Check if already at target preset
        if target_preset == self.current_preset:
            return
        
        # Execute PTZ movement
        logger.info(
            f"Tracking {detection.class_name} moving {direction.value} "
            f"in {zone.name} → Moving to preset {target_preset}"
        )
        
        try:
            self.ptz.goto_preset(target_preset, speed=0.8)
            
            self.current_preset = target_preset
            self.last_ptz_time = time.time()
            self.ptz_movement_count += 1
            
            if self.on_ptz_move:
                self.on_ptz_move(target_preset)
            
            # Record event
            self._record_tracking_event(
                object_id=track_info.object_id,
                class_name=detection.class_name,
                direction=direction,
                zone=zone.name,
                preset=target_preset
            )
            
        except Exception as e:
            logger.error(f"Failed to move PTZ camera: {e}")
    
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
