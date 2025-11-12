# GitHub Copilot Instructions for Security Camera AI Automation

## Project Overview

This project integrates **AI-powered video analysis** with **PTZ (Pan-Tilt-Zoom) camera control** to automatically track subjects moving through the camera's field of view. The system detects motion direction (e.g., right-to-left movement) and triggers camera preset positions to maintain visual tracking of subjects.

## Architecture

### Core Components
1. **Video Stream Ingestion** - Capture live feed from IP camera (RTSP/HTTP)
2. **AI Object Detection** - Real-time person/vehicle detection using computer vision
3. **Motion Direction Analysis** - Track object trajectories and determine movement direction
4. **PTZ Camera Control** - API integration to control camera position via presets
5. **Tracking Logic** - Decision engine to trigger appropriate camera movements

### Technology Stack
- **Python 3.10+** - Primary language
- **OpenCV** - Video processing and stream handling
- **YOLO / TensorFlow / PyTorch** - Object detection models
- **ONVIF** - Standard protocol for IP camera control (PTZ)
- **Flask/FastAPI** - Web interface and API server (optional)
- **asyncio** - Asynchronous camera control and video processing

## Project Structure

**IMPORTANT: Keep root directory clean!** Only configuration files and documentation belong in root.

```
security-video-automation/
├── src/                           # All application code
│   ├── __init__.py
│   ├── main.py                    # Main entry point
│   ├── video/
│   │   ├── __init__.py
│   │   ├── stream_handler.py      # RTSP/HTTP stream capture
│   │   ├── frame_processor.py     # Video frame processing
│   │   └── recorder.py            # Optional recording functionality
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── object_detector.py     # AI model for detection (YOLO/etc)
│   │   ├── motion_tracker.py      # Track object movement & direction
│   │   └── models/                # Pre-trained AI models (gitignored)
│   │       └── .gitkeep
│   ├── camera/
│   │   ├── __init__.py
│   │   ├── ptz_controller.py      # PTZ camera API integration
│   │   ├── onvif_client.py        # ONVIF protocol client
│   │   ├── preset_manager.py      # Manage camera presets
│   │   └── camera_discovery.py    # Discover cameras on network
│   ├── automation/
│   │   ├── __init__.py
│   │   ├── tracking_engine.py     # Main tracking logic
│   │   ├── rules_engine.py        # Configurable tracking rules
│   │   └── event_logger.py        # Log tracking events
│   └── web/                       # Web dashboard
│       ├── __init__.py
│       ├── app.py                 # FastAPI application
│       ├── static/                # CSS, JS, images
│       │   ├── css/
│       │   ├── js/
│       │   ├── images/
│       │   └── demo/              # Demo assets
│       └── templates/             # HTML templates
│           ├── index.html
│           └── demo.html
├── config/                        # Configuration files
│   ├── camera_config.yaml         # Camera settings & presets
│   ├── ai_config.yaml             # AI model parameters
│   └── tracking_rules.yaml        # Movement rules & triggers
├── tests/                         # All test files
│   ├── __init__.py
│   ├── conftest.py                # Pytest fixtures
│   ├── unit/
│   │   ├── test_ptz_controller.py
│   │   ├── test_object_detector.py
│   │   └── test_motion_tracker.py
│   └── integration/
│       ├── test_tracking_engine.py
│       └── test_camera_integration.py
├── scripts/                       # Utility scripts
│   ├── discover_camera.py         # Find camera IP & capabilities
│   ├── test_ptz.py               # Test PTZ movements
│   ├── calibrate_presets.py      # Set up camera presets
│   └── setup_dev_env.py          # Development environment setup
├── docs/                          # Additional documentation
│   ├── API.md                     # API documentation
│   ├── CAMERA_SETUP.md            # Camera configuration guide
│   ├── TROUBLESHOOTING.md         # Common issues and solutions
│   └── screenshots/               # Images for documentation
│       ├── dashboard.png
│       ├── detection.png
│       └── tracking.gif
├── logs/                          # Application logs (gitignored)
│   └── .gitkeep
├── recordings/                    # Video recordings (gitignored)
│   └── .gitkeep
├── .github/                       # GitHub-specific files
│   ├── copilot-instructions.md
│   ├── WORKFLOW.md
│   └── workflows/                 # CI/CD (optional)
│       └── tests.yml
├── .env.example                   # Environment variables template
├── .gitignore                     # Git ignore rules
├── requirements.txt               # Python dependencies
├── requirements-dev.txt           # Development dependencies
├── pytest.ini                     # Pytest configuration
├── setup.py                       # Package setup (optional)
├── Dockerfile                     # Docker configuration
├── docker-compose.yml             # Docker Compose
├── render.yaml                    # Render.com deployment
├── vercel.json                    # Vercel deployment (optional)
├── README.md                      # Main documentation ← ONLY .md file in root!
└── LICENSE                        # License file
```

### Root Directory Rules

