"""
Motion Tracker

Tracks object movement across video frames and determines direction of motion.
Maintains position history for each tracked object and calculates velocity vectors.

Example:
    from src.ai.motion_tracker import MotionTracker, Direction
    
    tracker = MotionTracker(history_length=30, movement_threshold=50)
    
    # Update with detection results
    direction = tracker.update(object_id="person_1", center=(320, 240))
    
    if direction == Direction.RIGHT_TO_LEFT:
        print("Subject moving right to left - trigger camera preset!")
"""

import logging
import time
from collections import deque
from enum import Enum
from typing import Dict, List, Optional, Tuple, Deque
from dataclasses import dataclass

import numpy as np


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Direction(Enum):
    """Movement directions for tracked objects"""
    LEFT_TO_RIGHT = "left_to_right"
    RIGHT_TO_LEFT = "right_to_left"
    TOP_TO_BOTTOM = "top_to_bottom"
    BOTTOM_TO_TOP = "bottom_to_top"
    STATIONARY = "stationary"
    UNKNOWN = "unknown"


@dataclass
class TrackInfo:
    """
    Information about a tracked object
    
    Attributes:
        object_id: Unique identifier for tracked object
        current_position: Current (x, y) center position
        current_direction: Current movement direction
        velocity: (vx, vy) velocity vector in pixels/second
        total_displacement: Total distance traveled since first detection
        frames_tracked: Number of frames this object has been tracked
        last_update_time: Timestamp of last position update
        is_active: Whether object is currently being tracked
    """
    object_id: str
    current_position: Tuple[int, int]
    current_direction: Direction
    velocity: Tuple[float, float]
    total_displacement: float
    frames_tracked: int
    last_update_time: float
    is_active: bool = True


