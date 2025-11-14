"""
Unit tests for Object Detector

Tests YOLO detection, filtering, and visualization.
"""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from src.ai.object_detector import ObjectDetector, DetectionResult


@pytest.fixture
def sample_frame():
    """Create a sample video frame (640x480 BGR)"""
    return np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)


@pytest.fixture
def detector():
    """Create object detector with mocked YOLO model"""
    with patch('src.ai.object_detector.YOLO'):
        detector = ObjectDetector(
            model_path='yolov8n.pt',
            confidence_threshold=0.5
        )
    return detector


class TestDetectorInit:
    """Test detector initialization"""
    
    def test_initialization(self, detector):
        """Test successful detector initialization"""
        assert detector.confidence_threshold == 0.5
        assert detector.model is not None
    
    def test_custom_confidence_threshold(self):
        """Test initialization with custom confidence threshold"""
        with patch('src.ai.object_detector.YOLO'):
            detector = ObjectDetector(
                model_path='yolov8n.pt',
                confidence_threshold=0.7
            )
            assert detector.confidence_threshold == 0.7


class TestDetection:
    """Test object detection"""
    
    def test_detect_empty_frame(self, detector, sample_frame):
        """Test detection on frame with no objects"""
        detector.model.return_value = MagicMock()
        detector.model.return_value[0].boxes = []
        
        # Mock the return
        mock_results = MagicMock()
        mock_results[0].boxes = []
        detector.model.return_value = [mock_results]
        
        detections = detector.detect(sample_frame)
        
        assert len(detections) == 0
    
    def test_detect_person(self, detector, sample_frame):
        """Test detection of person"""
        # Create mock detection result
        mock_box = MagicMock()
        mock_box.cls = [0]  # Class 0 = person in COCO
        mock_box.conf = [0.9]  # Confidence 0.9
        mock_box.xyxy = [[100, 100, 200, 300]]  # Bounding box
        
        mock_results = MagicMock()
        mock_results.boxes = [mock_box]
        mock_results.names = {0: 'person', 1: 'bicycle'}
        
        detector.model.return_value = [mock_results]
        
        detections = detector.detect(sample_frame)
        
        assert len(detections) > 0
    
    def test_detect_multiple_objects(self, detector, sample_frame):
        """Test detection of multiple objects"""
        # Create multiple mock detections
        mock_box1 = MagicMock()
        mock_box1.cls = [0]  # Person
        mock_box1.conf = [0.9]
        mock_box1.xyxy = [[100, 100, 200, 300]]
        
        mock_box2 = MagicMock()
        mock_box2.cls = [0]  # Person
        mock_box2.conf = [0.8]
        mock_box2.xyxy = [[300, 150, 450, 400]]
        
        mock_results = MagicMock()
        mock_results.boxes = [mock_box1, mock_box2]
        mock_results.names = {0: 'person'}
        
        detector.model.return_value = [mock_results]
        
        detections = detector.detect(sample_frame)
        
        assert len(detections) == 2


class TestConfidenceFiltering:
    """Test confidence filtering"""
    
    def test_filter_low_confidence(self, detector, sample_frame):
        """Test filtering of low confidence detections"""
        # Create detection below threshold
        mock_box = MagicMock()
        mock_box.cls = [0]
        mock_box.conf = [0.3]  # Below 0.5 threshold
        mock_box.xyxy = [[100, 100, 200, 300]]
        
        mock_results = MagicMock()
        mock_results.boxes = [mock_box]
        mock_results.names = {0: 'person'}
        
        detector.model.return_value = [mock_results]
        detector.confidence_threshold = 0.5
        
        detections = detector.detect(sample_frame)
        
        # Should be filtered out
        assert len(detections) == 0
    
    def test_filter_high_confidence(self, detector, sample_frame):
        """Test keeping high confidence detections"""
        mock_box = MagicMock()
        mock_box.cls = [0]
        mock_box.conf = [0.9]  # Above 0.5 threshold
        mock_box.xyxy = [[100, 100, 200, 300]]
        
        mock_results = MagicMock()
        mock_results.boxes = [mock_box]
        mock_results.names = {0: 'person'}
        
        detector.model.return_value = [mock_results]
        detector.confidence_threshold = 0.5
        
        detections = detector.detect(sample_frame)
        
        # Should be kept
        assert len(detections) > 0