**✅ ONLY THESE IN ROOT:**
- **ONE main documentation file:** `README.md` ← The only .md file in root!
- **Configuration files:** `.env.example`, `pytest.ini`, `setup.py`
- **Dependency files:** `requirements.txt`, `requirements-dev.txt`, `package.json`
- **License:** `LICENSE` or `LICENSE.txt`
- **Build/deployment files:** `Dockerfile`, `docker-compose.yml`, `render.yaml`, `vercel.json`
- **Git files:** `.gitignore`, `.gitattributes`
- **CI/CD folders:** `.github/`, `.gitlab-ci.yml`

**📁 ALL OTHER DOCUMENTATION → `docs/` subfolder:**
- `docs/DEPLOYMENT.md` (not root)
- `docs/PROJECT_SUMMARY.md` (not root)
- `docs/CONTRIBUTING.md` (not root)
- `docs/CHANGELOG.md` (not root)
- `docs/API.md` (not root)
- `docs/TROUBLESHOOTING.md` (not root)

**❌ NEVER IN ROOT:**
- Source code files (`.py`, `.js` files) → Use `src/`
- Test files → Use `tests/`
- Configuration data (`.yaml`, `.json`) → Use `config/`
- Utility scripts → Use `scripts/`
- Temporary files → Use `logs/` or gitignore
- Video/image files → Use `recordings/` or `src/web/static/`
- Log files → Use `logs/`
- Cache files → Gitignore them

### Folder Organization Guidelines

1. **`src/`** - All application source code
   - Organized by feature/domain (video, ai, camera, automation)
   - Each subfolder has `__init__.py`
   - Entry point is `src/main.py`

2. **`config/`** - Configuration files only
   - YAML/JSON configuration files
   - No code, only data
   - Environment-specific configs

3. **`tests/`** - All test files
   - Mirror `src/` structure
   - Separate `unit/` and `integration/`
   - Fixtures in `conftest.py`

4. **`scripts/`** - Standalone utility scripts
   - Development/deployment helpers
   - One-off tasks
   - Not part of main application

5. **`docs/`** - Extended documentation
   - API documentation
   - Setup guides
   - Screenshots and diagrams
   - NOT for README (that stays in root)

6. **`logs/` and `recordings/`** - Runtime artifacts
   - Created by application
   - Gitignored (keep `.gitkeep` only)
   - Auto-created if missing

### File Naming Conventions

**Python Files:**
- Use `snake_case.py` for all Python files
- Module names: `ptz_controller.py`, `motion_tracker.py`
- Test files: `test_<module_name>.py`

**Configuration Files:**
- Use descriptive names: `camera_config.yaml`, `tracking_rules.yaml`
- Environment-specific: `config.dev.yaml`, `config.prod.yaml`

**Documentation:**
- Use UPPERCASE for important docs: `README.md`, `LICENSE`, `CHANGELOG.md`
- Use descriptive names: `DEPLOYMENT.md`, `TROUBLESHOOTING.md`

### When Creating New Files

**Always ask yourself:**
1. **Where does this belong?** (src, tests, scripts, docs, config?)
2. **Is the subfolder structure clear?** (create subfolders if needed)
3. **Does it keep the root clean?** (move to appropriate subfolder)

**Examples:**

✅ **Good - Organized:**
```
src/camera/ptz_controller.py          # Application code
tests/unit/test_ptz_controller.py     # Tests
config/camera_config.yaml             # Configuration
scripts/discover_camera.py            # Utility script
docs/CAMERA_SETUP.md                  # Documentation
```

❌ **Bad - Cluttered root:**
```
ptz_controller.py                      # Should be in src/camera/
test_ptz.py                            # Should be in tests/
camera_config.yaml                     # Should be in config/
setup_camera.py                        # Should be in scripts/
camera_guide.md                        # Should be in docs/
```

### Import Path Best Practices

Since code is in `src/`, use absolute imports from project root:

```python
# Good - Absolute imports from src/
from src.camera.ptz_controller import PTZController
from src.ai.object_detector import ObjectDetector
from src.automation.tracking_engine import TrackingEngine

# Avoid - Relative imports across modules
from ..camera.ptz_controller import PTZController  # Fragile
```

**Setup for absolute imports:**

```python
# src/__init__.py (empty file)

# setup.py (optional, for package installation)
from setuptools import setup, find_packages

setup(
    name="security-video-automation",
    packages=find_packages(),
    python_requires=">=3.10",
)
```

### Module Organization Example

**Good module structure:**

```python
# src/camera/ptz_controller.py
"""PTZ camera control module."""

from typing import Optional
from onvif import ONVIFCamera

class PTZController:
    """Control PTZ camera using ONVIF protocol."""
    
    def __init__(self, camera_ip: str, username: str, password: str):
        """Initialize PTZ controller."""
        pass

# src/camera/__init__.py
"""Camera control package."""

from .ptz_controller import PTZController
from .preset_manager import PresetManager

__all__ = ['PTZController', 'PresetManager']
```

**Usage:**

```python
# src/main.py
from src.camera import PTZController  # Clean import
from src.ai import ObjectDetector

# Not: from src.camera.ptz_controller import PTZController (too verbose)
```

## Code Style & Conventions

### General Guidelines
- Follow PEP 8 style guide
- Use type hints for all functions
- Use descriptive variable names (`subject_velocity` not `sv`)
- Keep functions focused (single responsibility)
- Use dataclasses for structured data (detection results, camera position)