class MotionTracker:
    """
    Track object motion and determine movement direction
    
    Uses position history to calculate velocity vectors and determine
    dominant direction of movement (e.g., right-to-left, stationary, etc.)
    """
    
    def __init__(
        self,
        history_length: int = 30,
        movement_threshold: int = 50,
        stationary_threshold: int = 20,
        inactive_timeout: float = 2.0
    ):
        """
        Initialize motion tracker
        
        Args:
            history_length: Number of frames to track for each object
            movement_threshold: Minimum pixel displacement to detect direction
            stationary_threshold: Maximum displacement to consider stationary
            inactive_timeout: Seconds before marking track as inactive
        """
        self.history_length = history_length
        self.movement_threshold = movement_threshold
        self.stationary_threshold = stationary_threshold
        self.inactive_timeout = inactive_timeout
        
        # Track position history for each object
        self.position_history: Dict[str, Deque[Tuple[int, int, float]]] = {}
        
        # Track metadata for each object
        self.track_info: Dict[str, TrackInfo] = {}
        
        logger.info(
            f"MotionTracker initialized: history={history_length}, "
            f"threshold={movement_threshold}px"
        )
    
    def update(
        self,
        object_id: str,
        center: Tuple[int, int],
        timestamp: Optional[float] = None
    ) -> Direction:
        """
        Update object position and calculate movement direction
        
        Args:
            object_id: Unique identifier for tracked object
            center: (x, y) center position in frame
            timestamp: Unix timestamp (uses current time if None)
            
        Returns:
            Direction enum indicating movement direction
            
        Example:
            direction = tracker.update("person_1", (320, 240))
            if direction == Direction.RIGHT_TO_LEFT:
                camera.goto_preset("zone_left")
        """
        if timestamp is None:
            timestamp = time.time()
        
        # Initialize tracking for new object
        if object_id not in self.position_history:
            self.position_history[object_id] = deque(maxlen=self.history_length)
            self.track_info[object_id] = TrackInfo(
                object_id=object_id,
                current_position=center,
                current_direction=Direction.UNKNOWN,
                velocity=(0.0, 0.0),
                total_displacement=0.0,
                frames_tracked=0,
                last_update_time=timestamp,
                is_active=True
            )
        
        # Add position to history (x, y, timestamp)
        self.position_history[object_id].append((center[0], center[1], timestamp))
        
        # Update track info
        track = self.track_info[object_id]
        track.current_position = center
        track.frames_tracked += 1
        track.last_update_time = timestamp
        track.is_active = True
        
        # Calculate direction and velocity
        direction = self._calculate_direction(object_id)
        velocity = self._calculate_velocity(object_id)
        displacement = self._calculate_total_displacement(object_id)
        
        track.current_direction = direction
        track.velocity = velocity
        track.total_displacement = displacement
        
        return direction
    
    def _calculate_direction(self, object_id: str) -> Direction:
        """
        Calculate movement direction from position history
        
        Args:
            object_id: Object to calculate direction for
            
        Returns:
            Direction enum
        """
        positions = self.position_history[object_id]
        
        # Need minimum history to determine direction
        if len(positions) < 5:
            return Direction.UNKNOWN
        
        # Get start and end positions
        start_x, start_y, start_time = positions[0]
        end_x, end_y, end_time = positions[-1]
        
        # Calculate displacement
        dx = end_x - start_x
        dy = end_y - start_y
        total_displacement = (dx ** 2 + dy ** 2) ** 0.5
        
        # Check if stationary
        if total_displacement < self.stationary_threshold:
            return Direction.STATIONARY
        
        # Check if displacement meets threshold
        if total_displacement < self.movement_threshold:
            return Direction.UNKNOWN
        
        # Determine dominant direction
        abs_dx = abs(dx)
        abs_dy = abs(dy)
        
        if abs_dx > abs_dy:
            # Horizontal movement is dominant
            if dx > 0:
                return Direction.LEFT_TO_RIGHT
            else:
                return Direction.RIGHT_TO_LEFT
        else:
            # Vertical movement is dominant
            if dy > 0:
                return Direction.TOP_TO_BOTTOM
            else:
                return Direction.BOTTOM_TO_TOP
    
    def _calculate_velocity(self, object_id: str) -> Tuple[float, float]:
        """
        Calculate velocity vector (vx, vy) in pixels per second
        
        Args:
            object_id: Object to calculate velocity for
            
        Returns:
            (vx, vy) velocity tuple
        """
        positions = self.position_history[object_id]
        
        if len(positions) < 2:
            return (0.0, 0.0)
        
        # Use recent positions for velocity calculation
        recent_count = min(10, len(positions))
        recent_positions = list(positions)[-recent_count:]
        
        start_x, start_y, start_time = recent_positions[0]
        end_x, end_y, end_time = recent_positions[-1]
        
        time_diff = end_time - start_time
        
        if time_diff <= 0:
            return (0.0, 0.0)
        
        vx = (end_x - start_x) / time_diff
        vy = (end_y - start_y) / time_diff
        
        return (vx, vy)
    
    def _calculate_total_displacement(self, object_id: str) -> float:
        """
        Calculate total distance traveled
        
        Args:
            object_id: Object to calculate displacement for
            
        Returns:
            Total displacement in pixels
        """
        positions = self.position_history[object_id]
        
        if len(positions) < 2:
            return 0.0
        
        total = 0.0
        
        for i in range(1, len(positions)):
            x1, y1, _ = positions[i - 1]
            x2, y2, _ = positions[i]
            
            distance = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
            total += distance
        
        return total
    
    def get_track_info(self, object_id: str) -> Optional[TrackInfo]:
        """
        Get tracking information for an object
        
        Args:
            object_id: Object to get info for
            
        Returns:
            TrackInfo object or None if not tracked
        """
        return self.track_info.get(object_id)
    
    def get_all_tracks(self) -> Dict[str, TrackInfo]:
        """
        Get tracking information for all objects
        
        Returns:
            Dictionary mapping object_id to TrackInfo
        """
        return self.track_info.copy()
    
    def get_active_tracks(self) -> Dict[str, TrackInfo]:
        """
        Get only active (recently updated) tracks
        
        Returns:
            Dictionary of active tracks
        """
        current_time = time.time()
        active = {}
        
        for obj_id, track in self.track_info.items():
            time_since_update = current_time - track.last_update_time
            
            if time_since_update <= self.inactive_timeout:
                active[obj_id] = track
            else:
                track.is_active = False
        
        return active
    
    def get_objects_by_direction(self, direction: Direction) -> List[TrackInfo]:
        """
        Get all objects moving in a specific direction
        
        Args:
            direction: Direction to filter by
            
        Returns:
            List of TrackInfo objects moving in that direction
        """
        return [
            track for track in self.get_active_tracks().values()
            if track.current_direction == direction
        ]
    
    def get_fastest_object(self) -> Optional[TrackInfo]:
        """
        Get the object with highest velocity magnitude
        
        Returns:
            TrackInfo of fastest object, or None if no active tracks
        """
        active_tracks = list(self.get_active_tracks().values())
        
        if not active_tracks:
            return None
        
        def velocity_magnitude(track: TrackInfo) -> float:
            vx, vy = track.velocity
            return (vx ** 2 + vy ** 2) ** 0.5
        
        return max(active_tracks, key=velocity_magnitude)
    
    def clear_track(self, object_id: str) -> None:
        """
        Remove tracking data for an object
        
        Args:
            object_id: Object to stop tracking
        """
        if object_id in self.position_history:
            del self.position_history[object_id]
        
        if object_id in self.track_info:
            del self.track_info[object_id]
        
        logger.debug(f"Cleared track for {object_id}")
    
    def clear_inactive_tracks(self) -> int:
        """
        Remove tracks that haven't been updated recently
        
        Returns:
            Number of tracks cleared
        """
        current_time = time.time()
        inactive_ids = []
        
        for obj_id, track in self.track_info.items():
            time_since_update = current_time - track.last_update_time
            
            if time_since_update > self.inactive_timeout:
                inactive_ids.append(obj_id)
        
        for obj_id in inactive_ids:
            self.clear_track(obj_id)
        
        if inactive_ids:
            logger.debug(f"Cleared {len(inactive_ids)} inactive tracks")
        
        return len(inactive_ids)
    
    def get_track_count(self) -> int:
        """Get total number of tracked objects"""
        return len(self.position_history)
    
    def get_active_track_count(self) -> int:
        """Get number of active tracked objects"""
        return len(self.get_active_tracks())
    
    def reset(self) -> None:
        """Clear all tracking data"""
        self.position_history.clear()
        self.track_info.clear()
        logger.info("Motion tracker reset")
    
    def __repr__(self) -> str:
        """String representation"""
        active_count = self.get_active_track_count()
        total_count = self.get_track_count()
        
        return (
            f"MotionTracker(active={active_count}, total={total_count}, "
            f"history={self.history_length})"
        )


