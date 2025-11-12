"""
Test Object Detector

Quick test script to validate YOLOv8 object detection on webcam or test image.

Usage:
    # Test with webcam (default)
    python scripts/test_object_detector.py
    
    # Test with image file
    python scripts/test_object_detector.py --image path/to/image.jpg
    
    # Test with video file
    python scripts/test_object_detector.py --video path/to/video.mp4
    
    # Use different model (faster/slower)
    python scripts/test_object_detector.py --model yolov8s.pt
    
    # Adjust confidence threshold
    python scripts/test_object_detector.py --confidence 0.7
"""

import cv2
import sys
import argparse
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai.object_detector import ObjectDetector


def test_webcam(detector: ObjectDetector, camera_index: int = 0):
    """Test detector on webcam feed"""
    print(f"\nTesting with webcam (camera {camera_index})...")
    print("Press 'q' to quit\n")
    
    cap = cv2.VideoCapture(camera_index)
    
    if not cap.isOpened():
        print(f"✗ Failed to open webcam {camera_index}")
        return False
    
    frame_count = 0
    fps_start = time.time()
    
    try:
        while True:
            ret, frame = cap.read()
            
            if not ret:
                print("✗ Failed to read frame from webcam")
                break
            
            frame_count += 1
            
            # Run detection
            detections = detector.detect(frame, frame_number=frame_count)
            
            # Draw detections
            annotated_frame = detector.draw_detections(
                frame,
                detections,
                show_confidence=True,
                show_track_id=False
            )
            
            # Calculate FPS
            elapsed = time.time() - fps_start
            fps = frame_count / elapsed if elapsed > 0 else 0
            
            # Draw FPS
            cv2.putText(
                annotated_frame,
                f"FPS: {fps:.1f} | Detections: {len(detections)}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )
            
            # Show frame
            cv2.imshow('Object Detection Test', annotated_frame)
            
            # Print detections
            if detections:
                print(f"Frame {frame_count}: {len(detections)} detections")
                for det in detections:
                    print(f"  - {det.class_name}: {det.confidence:.2f} at {det.center}")
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    except KeyboardInterrupt:
        print("\nStopped by user")
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
    
    print(f"\n✓ Processed {frame_count} frames")
    print(f"  Average FPS: {fps:.1f}")
    
    return True


def test_image(detector: ObjectDetector, image_path: str):
    """Test detector on static image"""
    print(f"\nTesting with image: {image_path}...")
    
    frame = cv2.imread(image_path)
    
    if frame is None:
        print(f"✗ Failed to load image: {image_path}")
        return False
    
    print(f"✓ Image loaded: {frame.shape[1]}x{frame.shape[0]}")
    
    # Run detection
    start_time = time.time()
    detections = detector.detect(frame)
    inference_time = (time.time() - start_time) * 1000
    
    print(f"✓ Detection completed in {inference_time:.1f}ms")
    print(f"  Found {len(detections)} objects:")
    
    for i, det in enumerate(detections, 1):
        print(f"    {i}. {det.class_name}: {det.confidence:.2f} at {det.bbox}")
    
    # Draw detections
    annotated_frame = detector.draw_detections(frame, detections)
    
    # Display
    cv2.imshow('Object Detection Test', annotated_frame)
    print("\nPress any key to close...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    
    return True


def test_video(detector: ObjectDetector, video_path: str):
    """Test detector on video file"""
    print(f"\nTesting with video: {video_path}...")
    print("Press 'q' to quit\n")
    
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print(f"✗ Failed to open video: {video_path}")
        return False
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    print(f"✓ Video loaded: {total_frames} frames @ {fps:.1f} FPS")
    
    frame_count = 0
    detection_count = 0
    fps_start = time.time()
    
    try:
        while True:
            ret, frame = cap.read()
            
            if not ret:
                print("\n✓ Reached end of video")
                break
            
            frame_count += 1
            
            # Run detection
            detections = detector.detect(frame, frame_number=frame_count)
            detection_count += len(detections)
            
            # Draw detections
            annotated_frame = detector.draw_detections(frame, detections)
            
            # Calculate processing FPS
            elapsed = time.time() - fps_start
            processing_fps = frame_count / elapsed if elapsed > 0 else 0
            
            # Draw stats
            cv2.putText(
                annotated_frame,
                f"Frame: {frame_count}/{total_frames} | FPS: {processing_fps:.1f}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )
            
            # Show frame
            cv2.imshow('Object Detection Test', annotated_frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    except KeyboardInterrupt:
        print("\nStopped by user")
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
    
    elapsed = time.time() - fps_start
    avg_fps = frame_count / elapsed if elapsed > 0 else 0
    avg_detections = detection_count / frame_count if frame_count > 0 else 0
    
    print(f"\n✓ Processed {frame_count} frames in {elapsed:.1f}s")
    print(f"  Processing FPS: {avg_fps:.1f}")
    print(f"  Total detections: {detection_count}")
    print(f"  Average detections/frame: {avg_detections:.1f}")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Test YOLOv8 object detector',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--model',
        default='yolov8n.pt',
        help='YOLO model to use (default: yolov8n.pt - fastest)'
    )
    
    parser.add_argument(
        '--confidence',
        type=float,
        default=0.5,
        help='Confidence threshold 0.0-1.0 (default: 0.5)'
    )
    
    parser.add_argument(
        '--image',
        help='Path to test image'
    )
    
    parser.add_argument(
        '--video',
        help='Path to test video'
    )
    
    parser.add_argument(
        '--camera',
        type=int,
        default=0,
        help='Camera index for webcam test (default: 0)'
    )
    
    parser.add_argument(
        '--device',
        default='cpu',
        help='Device to run on: cpu, cuda, 0, 1, etc. (default: cpu)'
    )
    
    parser.add_argument(
        '--classes',
        nargs='+',
        help='Target classes to detect (default: person car truck bus motorcycle bicycle)'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Object Detector Test")
    print("=" * 60)
    
    # Initialize detector
    print(f"\nInitializing detector...")
    print(f"  Model: {args.model}")
    print(f"  Confidence: {args.confidence}")
    print(f"  Device: {args.device}")
    
    try:
        detector = ObjectDetector(
            model_path=args.model,
            confidence_threshold=args.confidence,
            target_classes=args.classes,
            device=args.device
        )
    except Exception as e:
        print(f"\n✗ Failed to initialize detector: {e}")
        print("\nTroubleshooting:")
        print("  1. Ensure ultralytics is installed: pip install ultralytics")
        print("  2. Model will auto-download on first use")
        print("  3. Check internet connection if model download fails")
        return 1
    
    # Run appropriate test
    success = False
    
    if args.image:
        success = test_image(detector, args.image)
    elif args.video:
        success = test_video(detector, args.video)
    else:
        success = test_webcam(detector, args.camera)
    
    print("\n" + "=" * 60)
    
    if success:
        print("✓ Test completed successfully")
        return 0
    else:
        print("✗ Test failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