### Example:
```python
from dataclasses import dataclass
from typing import Tuple

@dataclass
class DetectionResult:
    """Represents a detected object in video frame"""
    class_name: str          # 'person', 'vehicle', etc.
    confidence: float        # 0.0 to 1.0
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    center: Tuple[int, int]  # (x, y) center point
    frame_number: int
    timestamp: float
```

## PTZ Camera Integration

### Camera Discovery & Capabilities

**Priority 1: Determine Camera Model & API**
1. Check camera documentation for API specifications
2. Common protocols:
   - **ONVIF** (most IP cameras support this)
   - **HTTP CGI API** (manufacturer-specific)
   - **SDK** (manufacturer provides Python/C++ library)

**Discovery Script Pattern:**
```python
from onvif import ONVIFCamera

def discover_camera_capabilities(ip: str, port: int, user: str, password: str) -> dict:
    """
    Discover what the camera supports (PTZ, presets, etc.)
    
    Args:
        ip: Camera IP address
        port: ONVIF port (usually 80, 8080, or 8000)
        user: Camera username
        password: Camera password
        
    Returns:
        Dict with camera capabilities and supported operations
    """
    try:
        camera = ONVIFCamera(ip, port, user, password)
        
        # Get device information
        device_info = camera.devicemgmt.GetDeviceInformation()
        
        # Check PTZ support
        ptz_service = camera.create_ptz_service()
        
        # Get available presets
        presets = ptz_service.GetPresets({'ProfileToken': profile_token})
        
        return {
            'manufacturer': device_info.Manufacturer,
            'model': device_info.Model,
            'has_ptz': True,
            'presets': [{'token': p.token, 'name': p.Name} for p in presets],
            'supports_continuous_move': True,
            'supports_absolute_move': True
        }
    except Exception as e:
        print(f"Camera discovery failed: {e}")
        return {'has_ptz': False, 'error': str(e)}
```

### PTZ Control Patterns

**1. Preset-Based Tracking (Recommended for your use case)**
```python
class PTZController:
    """Control PTZ camera using presets"""
    
    def __init__(self, camera_ip: str, username: str, password: str):
        self.camera = ONVIFCamera(camera_ip, 80, username, password)
        self.ptz = self.camera.create_ptz_service()
        self.media = self.camera.create_media_service()
        self.profile = self.media.GetProfiles()[0]
        
    def goto_preset(self, preset_token: str, speed: float = 1.0):
        """
        Move camera to a preset position
        
        Args:
            preset_token: Preset identifier (e.g., '1', '2', 'entrance')
            speed: Movement speed 0.0 to 1.0
        """
        request = self.ptz.create_type('GotoPreset')
        request.ProfileToken = self.profile.token
        request.PresetToken = preset_token
        request.Speed = {'PanTilt': {'x': speed, 'y': speed}}
        
        self.ptz.GotoPreset(request)
        
    def set_preset(self, name: str) -> str:
        """Save current position as preset"""
        request = self.ptz.create_type('SetPreset')
        request.ProfileToken = self.profile.token
        request.PresetName = name
        
        response = self.ptz.SetPreset(request)
        return response.PresetToken
```

**2. Continuous Movement (for smooth tracking)**
```python
    def continuous_move(self, pan_velocity: float, tilt_velocity: float, duration: float = 1.0):
        """
        Continuous pan/tilt movement
        
        Args:
            pan_velocity: -1.0 (left) to 1.0 (right)
            tilt_velocity: -1.0 (down) to 1.0 (up)
            duration: Movement duration in seconds
        """
        request = self.ptz.create_type('ContinuousMove')
        request.ProfileToken = self.profile.token
        request.Velocity = {
            'PanTilt': {'x': pan_velocity, 'y': tilt_velocity},
            'Zoom': {'x': 0}
        }
        
        self.ptz.ContinuousMove(request)
        time.sleep(duration)
        self.ptz.Stop({'ProfileToken': self.profile.token})
```

## AI Object Detection & Tracking

### Object Detection Setup

**Recommended Models:**
1. **YOLOv8** - Fast, accurate, easy to use (Ultralytics)
2. **YOLOv5** - Lightweight, good for edge devices
3. **TensorFlow Object Detection API** - More customizable
4. **MediaPipe** - Google's solution, good for person tracking

**YOLOv8 Implementation:**
```python
from ultralytics import YOLO
import cv2
from typing import List

class ObjectDetector:
    """Detect objects in video frames using YOLO"""
    
    def __init__(self, model_path: str = 'yolov8n.pt', confidence_threshold: float = 0.5):
        """
        Initialize detector
        
        Args:
            model_path: Path to YOLO model (yolov8n.pt, yolov8s.pt, etc.)
            confidence_threshold: Minimum confidence for detections
        """
        self.model = YOLO(model_path)
        self.confidence_threshold = confidence_threshold
        self.target_classes = ['person', 'car', 'truck', 'bicycle']
        
    def detect(self, frame: np.ndarray) -> List[DetectionResult]:
        """
        Detect objects in frame
        
        Args:
            frame: OpenCV image (BGR format)
            
        Returns:
            List of DetectionResult objects
        """
        results = self.model(frame, verbose=False)[0]
        
        detections = []
        for box in results.boxes:
            class_id = int(box.cls[0])
            class_name = results.names[class_id]
            confidence = float(box.conf[0])
            
            if class_name in self.target_classes and confidence >= self.confidence_threshold:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                
                detections.append(DetectionResult(
                    class_name=class_name,
                    confidence=confidence,
                    bbox=(x1, y1, x2, y2),
                    center=(center_x, center_y),
                    frame_number=0,  # Set by caller
                    timestamp=time.time()
                ))
                
        return detections
```

