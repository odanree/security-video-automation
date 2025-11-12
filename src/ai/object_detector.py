"""
Object Detector using YOLOv8

Detects objects (persons, vehicles, etc.) in video frames using the YOLOv8 model.
Provides detection results with bounding boxes, confidence scores, and class labels.

Example:
    from src.ai.object_detector import ObjectDetector
    
    detector = ObjectDetector(model_path='yolov8n.pt', confidence=0.6)
    detections = detector.detect(frame)
    
    for detection in detections:
        print(f"{detection.class_name}: {detection.confidence:.2f}")
"""

import cv2
import numpy as np
import logging
from typing import List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

# YOLOv8 imports (will be imported dynamically to handle missing dependency)
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    YOLO = None


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DetectionResult:
    """
    Represents a detected object in a video frame
    
    Attributes:
        class_name: Object class (e.g., 'person', 'car', 'truck')
        confidence: Detection confidence (0.0 to 1.0)
        bbox: Bounding box coordinates (x1, y1, x2, y2)
        center: Center point of bounding box (x, y)
        frame_number: Frame number where object was detected
        timestamp: Unix timestamp of detection
        track_id: Optional tracking ID for multi-frame tracking
    """
    class_name: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    center: Tuple[int, int]           # (x, y)
    frame_number: int
    timestamp: float
    track_id: Optional[int] = None


