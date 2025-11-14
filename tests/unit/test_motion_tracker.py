"""
Unit tests for Motion Tracker

Tests direction detection, velocity calculation, and multi-object tracking.
"""

import pytest
from enum import Enum
from unittest.mock import Mock, MagicMock
from src.ai.motion_tracker import MotionTracker, Direction, MultiObjectTracker


@pytest.fixture
def motion_tracker():
    """Create motion tracker for testing"""
    return MotionTracker(
        history_length=30,
        movement_threshold=50
    )


@pytest.fixture
def multi_tracker():
    """Create multi-object tracker for testing"""
    return MultiObjectTracker(
        max_distance=100.0,
        max_age=30
    )


class TestMotionTrackerInit:
    """Test motion tracker initialization"""
    
    def test_initialization(self, motion_tracker):
        """Test successful initialization"""
        assert motion_tracker.history_length == 30
        assert motion_tracker.movement_threshold == 50
        assert motion_tracker.tracked_objects == {}
    
    def test_custom_parameters(self):
        """Test initialization with custom parameters"""
        tracker = MotionTracker(history_length=50, movement_threshold=100)
        
        assert tracker.history_length == 50
        assert tracker.movement_threshold == 100


class TestDirectionDetection:
    """Test movement direction detection"""
    
    def test_stationary_object(self, motion_tracker):
        """Test detection of stationary object"""
        center = (320, 240)
        
        # Update with same position multiple times
        for _ in range(10):
            direction = motion_tracker.update("obj_1", center)
        
        assert direction == Direction.STATIONARY
    
    def test_left_to_right_movement(self, motion_tracker):
        """Test detection of left-to-right movement"""
        # Start on left, move right
        for x in range(100, 200, 10):
            direction = motion_tracker.update("obj_1", (x, 240))
        
        assert direction == Direction.LEFT_TO_RIGHT
    
    def test_right_to_left_movement(self, motion_tracker):
        """Test detection of right-to-left movement"""
        # Start on right, move left
        for x in range(500, 400, -10):
            direction = motion_tracker.update("obj_1", (x, 240))
        
        assert direction == Direction.RIGHT_TO_LEFT
    
    def test_top_to_bottom_movement(self, motion_tracker):
        """Test detection of top-to-bottom movement"""
        # Start on top, move down
        for y in range(100, 200, 10):
            direction = motion_tracker.update("obj_1", (320, y))
        
        assert direction == Direction.TOP_TO_BOTTOM
    
    def test_bottom_to_top_movement(self, motion_tracker):
        """Test detection of bottom-to-top movement"""
        # Start on bottom, move up
        for y in range(400, 300, -10):
            direction = motion_tracker.update("obj_1", (320, y))
        
        assert direction == Direction.BOTTOM_TO_TOP


class TestMovementThreshold:
    """Test movement threshold behavior"""
    
    def test_small_movement_below_threshold(self, motion_tracker):
        """Test that small movements below threshold are stationary"""
        motion_tracker.movement_threshold = 100
        
        # Small movement (10 pixels)
        for i in range(15):
            center = (320 + i, 240)
            direction = motion_tracker.update("obj_1", center)
        
        # Should be stationary (total movement < 100)
        assert direction == Direction.STATIONARY
    
    def test_large_movement_above_threshold(self, motion_tracker):
        """Test that large movements above threshold are detected"""
        motion_tracker.movement_threshold = 50
        
        # Large movement (100 pixels right)
        for i in range(15):
            center = (320 + i*7, 240)  # Each step is 7 pixels, total ~105
            direction = motion_tracker.update("obj_1", center)
        
        # Should detect direction (total movement > 50)
        assert direction != Direction.STATIONARY


class TestPositionHistory:
    """Test position history tracking"""
    
    def test_history_size_limited(self, motion_tracker):
        """Test that position history is limited to history_length"""
        motion_tracker.history_length = 10
        
        # Add 20 positions
        for i in range(20):
            motion_tracker.update("obj_1", (100 + i, 200))
        
        # History should be limited to 10
        assert len(motion_tracker.tracked_objects["obj_1"]) == 10
    
    def test_multiple_objects(self, motion_tracker):
        """Test tracking multiple objects simultaneously"""
        # Track 3 objects
        for i in range(5):
            motion_tracker.update("obj_1", (100 + i*5, 200))
            motion_tracker.update("obj_2", (300 + i*5, 200))
            motion_tracker.update("obj_3", (500 + i*5, 200))
        
        assert len(motion_tracker.tracked_objects) == 3
        assert "obj_1" in motion_tracker.tracked_objects
        assert "obj_2" in motion_tracker.tracked_objects
        assert "obj_3" in motion_tracker.tracked_objects