### Motion Direction Tracking

**Track subject movement and determine direction:**
```python
from collections import deque
from enum import Enum

class Direction(Enum):
    """Movement directions"""
    LEFT_TO_RIGHT = "left_to_right"
    RIGHT_TO_LEFT = "right_to_left"
    TOP_TO_BOTTOM = "top_to_bottom"
    BOTTOM_TO_TOP = "bottom_to_top"
    STATIONARY = "stationary"

class MotionTracker:
    """Track object motion and determine direction"""
    
    def __init__(self, history_length: int = 30, movement_threshold: int = 50):
        """
        Args:
            history_length: Number of frames to track
            movement_threshold: Minimum pixel movement to detect direction
        """
        self.tracked_objects = {}  # object_id -> deque of positions
        self.history_length = history_length
        self.movement_threshold = movement_threshold
        
    def update(self, object_id: str, center: Tuple[int, int]) -> Direction:
        """
        Update object position and calculate direction
        
        Args:
            object_id: Unique identifier for tracked object
            center: (x, y) center position
            
        Returns:
            Direction enum indicating movement direction
        """
        if object_id not in self.tracked_objects:
            self.tracked_objects[object_id] = deque(maxlen=self.history_length)
            
        self.tracked_objects[object_id].append(center)
        
        return self._calculate_direction(object_id)
        
    def _calculate_direction(self, object_id: str) -> Direction:
        """Calculate movement direction from position history"""
        positions = self.tracked_objects[object_id]
        
        if len(positions) < 5:  # Need minimum history
            return Direction.STATIONARY
            
        # Calculate displacement
        start_x, start_y = positions[0]
        end_x, end_y = positions[-1]
        
        dx = end_x - start_x
        dy = end_y - start_y
        
        # Determine dominant direction
        if abs(dx) < self.movement_threshold and abs(dy) < self.movement_threshold:
            return Direction.STATIONARY
            
        if abs(dx) > abs(dy):  # Horizontal movement dominant
            return Direction.RIGHT_TO_LEFT if dx < 0 else Direction.LEFT_TO_RIGHT
        else:  # Vertical movement dominant
            return Direction.BOTTOM_TO_TOP if dy < 0 else Direction.TOP_TO_BOTTOM
```

## Automated Tracking Logic

### Main Tracking Engine

**Combine detection, tracking, and PTZ control:**
```python
class TrackingEngine:
    """Main engine coordinating detection, tracking, and camera control"""
    
    def __init__(
        self,
        detector: ObjectDetector,
        ptz_controller: PTZController,
        motion_tracker: MotionTracker,
        config: dict
    ):
        self.detector = detector
        self.ptz = ptz_controller
        self.tracker = motion_tracker
        self.config = config
        
        # Define zones and their corresponding presets
        self.zone_presets = {
            'zone_left': 'preset_1',
            'zone_center': 'preset_2',
            'zone_right': 'preset_3'
        }
        
        self.current_tracking_id = None
        self.last_preset = None
        
    def process_frame(self, frame: np.ndarray) -> None:
        """
        Process single video frame
        
        Args:
            frame: OpenCV BGR image
        """
        # Detect objects
        detections = self.detector.detect(frame)
        
        if not detections:
            return
            
        # Track primary subject (closest/largest)
        primary = self._select_primary_subject(detections)
        
        # Update motion tracking
        direction = self.tracker.update(
            object_id=f"obj_{primary.frame_number}",
            center=primary.center
        )
        
        # Determine required camera action
        self._handle_tracking(primary, direction, frame.shape)
        
    def _select_primary_subject(self, detections: List[DetectionResult]) -> DetectionResult:
        """Select the most important subject to track"""
        # Prioritize: 1) persons, 2) closest to center, 3) highest confidence
        persons = [d for d in detections if d.class_name == 'person']
        
        if persons:
            return max(persons, key=lambda d: d.confidence)
        return max(detections, key=lambda d: d.confidence)
        
    def _handle_tracking(
        self,
        subject: DetectionResult,
        direction: Direction,
        frame_shape: Tuple[int, int, int]
    ) -> None:
        """
        Decide and execute camera movement
        
        Args:
            subject: Detected subject to track
            direction: Movement direction
            frame_shape: (height, width, channels)
        """
        height, width = frame_shape[:2]
        x, y = subject.center
        
        # Determine which zone the subject is in
        zone = self._get_zone(x, width)
        
        # For RIGHT_TO_LEFT movement, anticipate and move camera
        if direction == Direction.RIGHT_TO_LEFT:
            # Subject moving from right to left
            if zone == 'zone_center' or zone == 'zone_left':
                # Move camera to left preset to track
                target_preset = self.zone_presets['zone_left']
                
                if target_preset != self.last_preset:
                    print(f"Subject moving {direction.value}, moving to {target_preset}")
                    self.ptz.goto_preset(target_preset, speed=0.8)
                    self.last_preset = target_preset
                    
        elif direction == Direction.LEFT_TO_RIGHT:
            # Subject moving from left to right
            if zone == 'zone_center' or zone == 'zone_right':
                target_preset = self.zone_presets['zone_right']
                
                if target_preset != self.last_preset:
                    print(f"Subject moving {direction.value}, moving to {target_preset}")
                    self.ptz.goto_preset(target_preset, speed=0.8)
                    self.last_preset = target_preset
                    
    def _get_zone(self, x: int, frame_width: int) -> str:
        """Determine which zone of frame the x-coordinate is in"""
        if x < frame_width * 0.33:
            return 'zone_left'
        elif x < frame_width * 0.66:
            return 'zone_center'
        else:
            return 'zone_right'
```

