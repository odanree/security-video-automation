# 🎥 Security Camera AI Automation

> AI-powered video analysis with automated PTZ camera tracking. Detects subjects, analyzes motion direction, and automatically controls camera presets to maintain visual tracking.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## 🌟 Features

- **🤖 AI Object Detection** - Real-time person/vehicle detection using YOLOv8
- **📍 Motion Direction Tracking** - Analyzes subject trajectories (left-to-right, right-to-left)
- **🎮 Automated PTZ Control** - Triggers camera preset positions via ONVIF protocol
- **📊 Web Dashboard** - Live monitoring, statistics, and manual controls
- **⚙️ Configurable Rules** - YAML-based tracking configuration
- **🔌 ONVIF Compatible** - Works with most IP PTZ cameras
- **🛡️ Production Resilience** - Circuit breakers, retry policies, health monitoring, and metrics

## 🎬 Demo

**[🔴 View Live Demo →](https://your-demo-url.vercel.app)** *(Coming Soon)*

### How It Works

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Camera    │ ───> │  AI Detector │ ───> │   Motion    │
│  RTSP Feed  │      │  (YOLOv8)    │      │   Tracker   │
└─────────────┘      └──────────────┘      └─────────────┘
                                                    │
                                                    ▼
                                            ┌─────────────┐
                                            │   Tracking  │
                                            │   Engine    │
                                            └─────────────┘
                                                    │
                                                    ▼
                                            ┌─────────────┐
                                            │ PTZ Control │
                                            │  (ONVIF)    │
                                            └─────────────┘
                                                    │
                                                    ▼
                                            ┌─────────────┐
                                            │   Camera    │
                                            │   Moves to  │
                                            │   Preset    │
                                            └─────────────┘
```

**Example:** Person walks right-to-left → AI detects → Motion tracker analyzes direction → Camera automatically moves to left preset to maintain tracking

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- IP camera with PTZ and ONVIF support
- Camera accessible on local network

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/security-video-automation.git
   cd security-video-automation
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure camera settings**
   ```bash
   cp .env.example .env
   # Edit .env with your camera details
   ```

5. **Discover your camera**
   ```bash
   python scripts/discover_camera.py 192.168.1.100
   ```

### Running the System

**Option 1: Interactive Runner (Easiest)**
```bash
python run.py
```
Select from menu options (display mode, headless, debug, etc.)

**Option 2: Direct Execution**
```bash
# Basic usage (headless)
python src/main.py

# With video display
python src/main.py --display

# Debug mode
python src/main.py --log-level DEBUG --display

# Run for 60 seconds
python src/main.py --display --duration 60

# Detection only (no PTZ control)
python src/main.py --display --no-ptz
```

**Keyboard Controls** (when `--display` is enabled):
- `q` - Quit
- `p` - Pause/resume tracking
- `s` - Show statistics

**Option 3: Web Dashboard** 🌐 (Recommended for Monitoring)
```bash
# Start web dashboard server
cd src/web
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Then open your browser to `http://localhost:8000`

**Dashboard Features:**
- 📹 **Live Video Stream** - Real-time MJPEG stream with AI detection overlays
- 📊 **Statistics Dashboard** - Total detections, active tracks, events, FPS
- 🎮 **Manual PTZ Control** - Directional pad and preset selection
- ⚡ **Real-Time Updates** - WebSocket connection for live statistics
- 📝 **Event Log** - Track all detections with timestamps and confidence scores
- 🎯 **Tracking Toggle** - Start/stop automated tracking with one click

**See [RUNNING.md](docs/RUNNING.md) for detailed usage instructions.**

## 📋 Project Structure

**IMPORTANT: We keep the root directory clean!** All source code goes in `src/`, tests in `tests/`, configs in `config/`, etc.

```
security-video-automation/
├── src/                           # All application code
│   ├── video/
│   │   ├── stream_handler.py      # RTSP stream capture
│   │   └── frame_processor.py     # Video frame processing
│   ├── ai/
│   │   ├── object_detector.py     # YOLOv8 detection
│   │   └── motion_tracker.py      # Direction analysis
│   ├── camera/
│   │   ├── ptz_controller.py      # PTZ API integration
│   │   └── onvif_client.py        # ONVIF protocol
│   ├── automation/
│   │   ├── tracking_engine.py     # Main tracking logic
│   │   └── rules_engine.py        # Configurable rules
│   └── web/
│       ├── app.py                 # FastAPI backend
│       └── static/                # Frontend assets
├── config/                        # Configuration files only
│   ├── camera_config.yaml         # Camera settings
│   └── tracking_rules.yaml        # Movement rules
├── scripts/                       # Utility scripts
│   ├── discover_camera.py         # Camera discovery
│   └── test_ptz.py               # PTZ testing
├── tests/                         # All test files
│   ├── unit/
│   └── integration/
├── docs/                          # Extended documentation
│   └── screenshots/
├── .github/
│   ├── copilot-instructions.md    # AI coding guidelines
│   ├── WORKFLOW.md                # Development workflow
│   └── FOLDER_STRUCTURE.md        # Project organization guide
├── README.md                      # This file
├── requirements.txt               # Dependencies
└── render.yaml                    # Deployment config
```

**See [FOLDER_STRUCTURE.md](.github/FOLDER_STRUCTURE.md) for detailed organization guidelines.**

## ⚙️ Configuration

### Camera Setup (`config/camera_config.yaml`)

```yaml
camera:
  ip: "192.168.1.100"
  port: 80
  username: "admin"
  password: "${CAMERA_PASSWORD}"
  
  stream:
    rtsp_url: "rtsp://admin:password@192.168.1.100:554/stream1"
    
  ptz:
    presets:
      - name: "zone_left"
        token: "1"
      - name: "zone_center"
        token: "2"
      - name: "zone_right"
        token: "3"
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
      min_displacement: 100
      
  filters:
    min_confidence: 0.6
    min_object_size: 50
```

## 🛠️ Development

### Project Architecture

The system is built with production-grade resilience:

```
src/
├── ai/              # Object detection and tracking models
├── camera/          # ONVIF PTZ camera control
├── automation/      # Main tracking engine
├── video/           # Stream handling and processing
├── web/             # FastAPI dashboard and REST API
├── resilience/      # Production resilience patterns ⭐
│   ├── circuit_breaker.py    # Prevent cascading failures
│   ├── retry.py              # Recover from transient failures
│   └── health_monitor.py     # System health tracking
├── monitoring/      # Performance metrics collection ⭐
│   └── metrics.py            # Thread-safe metrics with percentiles
└── utils/           # Configuration and utilities
```

**New in v1.1:** Production-ready resilience layer with circuit breakers, retry policies, and health monitoring. See [📖 RESILIENCE.md](docs/RESILIENCE.md) for details.

### Git Workflow

We use **feature branches** and **Pull Requests**. Never commit directly to `main`.

```bash
# Create feature branch
git checkout -b feature/my-feature

# Make changes with conventional commits
git commit -m "feat(camera): add timeout handling"

# Push and create PR
git push -u origin feature/my-feature
```

### Conventional Commits

All commits must follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat(scope): description` - New feature
- `fix(scope): description` - Bug fix
- `docs: description` - Documentation only
- `test(scope): description` - Adding tests
- `refactor(scope): description` - Code restructuring

**Examples:**
```bash
git commit -m "feat(ai): implement YOLOv8 detection"
git commit -m "fix(camera): handle PTZ timeout errors"
git commit -m "docs(readme): add setup instructions"
```

See [WORKFLOW.md](.github/WORKFLOW.md) for detailed workflow guidelines.

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test
pytest tests/test_ptz_controller.py
```

## 📊 Web Dashboard

The web dashboard provides:

- **Live Video Feed** - Real-time stream with detection overlays
- **Camera Control** - Manual preset triggering
- **Statistics** - Detection counts, direction analysis
- **Event Log** - Tracking history and movements

```bash
# Start web server
uvicorn src.web.app:app --host 0.0.0.0 --port 8000

# Access dashboard
# http://localhost:8000
```

### API Endpoints

**Core Endpoints:**
- `GET /api/camera/status` - Camera status and position
- `POST /api/camera/preset/{id}` - Move to preset
- `GET /api/tracking/stats` - Tracking statistics
- `WebSocket /ws/video` - Live video stream

**Health & Resilience Endpoints:**
- `GET /api/health` - Simple health check (JSON)
- `GET /api/metrics` - Performance metrics (latencies, counters)
- `GET /api/resilience/status` - Circuit breaker and retry policy status
- `GET /health` - Minimal health check (legacy)

For detailed resilience documentation, see [📖 RESILIENCE.md](docs/RESILIENCE.md)

## 🎯 Use Cases

- **Security Monitoring** - Automatically follow suspects/intruders
- **Retail Analytics** - Track customer movement patterns
- **Traffic Analysis** - Monitor vehicle flow and direction
- **Wildlife Observation** - Track animal movements
- **Smart Home** - Automated surveillance coverage

## 🧪 Supported Cameras

Tested with:
- ✅ Hikvision PTZ cameras (ONVIF)
- ✅ Dahua PTZ cameras (ONVIF)
- ✅ Axis PTZ cameras (VAPIX/ONVIF)

Should work with any IP camera supporting:
- ONVIF protocol
- PTZ presets
- RTSP streaming

## 🚀 Deployment

### Option 1: Render.com (Full Backend)

1. Add `render.yaml`:
   ```yaml
   services:
     - type: web
       name: security-camera-ai
       env: python
       buildCommand: pip install -r requirements.txt
       startCommand: uvicorn src.web.app:app --host 0.0.0.0 --port $PORT
   ```

2. Connect GitHub repository in Render dashboard
3. Deploy automatically on push

### Option 2: Vercel (Demo Mode)

1. Create demo mode with pre-recorded video
2. Deploy frontend:
   ```bash
   vercel --prod
   ```

### Option 3: Local with ngrok (Development)

```bash
# Start local server
uvicorn src.web.app:app --port 8000

# Expose publicly
ngrok http 8000
```

## 📖 Documentation

- [Copilot Instructions](.github/copilot-instructions.md) - AI coding guidelines
- [Development Workflow](.github/WORKFLOW.md) - Git workflow and PR process
- [Folder Structure](.github/FOLDER_STRUCTURE.md) - Project organization guide
- [Deployment Guide](docs/DEPLOYMENT.md) - Deployment strategies and portfolio setup
- [Project Summary](docs/PROJECT_SUMMARY.md) - Quick reference and getting started
- [Camera Discovery](scripts/discover_camera.py) - Find and test your camera
- [API Documentation](docs/API.md) - Web API reference *(coming soon)*

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes using conventional commits
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

See [WORKFLOW.md](.github/WORKFLOW.md) for detailed guidelines.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics) - Object detection
- [python-onvif-zeep](https://github.com/quatanium/python-onvif) - ONVIF client
- [OpenCV](https://opencv.org/) - Video processing
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework

## 📧 Contact

**Your Name** - [@yourhandle](https://twitter.com/yourhandle) - your.email@example.com

Project Link: [https://github.com/yourusername/security-video-automation](https://github.com/yourusername/security-video-automation)

---

⭐ **Star this repo if you find it useful!**