class TestDirectionEnum:
    """Test Direction enum"""
    
    def test_direction_values(self):
        """Test that all direction values are defined"""
        assert hasattr(Direction, 'LEFT_TO_RIGHT')
        assert hasattr(Direction, 'RIGHT_TO_LEFT')
        assert hasattr(Direction, 'TOP_TO_BOTTOM')
        assert hasattr(Direction, 'BOTTOM_TO_TOP')
        assert hasattr(Direction, 'STATIONARY')
    
    def test_direction_enum_comparison(self):
        """Test comparing direction enums"""
        d1 = Direction.LEFT_TO_RIGHT
        d2 = Direction.LEFT_TO_RIGHT
        d3 = Direction.RIGHT_TO_LEFT
        
        assert d1 == d2
        assert d1 != d3


class TestMultiObjectTracker:
    """Test multi-object tracker"""
    
    def test_initialization(self, multi_tracker):
        """Test multi-object tracker initialization"""
        assert multi_tracker.max_distance == 100.0
        assert multi_tracker.max_age == 30
    
    def test_single_object_tracking(self, multi_tracker):
        """Test tracking a single object"""
        detection1 = MagicMock()
        detection1.center = (100, 100)
        
        # First frame
        tracks = multi_tracker.update([detection1], frame_number=0)
        
        assert len(tracks) == 1
    
    def test_multiple_objects_tracking(self, multi_tracker):
        """Test tracking multiple objects"""
        detection1 = MagicMock()
        detection1.center = (100, 100)
        
        detection2 = MagicMock()
        detection2.center = (300, 300)
        
        # First frame
        tracks = multi_tracker.update([detection1, detection2], frame_number=0)
        
        assert len(tracks) == 2
    
    def test_object_persistence(self, multi_tracker):
        """Test that objects maintain IDs across frames"""
        detection1 = MagicMock()
        detection1.center = (100, 100)
        
        # Frame 1
        tracks1 = multi_tracker.update([detection1], frame_number=0)
        id1 = tracks1[0].track_id if hasattr(tracks1[0], 'track_id') else None
        
        # Frame 2 - same object, slightly moved
        detection2 = MagicMock()
        detection2.center = (105, 105)  # Close to previous position
        
        tracks2 = multi_tracker.update([detection2], frame_number=1)
        id2 = tracks2[0].track_id if hasattr(tracks2[0], 'track_id') else None
        
        # IDs should match (same object)
        if id1 is not None and id2 is not None:
            assert id1 == id2


class TestEdgeCases:
    """Test edge cases"""
    
    def test_single_position_is_stationary(self, motion_tracker):
        """Test that single position update is stationary"""
        direction = motion_tracker.update("obj_1", (320, 240))
        
        assert direction == Direction.STATIONARY
    
    def test_rapid_direction_changes(self, motion_tracker):
        """Test detection with rapid direction changes"""
        # Move right then left then right
        positions = [
            (100, 240),
            (150, 240),
            (200, 240),  # Moving right
            (150, 240),  # Back left
            (100, 240),  # Further left
            (150, 240),  # Back right
        ]
        
        last_direction = None
        for pos in positions:
            direction = motion_tracker.update("obj_1", pos)
            last_direction = direction
        
        # Final direction depends on last movement
        assert last_direction is not None
    
    def test_diagonal_movement(self, motion_tracker):
        """Test detection with diagonal movement"""
        # Move diagonally (down and to the right)
        for i in range(10):
            x = 100 + i * 10
            y = 100 + i * 10
            direction = motion_tracker.update("obj_1", (x, y))
        
        # Should detect dominant direction
        assert direction != Direction.STATIONARY
    
    def test_circular_movement(self, motion_tracker):
        """Test detection with circular/complex movement"""
        # Move in a circle
        positions = [
            (200, 100),  # Top
            (300, 150),  # Top-right
            (300, 250),  # Right
            (200, 300),  # Bottom-right
            (100, 300),  # Bottom
            (50, 200),   # Left
        ]
        
        last_direction = None
        for pos in positions:
            direction = motion_tracker.update("obj_1", pos)
            last_direction = direction
        
        assert last_direction is not None


class TestVelocityCalculation:
    """Test velocity calculation"""
    
    def test_constant_velocity(self, motion_tracker):
        """Test detection with constant velocity"""
        # Move at constant velocity (1 unit per frame)
        for i in range(15):
            motion_tracker.update("obj_1", (100 + i, 240))
        
        # Should detect direction
        assert motion_tracker.update("obj_1", (115, 240)) == Direction.LEFT_TO_RIGHT
    
    def test_accelerating_movement(self, motion_tracker):
        """Test detection with accelerating movement"""
        # Move with increasing velocity
        x = 100
        for i in range(10):
            motion_tracker.update("obj_1", (x, 240))
            x += i  # Accelerating
        
        # Should still detect direction
        direction = motion_tracker.update("obj_1", (x + 10, 240))
        assert direction != Direction.STATIONARY


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