## Video Stream Handling

### RTSP Stream Capture
```python
import cv2
from threading import Thread
from queue import Queue

class VideoStreamHandler:
    """Handle video stream from IP camera"""
    
    def __init__(self, stream_url: str, buffer_size: int = 30):
        """
        Args:
            stream_url: RTSP or HTTP stream URL
                       Example: rtsp://username:password@192.168.1.100:554/stream1
            buffer_size: Frame buffer size
        """
        self.stream_url = stream_url
        self.capture = None
        self.frame_queue = Queue(maxsize=buffer_size)
        self.stopped = False
        
    def start(self) -> 'VideoStreamHandler':
        """Start video capture in separate thread"""
        self.capture = cv2.VideoCapture(self.stream_url)
        
        if not self.capture.isOpened():
            raise ValueError(f"Failed to open stream: {self.stream_url}")
            
        Thread(target=self._update, daemon=True).start()
        return self
        
    def _update(self) -> None:
        """Continuously read frames from stream"""
        while not self.stopped:
            if not self.frame_queue.full():
                ret, frame = self.capture.read()
                if not ret:
                    print("Stream ended or error occurred")
                    self.stopped = True
                    break
                    
                if not self.frame_queue.empty():
                    try:
                        self.frame_queue.get_nowait()  # Discard old frame
                    except:
                        pass
                        
                self.frame_queue.put(frame)
                
    def read(self) -> np.ndarray:
        """Get latest frame from stream"""
        return self.frame_queue.get()
        
    def stop(self) -> None:
        """Stop stream capture"""
        self.stopped = True
        if self.capture:
            self.capture.release()
```

## Configuration Files

### Camera Configuration (`config/camera_config.yaml`)
```yaml
camera:
  ip: "192.168.1.100"
  port: 80
  username: "admin"
  password: "${CAMERA_PASSWORD}"  # From environment variable
  
  stream:
    rtsp_url: "rtsp://${CAMERA_USERNAME}:${CAMERA_PASSWORD}@${CAMERA_IP}:554/stream1"
    resolution: [1920, 1080]
    fps: 30
    
  ptz:
    protocol: "onvif"  # or "http_cgi", "sdk"
    
    presets:
      - name: "zone_left"
        token: "1"
        description: "Left side coverage"
        
      - name: "zone_center"
        token: "2"
        description: "Center/entrance"
        
      - name: "zone_right"
        token: "3"
        description: "Right side coverage"
        
    movement:
      default_speed: 0.7
      smooth_tracking: true
```

### Tracking Rules (`config/tracking_rules.yaml`)
```yaml
tracking:
  enabled: true
  
  targets:
    - person
    - vehicle
    
  direction_triggers:
    right_to_left:
      enabled: true
      presets: ["zone_center", "zone_left"]
      min_displacement: 100  # pixels
      
    left_to_right:
      enabled: true
      presets: ["zone_center", "zone_right"]
      min_displacement: 100
      
  zones:
    zone_left:
      x_range: [0, 0.33]  # As fraction of frame width
      preset: "zone_left"
      
    zone_center:
      x_range: [0.33, 0.66]
      preset: "zone_center"
      
    zone_right:
      x_range: [0.66, 1.0]
      preset: "zone_right"
      
  filters:
    min_confidence: 0.6
    min_object_size: 50  # pixels
    ignore_stationary: false
```

## Main Application