class TestDetectionResult:
    """Test DetectionResult dataclass"""
    
    def test_detection_result_creation(self):
        """Test creating a detection result"""
        result = DetectionResult(
            class_name='person',
            confidence=0.95,
            bbox=(100, 100, 200, 300),
            center=(150, 200),
            frame_number=0,
            timestamp=0.0
        )
        
        assert result.class_name == 'person'
        assert result.confidence == 0.95
        assert result.bbox == (100, 100, 200, 300)
        assert result.center == (150, 200)
    
    def test_detection_result_center_calculation(self):
        """Test that center is calculated correctly from bbox"""
        bbox = (100, 100, 200, 300)
        center_x = (bbox[0] + bbox[2]) // 2
        center_y = (bbox[1] + bbox[3]) // 2
        
        assert center_x == 150
        assert center_y == 200


class TestClassFiltering:
    """Test filtering by class"""
    
    def test_filter_by_target_classes(self, detector, sample_frame):
        """Test filtering to only target classes"""
        detector.target_classes = ['person']
        
        # Create car detection (not in target classes)
        mock_box = MagicMock()
        mock_box.cls = [2]  # Car class
        mock_box.conf = [0.9]
        mock_box.xyxy = [[100, 100, 200, 300]]
        
        mock_results = MagicMock()
        mock_results.boxes = [mock_box]
        mock_results.names = {0: 'person', 2: 'car'}
        
        detector.model.return_value = [mock_results]
        
        detections = detector.detect(sample_frame)
        
        # Should be filtered out (car not in target_classes)
        assert len(detections) == 0


class TestVisualization:
    """Test detection visualization"""
    
    def test_draw_detections(self, detector, sample_frame):
        """Test drawing detections on frame"""
        detection = DetectionResult(
            class_name='person',
            confidence=0.95,
            bbox=(100, 100, 200, 300),
            center=(150, 200),
            frame_number=0,
            timestamp=0.0
        )
        
        frame_with_detections = detector.draw_detections(
            sample_frame.copy(),
            [detection]
        )
        
        # Should return a frame
        assert frame_with_detections is not None
        assert frame_with_detections.shape == sample_frame.shape
    
    def test_draw_multiple_detections(self, detector, sample_frame):
        """Test drawing multiple detections"""
        detections = [
            DetectionResult('person', 0.95, (100, 100, 200, 300), (150, 200), 0, 0.0),
            DetectionResult('person', 0.85, (300, 150, 450, 400), (375, 275), 0, 0.0),
        ]
        
        frame_with_detections = detector.draw_detections(
            sample_frame.copy(),
            detections
        )
        
        assert frame_with_detections is not None
        assert frame_with_detections.shape == sample_frame.shape


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_detect_on_very_small_frame(self, detector):
        """Test detection on very small frame"""
        small_frame = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        
        mock_results = MagicMock()
        mock_results.boxes = []
        detector.model.return_value = [mock_results]
        
        detections = detector.detect(small_frame)
        
        assert isinstance(detections, list)
    
    def test_detect_on_very_large_frame(self, detector):
        """Test detection on very large frame"""
        large_frame = np.random.randint(0, 256, (1080, 1920, 3), dtype=np.uint8)
        
        mock_results = MagicMock()
        mock_results.boxes = []
        detector.model.return_value = [mock_results]
        
        detections = detector.detect(large_frame)
        
        assert isinstance(detections, list)
    
    def test_detect_with_zero_confidence_threshold(self, detector, sample_frame):
        """Test with confidence threshold of 0 (should accept all)"""
        detector.confidence_threshold = 0.0
        
        mock_box = MagicMock()
        mock_box.cls = [0]
        mock_box.conf = [0.01]  # Very low confidence
        mock_box.xyxy = [[100, 100, 200, 300]]
        
        mock_results = MagicMock()
        mock_results.boxes = [mock_box]
        mock_results.names = {0: 'person'}
        
        detector.model.return_value = [mock_results]
        
        detections = detector.detect(sample_frame)
        
        # Should be kept (threshold is 0)
        assert len(detections) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