class ObjectDetector:
    """
    Detect objects in video frames using YOLOv8
    
    Supports detection of multiple object classes including:
    - person
    - bicycle, car, motorcycle, bus, truck
    - And 75+ other COCO dataset classes
    """
    
    # COCO class names for common tracking targets
    DEFAULT_TARGET_CLASSES = [
        'person',
        'bicycle',
        'car',
        'motorcycle',
        'bus',
        'truck'
    ]
    
    def __init__(
        self,
        model_path: str = 'yolov8n.pt',
        confidence_threshold: float = 0.5,
        target_classes: Optional[List[str]] = None,
        device: str = 'cpu'
    ):
        """
        Initialize object detector
        
        Args:
            model_path: Path to YOLO model file
                       Available models: yolov8n.pt (nano), yolov8s.pt (small),
                       yolov8m.pt (medium), yolov8l.pt (large), yolov8x.pt (xlarge)
            confidence_threshold: Minimum confidence for detections (0.0 to 1.0)
            target_classes: List of class names to detect (None = use defaults)
            device: Device to run inference on ('cpu', 'cuda', '0', '1', etc.)
            
        Raises:
            ImportError: If ultralytics is not installed
            FileNotFoundError: If model file doesn't exist and auto-download fails
        """
        if not YOLO_AVAILABLE:
            raise ImportError(
                "ultralytics is not installed. "
                "Install it with: pip install ultralytics"
            )
        
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.target_classes = target_classes or self.DEFAULT_TARGET_CLASSES
        self.device = device
        
        logger.info(f"Loading YOLO model from {model_path}...")
        
        try:
            self.model = YOLO(model_path)
            self.model.to(device)
            
            # Get class names from model
            self.class_names = self.model.names
            
            logger.info(f"✓ Model loaded successfully on {device}")
            logger.info(f"  Target classes: {', '.join(self.target_classes)}")
            logger.info(f"  Confidence threshold: {confidence_threshold}")
            
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            raise
    
    def detect(
        self,
        frame: np.ndarray,
        frame_number: int = 0,
        timestamp: Optional[float] = None
    ) -> List[DetectionResult]:
        """
        Detect objects in a single frame
        
        Args:
            frame: OpenCV BGR image
            frame_number: Frame sequence number
            timestamp: Frame timestamp (Unix time)
            
        Returns:
            List of DetectionResult objects
            
        Example:
            detections = detector.detect(frame)
            for det in detections:
                x1, y1, x2, y2 = det.bbox
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        """
        import time
        
        if timestamp is None:
            timestamp = time.time()
        
        detections = []
        
        try:
            # Run inference
            results = self.model(frame, verbose=False)[0]
            
            # Process each detection
            for box in results.boxes:
                class_id = int(box.cls[0])
                class_name = self.class_names[class_id]
                confidence = float(box.conf[0])
                
                # Filter by confidence and target classes
                if (confidence >= self.confidence_threshold and
                    class_name in self.target_classes):
                    
                    # Get bounding box coordinates
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    
                    # Calculate center point
                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2
                    
                    # Get track ID if available (from tracking mode)
                    track_id = None
                    if hasattr(box, 'id') and box.id is not None:
                        track_id = int(box.id[0])
                    
                    detection = DetectionResult(
                        class_name=class_name,
                        confidence=confidence,
                        bbox=(x1, y1, x2, y2),
                        center=(center_x, center_y),
                        frame_number=frame_number,
                        timestamp=timestamp,
                        track_id=track_id
                    )
                    
                    detections.append(detection)
            
            logger.debug(f"Frame {frame_number}: Detected {len(detections)} objects")
            
        except Exception as e:
            logger.error(f"Detection failed on frame {frame_number}: {e}")
        
        return detections
    
    def detect_and_track(
        self,
        frame: np.ndarray,
        frame_number: int = 0,
        timestamp: Optional[float] = None
    ) -> List[DetectionResult]:
        """
        Detect and track objects across frames
        
        Uses YOLO's built-in tracking to assign consistent IDs to objects
        across multiple frames.
        
        Args:
            frame: OpenCV BGR image
            frame_number: Frame sequence number
            timestamp: Frame timestamp
            
        Returns:
            List of DetectionResult objects with track_id populated
        """
        import time
        
        if timestamp is None:
            timestamp = time.time()
        
        detections = []
        
        try:
            # Run tracking (built-in to YOLOv8)
            results = self.model.track(frame, persist=True, verbose=False)[0]
            
            if results.boxes is None or len(results.boxes) == 0:
                return detections
            
            for box in results.boxes:
                class_id = int(box.cls[0])
                class_name = self.class_names[class_id]
                confidence = float(box.conf[0])
                
                if (confidence >= self.confidence_threshold and
                    class_name in self.target_classes):
                    
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2
                    
                    # Get track ID
                    track_id = None
                    if hasattr(box, 'id') and box.id is not None:
                        track_id = int(box.id[0])
                    
                    detection = DetectionResult(
                        class_name=class_name,
                        confidence=confidence,
                        bbox=(x1, y1, x2, y2),
                        center=(center_x, center_y),
                        frame_number=frame_number,
                        timestamp=timestamp,
                        track_id=track_id
                    )
                    
                    detections.append(detection)
            
            logger.debug(f"Frame {frame_number}: Tracked {len(detections)} objects")
            
        except Exception as e:
            logger.error(f"Tracking failed on frame {frame_number}: {e}")
        
        return detections
    
    def draw_detections(
        self,
        frame: np.ndarray,
        detections: List[DetectionResult],
        show_confidence: bool = True,
        show_track_id: bool = True,
        color: Tuple[int, int, int] = (0, 255, 0),
        thickness: int = 2
    ) -> np.ndarray:
        """
        Draw detection bounding boxes and labels on frame
        
        Args:
            frame: OpenCV BGR image
            detections: List of DetectionResult objects
            show_confidence: Show confidence score
            show_track_id: Show tracking ID
            color: BGR color tuple for boxes
            thickness: Line thickness
            
        Returns:
            Frame with drawn detections
        """
        annotated_frame = frame.copy()
        
        for detection in detections:
            x1, y1, x2, y2 = detection.bbox
            
            # Draw bounding box
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, thickness)
            
            # Build label text
            label_parts = [detection.class_name]
            
            if show_confidence:
                label_parts.append(f"{detection.confidence:.2f}")
            
            if show_track_id and detection.track_id is not None:
                label_parts.append(f"ID:{detection.track_id}")
            
            label = " ".join(label_parts)
            
            # Draw label background
            (label_width, label_height), _ = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
            )
            
            cv2.rectangle(
                annotated_frame,
                (x1, y1 - label_height - 10),
                (x1 + label_width, y1),
                color,
                -1
            )
            
            # Draw label text
            cv2.putText(
                annotated_frame,
                label,
                (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )
            
            # Draw center point
            cv2.circle(annotated_frame, detection.center, 5, color, -1)
        
        return annotated_frame
    
    def filter_by_class(
        self,
        detections: List[DetectionResult],
        class_names: List[str]
    ) -> List[DetectionResult]:
        """
        Filter detections by class name
        
        Args:
            detections: List of all detections
            class_names: List of class names to keep
            
        Returns:
            Filtered list of detections
        """
        return [d for d in detections if d.class_name in class_names]
    
    def get_largest_detection(
        self,
        detections: List[DetectionResult]
    ) -> Optional[DetectionResult]:
        """
        Get the detection with the largest bounding box area
        
        Useful for identifying the primary subject in frame.
        
        Args:
            detections: List of detections
            
        Returns:
            Detection with largest bbox, or None if no detections
        """
        if not detections:
            return None
        
        def bbox_area(detection: DetectionResult) -> int:
            x1, y1, x2, y2 = detection.bbox
            return (x2 - x1) * (y2 - y1)
        
        return max(detections, key=bbox_area)
    
    def get_closest_to_center(
        self,
        detections: List[DetectionResult],
        frame_shape: Tuple[int, int]
    ) -> Optional[DetectionResult]:
        """
        Get detection closest to frame center
        
        Args:
            detections: List of detections
            frame_shape: (height, width) of frame
            
        Returns:
            Detection closest to center, or None if no detections
        """
        if not detections:
            return None
        
        height, width = frame_shape[:2]
        frame_center = (width // 2, height // 2)
        
        def distance_to_center(detection: DetectionResult) -> float:
            cx, cy = detection.center
            dx = cx - frame_center[0]
            dy = cy - frame_center[1]
            return (dx ** 2 + dy ** 2) ** 0.5
        
        return min(detections, key=distance_to_center)
    
    def __repr__(self) -> str:
        """String representation"""
        return (
            f"ObjectDetector(model={self.model_path}, "
            f"confidence={self.confidence_threshold}, "
            f"device={self.device})"
        )