### Entry Point (`src/main.py`)
```python
import cv2
import yaml
from src.video.stream_handler import VideoStreamHandler
from src.ai.object_detector import ObjectDetector
from src.ai.motion_tracker import MotionTracker
from src.camera.ptz_controller import PTZController
from src.automation.tracking_engine import TrackingEngine

def load_config(config_path: str) -> dict:
    """Load YAML configuration file"""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def main():
    """Main application entry point"""
    # Load configuration
    camera_config = load_config('config/camera_config.yaml')
    tracking_config = load_config('config/tracking_rules.yaml')
    
    # Initialize components
    print("Initializing video stream...")
    stream = VideoStreamHandler(camera_config['camera']['stream']['rtsp_url']).start()
    
    print("Loading AI model...")
    detector = ObjectDetector(model_path='yolov8n.pt', confidence_threshold=0.6)
    
    print("Connecting to PTZ camera...")
    ptz = PTZController(
        camera_ip=camera_config['camera']['ip'],
        username=camera_config['camera']['username'],
        password=camera_config['camera']['password']
    )
    
    # Create tracking engine
    tracker = MotionTracker(history_length=30, movement_threshold=100)
    engine = TrackingEngine(detector, ptz, tracker, tracking_config)
    
    print("Starting automated tracking...")
    frame_count = 0
    
    try:
        while True:
            frame = stream.read()
            frame_count += 1
            
            # Process every Nth frame to reduce CPU load
            if frame_count % 2 == 0:
                engine.process_frame(frame)
                
            # Display video (optional, remove for headless operation)
            cv2.imshow('Security Camera Tracking', frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    except KeyboardInterrupt:
        print("\nStopping tracking system...")
    finally:
        stream.stop()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
```

## Testing & Debugging

### Camera Discovery Script (`scripts/discover_camera.py`)
```python
"""Discover camera on network and check PTZ capabilities"""
import sys
from onvif import ONVIFCamera

def discover_camera(ip: str, port: int = 80, username: str = 'admin', password: str = 'admin'):
    """Test connection and discover camera capabilities"""
    try:
        print(f"Connecting to camera at {ip}:{port}...")
        camera = ONVIFCamera(ip, port, username, password)
        
        # Device info
        device_info = camera.devicemgmt.GetDeviceInformation()
        print(f"\n✓ Camera found!")
        print(f"  Manufacturer: {device_info.Manufacturer}")
        print(f"  Model: {device_info.Model}")
        print(f"  Firmware: {device_info.FirmwareVersion}")
        
        # Media profiles
        media_service = camera.create_media_service()
        profiles = media_service.GetProfiles()
        print(f"\n✓ Media Profiles: {len(profiles)}")
        
        # PTZ capabilities
        try:
            ptz_service = camera.create_ptz_service()
            print(f"✓ PTZ Service Available: Yes")
            
            # Get presets
            profile_token = profiles[0].token
            presets = ptz_service.GetPresets({'ProfileToken': profile_token})
            print(f"✓ Configured Presets: {len(presets)}")
            
            for preset in presets:
                print(f"    - {preset.Name} (Token: {preset.token})")
                
        except Exception as e:
            print(f"✗ PTZ Service: Not available ({e})")
            
        return True
        
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python discover_camera.py <camera_ip> [port] [username] [password]")
        sys.exit(1)
        
    ip = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 80
    username = sys.argv[3] if len(sys.argv) > 3 else 'admin'
    password = sys.argv[4] if len(sys.argv) > 4 else 'admin'
    
    discover_camera(ip, port, username, password)
```

### PTZ Test Script (`scripts/test_ptz.py`)
```python
"""Test PTZ movements and presets"""
from src.camera.ptz_controller import PTZController
import time

def test_presets(controller: PTZController, preset_tokens: list):
    """Test moving between presets"""
    print("Testing preset movements...")
    
    for token in preset_tokens:
        print(f"Moving to preset {token}...")
        controller.goto_preset(token, speed=0.5)
        time.sleep(3)  # Wait for movement to complete
        
    print("Preset test complete")

def test_continuous_move(controller: PTZController):
    """Test continuous pan/tilt"""
    print("\nTesting continuous movement...")
    
    # Pan right
    print("Panning right...")
    controller.continuous_move(pan_velocity=0.5, tilt_velocity=0, duration=2)
    time.sleep(1)
    
    # Pan left
    print("Panning left...")
    controller.continuous_move(pan_velocity=-0.5, tilt_velocity=0, duration=2)
    time.sleep(1)
    
    print("Continuous movement test complete")

if __name__ == "__main__":
    # Update with your camera details
    ptz = PTZController(
        camera_ip="192.168.1.100",
        username="admin",
        password="your_password"
    )
    
    test_presets(ptz, ['1', '2', '3'])
    test_continuous_move(ptz)
```

## Security & Best Practices

### Credentials Management
- NEVER hardcode camera passwords
- Use environment variables or secure vault
- Restrict camera API access to local network only
- Use HTTPS for web interface if exposed

### Example `.env` file:
```env
CAMERA_IP=192.168.1.100
CAMERA_USERNAME=admin
CAMERA_PASSWORD=your_secure_password
CAMERA_RTSP_PORT=554
CAMERA_ONVIF_PORT=80
```

### Performance Optimization
- Process every 2nd or 3rd frame to reduce CPU load
- Use smaller YOLO models (yolov8n.pt) for real-time performance
- Run on GPU if available (CUDA)
- Consider edge devices (Jetson Nano, Coral TPU)

### Privacy & Compliance
- Post signage about video surveillance
- Store footage securely
- Implement retention policies
- Blur faces if required by local laws
- Limit tracking to public areas

## Common Camera API Types

### 1. ONVIF (Recommended - Universal Standard)
- Supported by most IP cameras
- Standardized PTZ control
- Python library: `python-onvif-zeep`
- Requires: Camera IP, port (80/8080), username, password

