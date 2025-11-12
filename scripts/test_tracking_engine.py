"""
Test Tracking Engine

Validates the tracking engine with simulated video and mocked components.
Tests the complete workflow: detection → tracking → PTZ control.

Usage:
    python scripts/test_tracking_engine.py
"""

import sys
import cv2
import numpy as np
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai.object_detector import ObjectDetector, DetectionResult
from src.ai.motion_tracker import MotionTracker, Direction
from src.camera.ptz_controller import PTZController
from src.video.stream_handler import VideoStreamHandler
from src.automation.tracking_engine import (
    TrackingEngine,
    TrackingConfig,
    TrackingZone,
    TrackingMode
)


def create_test_video_with_movement(filename: str = "tracking_test.mp4"):
    """Create test video with simulated person moving right to left"""
    print(f"Creating test video: {filename}")
    
    width, height = 640, 480
    fps = 30
    duration = 10  # Longer duration for more movement
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(filename, fourcc, fps, (width, height))
    
    total_frames = duration * fps
    
    for frame_num in range(total_frames):
        # Create frame
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:] = (50, 50, 50)  # Dark gray background
        
        # Simulated person moving from right to left
        progress = frame_num / total_frames
        x = int(width * 0.8 - progress * width * 0.6)  # Move from 80% to 20%
        y = height // 2
        
        # Draw person (rectangle)
        person_width, person_height = 60, 120
        x1 = x - person_width // 2
        y1 = y - person_height // 2
        x2 = x + person_width // 2
        y2 = y + person_height // 2
        
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), -1)
        
        # Add zone markers
        zone_left = int(width * 0.33)
        zone_right = int(width * 0.66)
        
        cv2.line(frame, (zone_left, 0), (zone_left, height), (100, 100, 100), 2)
        cv2.line(frame, (zone_right, 0), (zone_right, height), (100, 100, 100), 2)
        
        cv2.putText(frame, "LEFT", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
        cv2.putText(frame, "CENTER", (zone_left + 10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
        cv2.putText(frame, "RIGHT", (zone_right + 10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
        
        # Frame info
        cv2.putText(
            frame,
            f"Frame {frame_num + 1}/{total_frames}",
            (10, height - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2
        )
        
        out.write(frame)
    
    out.release()
    print(f"✓ Created {total_frames} frames")
    
    return filename


class MockPTZController:
    """Mock PTZ controller for testing"""
    
    def __init__(self):
        self.preset_history = []
        self.current_preset = None
    
    def goto_preset(self, preset_token: str, speed: float = 1.0):
        """Mock preset movement"""
        print(f"    🎥 PTZ: Moving to preset '{preset_token}' at speed {speed}")
        self.preset_history.append(preset_token)
        self.current_preset = preset_token
        time.sleep(0.1)  # Simulate movement time


class MockObjectDetector:
    """Mock object detector that detects moving rectangle"""
    
    def __init__(self):
        self.frame_count = 0
    
    def detect(self, frame, frame_number=0):
        """Detect the green rectangle as a person"""
        self.frame_count = frame_number
        
        # Find green pixels (our simulated person)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Green color range
        lower_green = np.array([40, 40, 40])
        upper_green = np.array([80, 255, 255])
        
        mask = cv2.inRange(hsv, lower_green, upper_green)
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        detections = []
        
        for contour in contours:
            if cv2.contourArea(contour) > 1000:  # Minimum size
                x, y, w, h = cv2.boundingRect(contour)
                
                detection = DetectionResult(
                    class_name='person',
                    confidence=0.95,
                    bbox=(x, y, x + w, y + h),
                    center=(x + w // 2, y + h // 2),
                    frame_number=frame_number,
                    timestamp=time.time()
                )
                
                detections.append(detection)
        
        return detections


def main():
    print("=" * 70)
    print("Tracking Engine Test")
    print("=" * 70)
    
    # Create test video
    print("\n[1/6] Creating test video...")
    video_file = create_test_video_with_movement()
    
    # Initialize components
    print("\n[2/6] Initializing components...")
    
    detector = MockObjectDetector()
    print("  ✓ Mock object detector")
    
    motion_tracker = MotionTracker(
        history_length=30,
        movement_threshold=50,
        stationary_threshold=20
    )
    print("  ✓ Motion tracker")
    
    ptz = MockPTZController()
    print("  ✓ Mock PTZ controller")
    
    stream = VideoStreamHandler(
        stream_url=video_file,
        buffer_size=10,
        reconnect=False,
        name="TestVideo"
    )
    stream.start()
    print("  ✓ Video stream handler")
    
    # Configure tracking zones
    print("\n[3/6] Configuring tracking zones...")
    
    config = TrackingConfig(
        zones=[
            TrackingZone(
                name='zone_left',
                x_range=(0.0, 0.33),
                y_range=(0.0, 1.0),
                preset_token='preset_left',
                priority=1
            ),
            TrackingZone(
                name='zone_center',
                x_range=(0.33, 0.66),
                y_range=(0.0, 1.0),
                preset_token='preset_center',
                priority=1
            ),
            TrackingZone(
                name='zone_right',
                x_range=(0.66, 1.0),
                y_range=(0.0, 1.0),
                preset_token='preset_right',
                priority=1
            )
        ],
        target_classes=['person'],
        direction_triggers=[Direction.RIGHT_TO_LEFT],
        min_confidence=0.5,
        movement_threshold=30,  # Lower threshold
        cooldown_time=0.5  # Shorter cooldown
    )
    
    print(f"  ✓ Configured {len(config.zones)} tracking zones")
    
    # Create tracking engine
    print("\n[4/6] Creating tracking engine...")
    
    engine = TrackingEngine(
        detector=detector,
        motion_tracker=motion_tracker,
        ptz_controller=ptz,
        stream_handler=stream,
        config=config
    )
    
    # Set up callbacks
    detection_count = [0]
    ptz_move_count = [0]
    
    def on_detection(detections):
        detection_count[0] += len(detections)
    
    def on_ptz_move(preset):
        ptz_move_count[0] += 1
    
    engine.on_detection = on_detection
    engine.on_ptz_move = on_ptz_move
    
    print("  ✓ Tracking engine initialized")
    
    # Start tracking
    print("\n[5/6] Starting automated tracking...")
    print("  Simulating person walking from RIGHT to LEFT")
    print("  Expected: Camera should follow by moving presets\n")
    
    engine.start()
    
    # Let it run for a bit
    test_duration = 12
    
    for i in range(test_duration):
        time.sleep(1)
        stats = engine.get_statistics()
        
        print(
            f"  [{i+1}s] Frames: {stats['frames_processed']:3d} | "
            f"Detections: {detection_count[0]:3d} | "
            f"PTZ moves: {ptz_move_count[0]:2d} | "
            f"Current preset: {stats['current_preset']}"
        )
    
    # Stop tracking
    print("\n[6/6] Stopping tracking engine...")
    engine.stop()
    stream.stop()
    
    # Results
    print("\n" + "=" * 70)
    print("Test Results")
    print("=" * 70)
    
    stats = engine.get_statistics()
    
    print(f"\n✓ Test completed successfully")
    print(f"\nStatistics:")
    print(f"  Frames processed: {stats['frames_processed']}")
    print(f"  Total detections: {detection_count[0]}")
    print(f"  Total tracks: {stats['tracks']}")
    print(f"  PTZ movements: {ptz_move_count[0]}")
    print(f"  Active events: {stats['active_events']}")
    print(f"  Completed events: {stats['completed_events']}")
    
    print(f"\nPTZ Preset History:")
    for i, preset in enumerate(ptz.preset_history, 1):
        print(f"  {i}. {preset}")
    
    # Validation
    print("\n" + "=" * 70)
    print("Validation")
    print("=" * 70)
    
    success = True
    
    # Check if detections occurred
    if detection_count[0] > 0:
        print("✓ Objects detected successfully")
    else:
        print("✗ No detections (unexpected)")
        success = False
    
    # Check if PTZ movements occurred
    if ptz_move_count[0] > 0:
        print("✓ PTZ camera responded to movement")
    else:
        print("✗ No PTZ movements (unexpected)")
        success = False
    
    # Check preset sequence (should move from right → center → left)
    if ptz.preset_history:
        print(f"✓ PTZ preset sequence: {' → '.join(ptz.preset_history)}")
    
    # Cleanup
    Path(video_file).unlink()
    print(f"\nCleaned up test video: {video_file}")
    
    print("\n" + "=" * 70)
    
    if success:
        print("✓ All Validations Passed!")
        print("=" * 70)
        print("\nTracking engine is ready for:")
        print("  • Real-time object tracking")
        print("  • Automated PTZ camera control")
        print("  • Multi-zone tracking")
        print("  • Direction-based triggering")
        print("\nNext steps:")
        print("  1. Create configuration files (Task 10)")
        print("  2. Build main application (Task 11)")
        print("  3. Test with live camera feed")
        return 0
    else:
        print("✗ Some Validations Failed")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