class MultiObjectTracker:
    """
    High-level tracker for managing multiple objects with automatic ID assignment
    
    Integrates with object detector to maintain consistent tracking across frames.
    """
    
    def __init__(
        self,
        motion_tracker: Optional[MotionTracker] = None,
        max_distance: float = 100.0,
        max_age: int = 30
    ):
        """
        Initialize multi-object tracker
        
        Args:
            motion_tracker: MotionTracker instance (creates new if None)
            max_distance: Maximum distance to associate detections (pixels)
            max_age: Maximum frames to keep track without detection
        """
        self.motion_tracker = motion_tracker or MotionTracker()
        self.max_distance = max_distance
        self.max_age = max_age
        
        # Track ID management
        self.next_id = 1
        self.track_ages: Dict[str, int] = {}
        self.last_positions: Dict[str, Tuple[int, int]] = {}
    
    def update(
        self,
        detections: List[Tuple[int, int]],
        timestamp: Optional[float] = None
    ) -> Dict[str, Tuple[Tuple[int, int], Direction]]:
        """
        Update tracks with new detections
        
        Args:
            detections: List of (x, y) center positions
            timestamp: Frame timestamp
            
        Returns:
            Dictionary mapping track_id to (position, direction)
        """
        if timestamp is None:
            timestamp = time.time()
        
        # Match detections to existing tracks
        assignments = self._match_detections(detections)
        
        results = {}
        
        # Update matched tracks
        for track_id, detection_idx in assignments.items():
            if detection_idx is not None:
                position = detections[detection_idx]
                direction = self.motion_tracker.update(track_id, position, timestamp)
                
                self.track_ages[track_id] = 0
                self.last_positions[track_id] = position
                
                results[track_id] = (position, direction)
        
        # Create new tracks for unmatched detections
        matched_indices = set(assignments.values())
        
        for i, detection in enumerate(detections):
            if i not in matched_indices:
                track_id = f"track_{self.next_id}"
                self.next_id += 1
                
                direction = self.motion_tracker.update(track_id, detection, timestamp)
                
                self.track_ages[track_id] = 0
                self.last_positions[track_id] = detection
                
                results[track_id] = (detection, direction)
        
        # Age out old tracks
        self._age_tracks()
        
        return results
    
    def _match_detections(
        self,
        detections: List[Tuple[int, int]]
    ) -> Dict[str, Optional[int]]:
        """
        Match detections to existing tracks using nearest neighbor
        
        Args:
            detections: List of detection positions
            
        Returns:
            Dictionary mapping track_id to detection index (or None)
        """
        assignments = {}
        
        # Build cost matrix
        track_ids = list(self.last_positions.keys())
        
        if not track_ids or not detections:
            return assignments
        
        costs = np.zeros((len(track_ids), len(detections)))
        
        for i, track_id in enumerate(track_ids):
            last_pos = self.last_positions[track_id]
            
            for j, detection in enumerate(detections):
                distance = ((detection[0] - last_pos[0]) ** 2 + 
                           (detection[1] - last_pos[1]) ** 2) ** 0.5
                costs[i, j] = distance
        
        # Simple greedy matching
        used_detections = set()
        
        for i, track_id in enumerate(track_ids):
            min_cost = float('inf')
            best_detection = None
            
            for j in range(len(detections)):
                if j not in used_detections and costs[i, j] < min_cost:
                    min_cost = costs[i, j]
                    best_detection = j
            
            if best_detection is not None and min_cost < self.max_distance:
                assignments[track_id] = best_detection
                used_detections.add(best_detection)
            else:
                assignments[track_id] = None
        
        return assignments
    
    def _age_tracks(self) -> None:
        """Increment age of all tracks and remove old ones"""
        to_remove = []
        
        for track_id in list(self.track_ages.keys()):
            self.track_ages[track_id] += 1
            
            if self.track_ages[track_id] > self.max_age:
                to_remove.append(track_id)
        
        for track_id in to_remove:
            del self.track_ages[track_id]
            del self.last_positions[track_id]
            self.motion_tracker.clear_track(track_id)
    
    def get_motion_tracker(self) -> MotionTracker:
        """Get underlying motion tracker"""
        return self.motion_tracker