### 2. HTTP CGI API (Manufacturer-Specific)
**Hikvision Example:**
```python
import requests

def hikvision_goto_preset(ip: str, username: str, password: str, preset_id: int):
    """Move Hikvision camera to preset"""
    url = f"http://{ip}/ISAPI/PTZCtrl/channels/1/presets/{preset_id}/goto"
    response = requests.put(url, auth=(username, password))
    return response.status_code == 200
```

**Dahua Example:**
```python
def dahua_goto_preset(ip: str, username: str, password: str, preset_id: int):
    """Move Dahua camera to preset"""
    url = f"http://{ip}/cgi-bin/ptz.cgi?action=start&channel=0&code=GotoPreset&arg1=0&arg2={preset_id}&arg3=0"
    response = requests.get(url, auth=(username, password))
    return response.status_code == 200
```

### 3. SDK (Manufacturer Library)
- Hikvision: HCNetSDK
- Dahua: Dahua SDK
- Axis: VAPIX
- Usually requires manufacturer-specific installation

## Troubleshooting

### Camera Connection Issues
1. **Ping camera IP** - Verify network connectivity
2. **Check ONVIF port** - Try 80, 8080, 8000, 8899
3. **Verify credentials** - Test with camera web interface
4. **Enable ONVIF** - May be disabled in camera settings
5. **Firewall** - Ensure ports are open

### Stream Issues
1. **RTSP URL format** - Check camera documentation
2. **Codec support** - Use H.264 (most compatible)
3. **Network bandwidth** - Lower resolution if needed
4. **Buffer size** - Increase if frames dropping

### AI Detection Issues
1. **Model accuracy** - Use larger model (yolov8m.pt or yolov8l.pt)
2. **Lighting conditions** - Ensure adequate lighting
3. **Camera angle** - Position for clear subject view
4. **Confidence threshold** - Lower if missing detections

## Next Steps & Feature Ideas

### Phase 1: Basic Setup
- [ ] Discover camera and verify PTZ API works
- [ ] Set up 3-5 camera presets covering your area
- [ ] Test moving between presets manually
- [ ] Capture test video footage

### Phase 2: AI Integration
- [ ] Install YOLOv8 and test object detection
- [ ] Implement basic motion tracking
- [ ] Test direction detection (right-to-left)
- [ ] Log detected movements

### Phase 3: Automation
- [ ] Integrate PTZ control with AI detections
- [ ] Implement zone-based preset triggering
- [ ] Test automated tracking with live subjects
- [ ] Fine-tune movement thresholds

### Phase 4: Advanced Features
- [ ] Multi-camera support
- [ ] Smart tracking (predict movement path)
- [ ] Event recording (save clips when tracking)
- [ ] Web dashboard for monitoring
- [ ] Alert notifications (email/SMS)
- [ ] Time-based rules (different behavior day/night)
- [ ] Privacy zones (areas to ignore)

## Resources & Documentation

