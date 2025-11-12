"""
Test Motion Tracker

Validates motion tracking and direction detection with simulated movement.

Usage:
    python scripts/test_motion_tracker.py
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai.motion_tracker import MotionTracker, Direction


def simulate_movement(
    tracker: MotionTracker,
    object_id: str,
    positions: list,
    description: str
) -> Direction:
    """Simulate object movement through positions"""
    print(f"\n{description}")
    print(f"  Positions: {len(positions)} frames")
    
    final_direction = Direction.UNKNOWN
    
    for i, (x, y) in enumerate(positions):
        direction = tracker.update(object_id, (x, y))
        
        if i % 5 == 0:  # Print every 5th frame
            track_info = tracker.get_track_info(object_id)
            vx, vy = track_info.velocity if track_info else (0, 0)
            print(f"    Frame {i:2d}: pos=({x:3d}, {y:3d}), "
                  f"dir={direction.value:15s}, vel=({vx:6.1f}, {vy:6.1f})")
        
        final_direction = direction
        time.sleep(0.01)  # Simulate frame delay
    
    track_info = tracker.get_track_info(object_id)
    
    print(f"  ✓ Final direction: {final_direction.value}")
    print(f"  Total displacement: {track_info.total_displacement:.1f} pixels")
    print(f"  Frames tracked: {track_info.frames_tracked}")
    
    return final_direction


def main():
    print("=" * 70)
    print("Motion Tracker Test")
    print("=" * 70)
    
    # Initialize tracker
    print("\n[1/6] Initializing motion tracker...")
    tracker = MotionTracker(
        history_length=30,
        movement_threshold=50,
        stationary_threshold=20
    )
    print(f"      ✓ Tracker initialized: {tracker}")
    
    # Test 1: Right to Left movement
    print("\n[2/6] Testing RIGHT-TO-LEFT movement...")
    positions_rtl = [(500 - i*10, 240) for i in range(30)]  # Moving left
    direction = simulate_movement(
        tracker, "person_1", positions_rtl,
        "Simulating person walking right to left"
    )
    
    assert direction == Direction.RIGHT_TO_LEFT, \
        f"Expected RIGHT_TO_LEFT, got {direction.value}"
    print("      ✓ RIGHT-TO-LEFT detection: PASSED")
    
    # Test 2: Left to Right movement
    print("\n[3/6] Testing LEFT-TO-RIGHT movement...")
    tracker.reset()
    positions_ltr = [(100 + i*10, 240) for i in range(30)]  # Moving right
    direction = simulate_movement(
        tracker, "person_2", positions_ltr,
        "Simulating person walking left to right"
    )
    
    assert direction == Direction.LEFT_TO_RIGHT, \
        f"Expected LEFT_TO_RIGHT, got {direction.value}"
    print("      ✓ LEFT-TO-RIGHT detection: PASSED")
    
    # Test 3: Stationary object
    print("\n[4/6] Testing STATIONARY detection...")
    tracker.reset()
    positions_stationary = [(320, 240)] * 30  # Not moving
    direction = simulate_movement(
        tracker, "person_3", positions_stationary,
        "Simulating stationary person"
    )
    
    assert direction == Direction.STATIONARY, \
        f"Expected STATIONARY, got {direction.value}"
    print("      ✓ STATIONARY detection: PASSED")
    
    # Test 4: Top to Bottom movement
    print("\n[5/6] Testing TOP-TO-BOTTOM movement...")
    tracker.reset()
    positions_ttb = [(320, 100 + i*10) for i in range(30)]  # Moving down
    direction = simulate_movement(
        tracker, "person_4", positions_ttb,
        "Simulating person walking top to bottom"
    )
    
    assert direction == Direction.TOP_TO_BOTTOM, \
        f"Expected TOP_TO_BOTTOM, got {direction.value}"
    print("      ✓ TOP-TO-BOTTOM detection: PASSED")
    
    # Test 5: Multi-object tracking
    print("\n[6/6] Testing multi-object tracking...")
    tracker.reset()
    
    # Track 3 objects simultaneously
    objects = {
        "car_1": [(100 + i*15, 200) for i in range(20)],      # Left to right
        "person_5": [(500 - i*12, 300) for i in range(20)],   # Right to left
        "bicycle_1": [(300, 150 + i*8) for i in range(20)]    # Top to bottom
    }
    
    print("  Tracking 3 objects simultaneously...")
    
    # Update all objects frame by frame
    for frame_idx in range(20):
        for obj_id, positions in objects.items():
            if frame_idx < len(positions):
                tracker.update(obj_id, positions[frame_idx])
    
    # Check results
    active_tracks = tracker.get_active_tracks()
    print(f"  Active tracks: {len(active_tracks)}")
    
    for obj_id, track_info in active_tracks.items():
        print(f"    {obj_id}: {track_info.current_direction.value}")
    
    # Verify directions
    assert tracker.get_track_info("car_1").current_direction == Direction.LEFT_TO_RIGHT
    assert tracker.get_track_info("person_5").current_direction == Direction.RIGHT_TO_LEFT
    assert tracker.get_track_info("bicycle_1").current_direction == Direction.TOP_TO_BOTTOM
    
    print("      ✓ Multi-object tracking: PASSED")
    
    # Test helper methods
    print("\n" + "=" * 70)
    print("Testing Helper Methods")
    print("=" * 70)
    
    rtl_objects = tracker.get_objects_by_direction(Direction.RIGHT_TO_LEFT)
    print(f"\n✓ Objects moving RIGHT-TO-LEFT: {len(rtl_objects)}")
    for track in rtl_objects:
        print(f"  - {track.object_id}")
    
    fastest = tracker.get_fastest_object()
    print(f"\n✓ Fastest object: {fastest.object_id}")
    print(f"  Velocity magnitude: {(fastest.velocity[0]**2 + fastest.velocity[1]**2)**0.5:.1f} px/s")
    
    print(f"\n✓ Total tracks: {tracker.get_track_count()}")
    print(f"✓ Active tracks: {tracker.get_active_track_count()}")
    
    # Success
    print("\n" + "=" * 70)
    print("✓ All Tests Passed!")
    print("=" * 70)
    print("\nMotion Tracker is ready for:")
    print("  • Real-time direction detection")
    print("  • Multi-object tracking")
    print("  • Velocity calculations")
    print("  • Integration with PTZ automation")
    print("\nNext steps:")
    print("  1. Create video stream handler (Task 8)")
    print("  2. Build tracking engine to coordinate detector + tracker + PTZ")
    print("  3. Test with live camera feed")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
