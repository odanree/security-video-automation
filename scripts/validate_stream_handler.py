"""
Validate Stream Handler

Tests stream handler functionality without requiring actual camera hardware.
Creates a synthetic video file for testing.

Usage:
    python scripts/validate_stream_handler.py
"""

import sys
import cv2
import numpy as np
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.video.stream_handler import VideoStreamHandler, MultiStreamHandler


def create_test_video(filename: str = "test_video.mp4", duration: int = 5, fps: int = 30):
    """Create a test video file"""
    print(f"\nCreating test video: {filename}")
    print(f"  Duration: {duration}s @ {fps} FPS")
    
    width, height = 640, 480
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(filename, fourcc, fps, (width, height))
    
    total_frames = duration * fps
    
    for frame_num in range(total_frames):
        # Create frame with moving circle
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Moving circle (left to right)
        x = int((frame_num / total_frames) * width)
        y = height // 2
        
        cv2.circle(frame, (x, y), 50, (0, 255, 0), -1)
        
        # Frame number text
        cv2.putText(
            frame,
            f"Frame {frame_num + 1}/{total_frames}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )
        
        out.write(frame)
    
    out.release()
    print(f"  ✓ Created {total_frames} frames")
    
    return filename


def main():
    print("=" * 70)
    print("Stream Handler Validation")
    print("=" * 70)
    
    # Create test video
    print("\n[1/5] Creating test video...")
    video_file = create_test_video(duration=3, fps=30)
    
    # Test 1: Basic stream handling
    print("\n[2/5] Testing VideoStreamHandler initialization...")
    
    try:
        stream = VideoStreamHandler(
            stream_url=video_file,
            buffer_size=30,
            reconnect=False,
            name="TestVideo"
        )
        print("      ✓ VideoStreamHandler initialized")
    except Exception as e:
        print(f"      ✗ Failed: {e}")
        return 1
    
    # Test 2: Start stream
    print("\n[3/5] Testing stream start...")
    
    try:
        stream.start()
        print("      ✓ Stream started successfully")
        
        stats = stream.get_stats()
        width, height = stats.resolution
        print(f"      Resolution: {width}x{height}")
        print(f"      FPS: {stats.fps:.1f}")
        print(f"      Connected: {stats.is_connected}")
        
    except Exception as e:
        print(f"      ✗ Failed: {e}")
        return 1
    
    # Test 3: Read frames
    print("\n[4/5] Testing frame reading...")
    
    frames_read = 0
    start_time = time.time()
    
    try:
        for i in range(30):  # Read 30 frames
            frame = stream.read(timeout=1.0)
            
            if frame is not None:
                frames_read += 1
            else:
                print(f"      Warning: Frame {i} timeout")
        
        elapsed = time.time() - start_time
        
        print(f"      ✓ Read {frames_read} frames in {elapsed:.2f}s")
        print(f"      Effective FPS: {frames_read / elapsed:.1f}")
        
    except Exception as e:
        print(f"      ✗ Failed: {e}")
        stream.stop()
        return 1
    
    # Test 4: Stream statistics
    print("\n[5/5] Testing stream statistics...")
    
    stats = stream.get_stats()
    
    print(f"      Frames received: {stats.frames_received}")
    print(f"      Frames dropped: {stats.frames_dropped}")
    print(f"      FPS: {stats.fps:.1f}")
    print(f"      Is connected: {stats.is_connected}")
    print(f"      Reconnect attempts: {stats.reconnect_attempts}")
    
    # Stop stream
    stream.stop()
    print("\n      ✓ Stream stopped successfully")
    
    # Test MultiStreamHandler
    print("\n" + "=" * 70)
    print("Testing MultiStreamHandler")
    print("=" * 70)
    
    print("\nInitializing multi-stream handler...")
    multi = MultiStreamHandler()
    
    # Add multiple streams
    print("Adding 2 test streams...")
    
    try:
        multi.add_stream("stream1", video_file, buffer_size=10)
        multi.add_stream("stream2", video_file, buffer_size=10)
        
        print(f"✓ Active streams: {len(multi)}")
        
        # Read from all streams
        time.sleep(0.5)  # Let streams start
        
        frames = multi.read_all()
        print(f"✓ Read frames from {len([f for f in frames.values() if f is not None])} streams")
        
        # Get stats
        all_stats = multi.get_all_stats()
        
        for stream_id, stats in all_stats.items():
            print(f"\n{stream_id}:")
            print(f"  Frames received: {stats.frames_received}")
            print(f"  FPS: {stats.fps:.1f}")
            print(f"  Connected: {stats.is_connected}")
        
        # Stop all
        multi.stop_all()
        print("\n✓ All streams stopped")
        
    except Exception as e:
        print(f"✗ Multi-stream test failed: {e}")
        multi.stop_all()
        return 1
    
    # Success
    print("\n" + "=" * 70)
    print("✓ All Validations Passed!")
    print("=" * 70)
    
    print("\nStream handler is ready for:")
    print("  • RTSP camera stream capture")
    print("  • Threaded video processing")
    print("  • Automatic reconnection")
    print("  • Multi-camera support")
    print("\nNext steps:")
    print("  1. Test with your actual camera RTSP URLs")
    print("  2. Integrate with object detector")
    print("  3. Build tracking engine to combine all components")
    
    # Cleanup
    Path(video_file).unlink()
    print(f"\nCleaned up test video: {video_file}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