- [ONVIF Python Library](https://github.com/quatanium/python-onvif)
- [Ultralytics YOLOv8](https://docs.ultralytics.com/)
- [OpenCV Documentation](https://docs.opencv.org/)
- [ONVIF Specification](https://www.onvif.org/profiles/)
- [IP Camera Finder Tools](https://www.advanced-ip-scanner.com/)

## Performance Targets

- **Detection latency**: < 100ms per frame
- **PTZ response time**: < 2 seconds to preset
- **Frame processing**: 15-30 FPS
- **CPU usage**: < 50% on modern hardware
- **Memory usage**: < 2GB

## Git Workflow & Commits

### Branch Strategy
**NEVER commit directly to `main`**. Always use feature branches and Pull Requests.

```bash
# Create feature branch
git checkout -b feature/camera-discovery
git checkout -b feature/ai-detection
git checkout -b fix/stream-timeout
```

### Conventional Commits (REQUIRED)
Follow [Conventional Commits](https://www.conventionalcommits.org/) specification:

**Format:** `<type>(<scope>): <subject>`

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance

**Scopes:**
- `camera`: PTZ control, ONVIF
- `ai`: Object detection, motion tracking
- `video`: Stream handling
- `automation`: Tracking engine
- `web`: Dashboard (if implemented)

**Examples:**
```bash
git commit -m "feat(camera): add ONVIF camera discovery script"
git commit -m "feat(ai): implement YOLOv8 object detection"
git commit -m "fix(camera): handle PTZ timeout errors"
git commit -m "feat(automation): add right-to-left tracking"
git commit -m "docs(readme): add setup instructions"
git commit -m "test(camera): add PTZ controller tests"
```

### Pull Request Workflow
1. Create feature branch from `main`
2. Make changes with conventional commits
3. Push branch to remote
4. Create PR to `main` with description
5. Wait for review/approval
6. Merge via GitHub (squash or rebase)
7. Delete feature branch

**See [WORKFLOW.md](.github/WORKFLOW.md) for detailed workflow instructions.**

## Web Dashboard & Portfolio Deployment

### Should You Add a Web Interface?

**YES - Highly Recommended for Portfolio** ✅

A web dashboard transforms this into a showcase-worthy portfolio project:

### Portfolio Benefits
1. **Visual Impact** - Live video feed, detection overlays, tracking stats
2. **Demonstrable** - Employers can see it working without running code
3. **Full-Stack Skills** - Shows Python backend + frontend + deployment
4. **Shareable** - Direct link for resume/LinkedIn

### Recommended Tech Stack

**Backend: FastAPI**
```python
# src/web/app.py
from fastapi import FastAPI, WebSocket
from fastapi.responses import StreamingResponse

app = FastAPI(title="Security Camera AI Tracker")

@app.get("/api/camera/status")
async def camera_status():
    return {
        "connected": True,
        "current_preset": "zone_center",
        "tracking_active": True,
        "detections": 3
    }

@app.websocket("/ws/video")
async def video_feed(websocket: WebSocket):
    """Stream video with detection overlays"""
    await websocket.accept()
    while True:
        frame = get_latest_frame_with_detections()
        await websocket.send_bytes(frame)

@app.post("/api/camera/preset/{preset_id}")
async def move_camera(preset_id: int):
    """Manual camera control"""
    ptz_controller.goto_preset(str(preset_id))
    return {"status": "moving"}
```

**Frontend: HTML/JS + Canvas**
- Display live video stream
- Show detection bounding boxes
- Manual camera controls
- Real-time statistics charts
- Event log

### Deployment Options

#### 1. Render.com (Recommended for Backend) ✅
- **Best for:** Python backend with always-on service
- **Pros:** Free tier, Python support, auto-deploy, WebSocket support
- **Cons:** Spins down after inactivity (free tier)
- **Setup:** Add `render.yaml` with web service config

```yaml
# render.yaml
services:
  - type: web
    name: security-camera-ai
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn src.web.app:app --host 0.0.0.0 --port $PORT
```

#### 2. Vercel (For Static Demo) ✅
- **Best for:** Portfolio demo with pre-recorded footage
- **Pros:** Instant deploy, fast CDN, custom domain
- **Cons:** Can't run long-lived processes, no real camera control
- **Use Case:** Demo mode showing pre-recorded tracking

#### 3. Hybrid Approach (Best for Portfolio) ✅

```
┌─────────────────────────────────────────┐
│  Vercel (Public Portfolio Demo)         │
│  - Pre-recorded video demonstration     │
│  - Static tracking results & charts     │
│  - GitHub link to source code           │
└─────────────────────────────────────────┘
                 +
┌─────────────────────────────────────────┐
│  Local Setup (Real Implementation)      │
│  - Live camera feed                      │
│  - Real PTZ control & AI tracking       │
│  - Local dashboard access                │
└─────────────────────────────────────────┘
```

### Portfolio Enhancement Checklist

- [ ] Add FastAPI web dashboard
- [ ] Create demo mode with pre-recorded video
- [ ] Deploy static demo to Vercel
- [ ] Record video demonstration for YouTube
- [ ] Add live demo link to README
- [ ] Include screenshots in documentation
- [ ] Create project showcase section for portfolio website

### Dashboard Features to Implement

**Essential:**
- Live video display with detection overlays
- Current camera position indicator
- Manual preset control buttons
- Auto-tracking on/off toggle

**Advanced:**
- Detection count statistics
- Direction movement chart (left/right ratios)
- Event timeline (detections, movements)
- Heatmap of most active zones
- Historical tracking data

## When Suggesting Code

### DO:
- Include error handling for network failures
- Test PTZ commands before automating
- Log all camera movements for debugging
- Use threading for video capture
- Implement graceful degradation (continue if AI fails)
- Follow conventional commit format
- Create feature branches for new work
- Add web endpoints for portfolio showcase
- **Keep root directory clean** - Place files in appropriate subfolders
- **Use absolute imports** from `src/` package
- **Create `__init__.py`** in every Python package folder

### DON'T:
- Hardcode camera credentials
- Block main thread with long operations
- Ignore camera command failures
- Process every frame (wasteful)
- Move camera too frequently (mechanical wear)
- Commit directly to main branch
- Skip Pull Request process
- Use vague commit messages
- **Put source code in root directory** - Use `src/`, `scripts/`, `tests/`
- **Create files without considering folder structure**
- **Mix concerns** - Keep config separate from code

### File Creation Checklist

Before creating any new file, ask:

1. **Is this application code?** → `src/<module>/filename.py`
2. **Is this a test?** → `tests/unit/` or `tests/integration/`
3. **Is this a utility script?** → `scripts/filename.py`
4. **Is this configuration?** → `config/filename.yaml`
5. **Is this documentation?** → `docs/filename.md` or root (README, LICENSE only)
6. **Is this a web asset?** → `src/web/static/` or `src/web/templates/`

**Example decisions:**

- Camera discovery script? → `scripts/discover_camera.py` ✅
- PTZ controller class? → `src/camera/ptz_controller.py` ✅
- Camera settings? → `config/camera_config.yaml` ✅
- Setup guide? → `docs/CAMERA_SETUP.md` ✅
- Main application? → `src/main.py` ✅
- PTZ tests? → `tests/unit/test_ptz_controller.py` ✅

---

**Remember:** Start simple, test thoroughly, and iterate. First verify PTZ API works, then add AI, then combine them for automation. Add web dashboard for portfolio impact!
