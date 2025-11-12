"""
Test Video Stream Handler

Tests RTSP stream capture with your IP cameras or test video file.

Usage:
    # Test with camera RTSP stream
    python scripts/test_stream_handler.py --rtsp rtsp://admin:password@192.168.1.100:554/stream1
    
    # Test with video file
    python scripts/test_stream_handler.py --file path/to/video.mp4
    
    # Test with webcam
    python scripts/test_stream_handler.py --camera 0
"""

import sys
import argparse
import time
import cv2
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.video.stream_handler import VideoStreamHandler


def test_stream(stream_url: str, duration: int = 10, display: bool = True):
    """
    Test video stream handler
    
    Args:
        stream_url: RTSP URL, file path, or camera index
        duration: How long to run test (seconds)
        display: Whether to display video window
    """
    print("=" * 70)
    print("Video Stream Handler Test")
    print("=" * 70)
    
    print(f"\nStream URL: {stream_url}")
    print(f"Test duration: {duration} seconds")
    print(f"Display video: {display}")
    
    # Initialize stream handler
    print("\n[1/3] Initializing stream handler...")
    
    try:
        stream = VideoStreamHandler(
            stream_url=stream_url,
            buffer_size=30,
            reconnect=True,
            reconnect_delay=3.0,
            name="TestStream"
        )
        
        print("      ✓ Stream handler initialized")
        
    except Exception as e:
        print(f"\n✗ Failed to initialize stream handler: {e}")
        return 1
    
    # Start stream
    print("\n[2/3] Starting video stream...")
    
    try:
        stream.start()
        print("      ✓ Stream started")
        
        # Get initial stats
        stats = stream.get_stats()
        width, height = stats.resolution
        print(f"      Resolution: {width}x{height}")
        print(f"      FPS: {stats.fps:.1f}")
        
    except Exception as e:
        print(f"\n✗ Failed to start stream: {e}")
        print("\nTroubleshooting:")
        print("  1. Check camera IP and credentials")
        print("  2. Verify RTSP port (usually 554)")
        print("  3. Test RTSP URL in VLC player first")
        print("  4. Check network connectivity")
        return 1
    
    # Read and process frames
    print("\n[3/3] Reading frames from stream...")
    print("      Press 'q' to quit early\n")
    
    start_time = time.time()
    frame_count = 0
    last_stats_time = start_time
    
    try:
        while True:
            # Check duration
            elapsed = time.time() - start_time
            if elapsed >= duration:
                print(f"\n      ✓ Test duration reached ({duration}s)")
                break
            
            # Read frame
            frame = stream.read(timeout=1.0)
            
            if frame is None:
                print("      Warning: No frame received (timeout)")
                continue
            
            frame_count += 1
            
            # Print stats every 2 seconds
            if time.time() - last_stats_time >= 2.0:
                stats = stream.get_stats()
                
                print(
                    f"      Frames: {frame_count:4d} | "
                    f"Received: {stats.frames_received:5d} | "
                    f"Dropped: {stats.frames_dropped:3d} | "
                    f"FPS: {stats.fps:5.1f} | "
                    f"Connected: {stats.is_connected}"
                )
                
                last_stats_time = time.time()
            
            # Display frame
            if display:
                # Draw stats on frame
                cv2.putText(
                    frame,
                    f"Frame: {frame_count}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2
                )
                
                cv2.putText(
                    frame,
                    f"FPS: {stats.fps:.1f}",
                    (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2
                )
                
                cv2.imshow('Stream Test', frame)
                
                # Check for quit
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("\n      Stopped by user")
                    break
    
    except KeyboardInterrupt:
        print("\n      Stopped by user (Ctrl+C)")
    
    except Exception as e:
        print(f"\n✗ Error during stream processing: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        if display:
            cv2.destroyAllWindows()
        
        stream.stop()
    
    # Final statistics
    stats = stream.get_stats()
    elapsed = time.time() - start_time
    
    print("\n" + "=" * 70)
    print("Test Results")
    print("=" * 70)
    
    print(f"\n✓ Test completed successfully")
    print(f"\nDuration: {elapsed:.1f} seconds")
    print(f"Frames processed: {frame_count}")
    print(f"Frames received: {stats.frames_received}")
    print(f"Frames dropped: {stats.frames_dropped}")
    print(f"Average FPS: {frame_count / elapsed:.1f}")
    print(f"Reconnection attempts: {stats.reconnect_attempts}")
    
    if stats.frames_dropped > 0:
        drop_rate = (stats.frames_dropped / stats.frames_received) * 100
        print(f"\nFrame drop rate: {drop_rate:.1f}%")
        
        if drop_rate > 10:
            print("  Warning: High frame drop rate detected")
            print("  Consider: Increasing buffer size or reducing resolution")
    
    print("\n" + "=" * 70)
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        description='Test video stream handler',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Stream source options
    parser.add_argument(
        '--rtsp',
        help='RTSP URL (e.g., rtsp://admin:password@192.168.1.100:554/stream1)'
    )
    
    parser.add_argument(
        '--file',
        help='Video file path'
    )
    
    parser.add_argument(
        '--camera',
        type=int,
        help='Camera index (e.g., 0 for default webcam)'
    )
    
    # Camera shortcuts
    parser.add_argument(
        '--camera1',
        action='store_true',
        help='Use Camera 1 (192.168.1.107:8080) with default credentials'
    )
    
    parser.add_argument(
        '--camera2',
        action='store_true',
        help='Use Camera 2 (192.168.1.123:80) with default credentials'
    )
    
    # Test options
    parser.add_argument(
        '--duration',
        type=int,
        default=10,
        help='Test duration in seconds (default: 10)'
    )
    
    parser.add_argument(
        '--no-display',
        action='store_true',
        help='Disable video display window'
    )
    
    args = parser.parse_args()
    
    # Determine stream URL
    stream_url = None
    
    if args.camera1:
        # Camera 1 shortcut - try common RTSP paths
        # Many cameras use /stream1, /live, /h264, or manufacturer-specific paths
        stream_url = "rtsp://admin:admin@192.168.1.107:554/live"
        print("Using Camera 1 (192.168.1.107)")
        print("Note: RTSP path may vary by camera model")
        print("      Trying: /live")
        print("      If this fails, try: /stream1, /h264, /main, /ch0, /onvif1")
        
    elif args.camera2:
        # Camera 2 shortcut
        stream_url = "rtsp://admin:123456@192.168.1.123:554/live"
        print("Using Camera 2 (192.168.1.123)")
        
    elif args.rtsp:
        stream_url = args.rtsp
        
    elif args.file:
        stream_url = args.file
        
    elif args.camera is not None:
        stream_url = args.camera
    
    else:
        print("Error: No stream source specified")
        print("Use --camera1, --camera2, --rtsp, --file, or --camera")
        return 1
    
    # Run test
    return test_stream(
        stream_url=stream_url,
        duration=args.duration,
        display=not args.no_display
    )


if __name__ == "__main__":
    sys.exit(main())
