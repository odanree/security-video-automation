"""
AI Module

Object detection and motion tracking for automated PTZ camera control.
"""

from .object_detector import ObjectDetector, DetectionResult
from .motion_tracker import MotionTracker, MultiObjectTracker, Direction, TrackInfo

__all__ = [
    'ObjectDetector',
    'DetectionResult',
    'MotionTracker',
    'MultiObjectTracker',
    'Direction',
    'TrackInfo'
]
