# Development Workflow

## Git Workflow

### Branch Strategy

**NEVER commit directly to `main`**. Always use feature branches and Pull Requests.

```
main (protected)
  ↑
  └── Pull Request (requires review)
       ↑
       └── feature/* branches (your work)
```

### Creating a Feature Branch

```bash
# Ensure you're on main and up to date
git checkout main
git pull origin main

# Create a new feature branch
git checkout -b feature/camera-discovery
git checkout -b feature/ai-detection
git checkout -b feature/ptz-control
git checkout -b fix/stream-connection
git checkout -b docs/readme-update
```

### Branch Naming Conventions

- `feature/*` - New features (e.g., `feature/motion-tracking`)
- `fix/*` - Bug fixes (e.g., `fix/ptz-timeout`)
- `refactor/*` - Code refactoring (e.g., `refactor/detector-class`)
- `docs/*` - Documentation updates (e.g., `docs/add-setup-guide`)
- `test/*` - Adding tests (e.g., `test/ptz-controller`)
- `chore/*` - Maintenance tasks (e.g., `chore/update-deps`)

## Conventional Commits

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature for the user
- `fix`: Bug fix
- `docs`: Documentation only changes
- `style`: Code style changes (formatting, missing semicolons, etc.)
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `build`: Changes to build system or dependencies
- `ci`: Changes to CI configuration files and scripts
- `chore`: Other changes that don't modify src or test files
- `revert`: Reverts a previous commit

### Scopes (for this project)

- `camera`: PTZ camera control and ONVIF integration
- `ai`: Object detection and motion tracking
- `video`: Video stream handling and processing
- `automation`: Tracking engine and rules
- `config`: Configuration files
- `web`: Web dashboard (if implemented)
- `scripts`: Utility scripts

### Examples

```bash
# Feature commits
git commit -m "feat(camera): add ONVIF camera discovery script"
git commit -m "feat(ai): implement YOLOv8 object detection"
git commit -m "feat(automation): add right-to-left direction tracking"
git commit -m "feat(video): implement threaded RTSP stream handler"

# Bug fixes
git commit -m "fix(camera): handle PTZ timeout errors gracefully"
git commit -m "fix(ai): correct bounding box coordinates calculation"
git commit -m "fix(video): prevent frame queue overflow"

# Documentation
git commit -m "docs(readme): add camera setup instructions"
git commit -m "docs(workflow): add git workflow and commit guidelines"

# Refactoring
git commit -m "refactor(ai): extract detection logic into separate class"
git commit -m "refactor(camera): simplify preset management"

# Tests
git commit -m "test(camera): add unit tests for PTZ controller"
git commit -m "test(ai): add motion tracker direction tests"

# Build/Dependencies
git commit -m "build(deps): upgrade ultralytics to v8.1.0"
git commit -m "build: add opencv-python to requirements"

# Breaking changes
git commit -m "feat(api)!: change preset API to use names instead of tokens

BREAKING CHANGE: goto_preset() now requires preset name string instead of token ID"
```

### Multi-line Commit Messages

For complex changes, use multi-line commits:

```bash
git commit -m "feat(automation): implement zone-based tracking engine

- Add zone detection based on frame position
- Integrate motion tracker with PTZ controller
- Add configurable tracking rules from YAML
- Implement preset triggering on direction change

Closes #12"
```

## Pull Request Workflow

### 1. Make Your Changes

```bash
# On your feature branch
git checkout -b feature/camera-discovery

# Make changes, then stage and commit
git add scripts/discover_camera.py
git commit -m "feat(camera): add ONVIF camera discovery script"

# Make more changes
git add src/camera/ptz_controller.py
git commit -m "feat(camera): implement PTZ preset control"
```

### 2. Push to Remote

```bash
# First push of new branch
git push -u origin feature/camera-discovery

# Subsequent pushes
git push
```

### 3. Create Pull Request

**On GitHub:**

1. Go to your repository
2. Click "Pull requests" → "New pull request"
3. Select your feature branch
4. Fill in the PR template:

```markdown
## Description
Implements camera discovery script to detect ONVIF-compatible PTZ cameras on the network.

## Changes
- Added `scripts/discover_camera.py` for camera detection
- Implemented `PTZController` class for preset control
- Added camera configuration YAML template
- Updated requirements.txt with `onvif-zeep`

## Testing
- [x] Tested with Hikvision DS-2DE2A404IW-DE3
- [x] Verified ONVIF service detection
- [x] Listed all available presets
- [ ] Tested with Dahua camera (no access)

## Screenshots/Logs
```
✓ Camera found!
  Manufacturer: Hikvision
  Model: DS-2DE2A404IW-DE3
  Firmware: V5.7.3
✓ PTZ Service Available: Yes
✓ Configured Presets: 5
```

## Related Issues
Closes #1
```

### 4. Code Review

- Wait for review from team members (or yourself if solo)
- Address feedback with new commits
- Push updates to the same branch

```bash
# After review feedback
git add src/camera/ptz_controller.py
git commit -m "fix(camera): add timeout parameter to preset movements"
git push
```

### 5. Merge to Main

**After approval:**

1. Ensure branch is up to date with main:
   ```bash
   git checkout feature/camera-discovery
   git fetch origin
   git rebase origin/main
   git push --force-with-lease
   ```

2. Merge via GitHub (use "Squash and merge" or "Rebase and merge")

3. Delete feature branch:
   ```bash
   git checkout main
   git pull origin main
   git branch -d feature/camera-discovery
   git push origin --delete feature/camera-discovery
   ```

## PR Best Practices

### Keep PRs Small
- **Ideal size**: 200-400 lines of code
- **Maximum**: 800 lines
- Split large features into multiple PRs

### Good PR Examples

✅ **Good - Small and focused**
- PR: "Add ONVIF camera discovery script" (120 lines)
- PR: "Implement motion direction tracking" (200 lines)

❌ **Bad - Too large**
- PR: "Implement entire tracking system" (2,000 lines)

### Self-Review Checklist

Before creating PR:

- [ ] Code follows PEP 8 style guide
- [ ] All functions have docstrings
- [ ] Type hints added to function signatures
- [ ] Tests added/updated (if applicable)
- [ ] No hardcoded credentials
- [ ] Error handling implemented
- [ ] Logging added for debugging
- [ ] Configuration files updated
- [ ] README updated (if needed)
- [ ] Conventional commits used

## Web Dashboard & Deployment

### Should You Add a Web Interface?

**YES - For Portfolio Showcase** ✅

A web dashboard significantly enhances this project for your portfolio:

### Portfolio Benefits

1. **Visual Impact** 
   - Live video feed display
   - Real-time detection overlays (bounding boxes)
   - Camera movement visualization
   - Tracking statistics and charts

2. **Demonstrable Features**
   - Employers can see it working without running code
   - Deploy publicly with demo mode
   - Share direct link on resume/LinkedIn

3. **Full-Stack Demonstration**
   - Backend: Python/FastAPI
   - Frontend: React/Vue/vanilla JS
   - Real-time: WebSockets
   - Deployment: Cloud platform
   - Shows broader skills beyond Python

### Recommended Web Stack

#### Backend: FastAPI
```python
# src/web/app.py
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
import cv2

app = FastAPI(title="Security Camera AI Tracker")

# Serve frontend
app.mount("/static", StaticFiles(directory="web/static"), name="static")

@app.get("/")
async def dashboard():
    return FileResponse("web/templates/index.html")

@app.get("/api/camera/status")
async def camera_status():
    """Get current camera status and position"""
    return {
        "connected": True,
        "current_preset": "zone_center",
        "tracking_active": True,
        "detections": 3
    }

@app.websocket("/ws/video")
async def video_feed(websocket: WebSocket):
    """Stream video frames with detection overlays"""
    await websocket.accept()
    
    while True:
        frame = get_latest_frame_with_detections()
        _, buffer = cv2.imencode('.jpg', frame)
        await websocket.send_bytes(buffer.tobytes())

@app.post("/api/camera/preset/{preset_id}")
async def move_camera(preset_id: int):
    """Manually trigger camera preset"""
    ptz_controller.goto_preset(str(preset_id))
    return {"status": "moving", "preset": preset_id}

@app.get("/api/tracking/stats")
async def tracking_statistics():
    """Get tracking statistics"""
    return {
        "total_detections": 1234,
        "directions": {
            "left_to_right": 450,
            "right_to_left": 784
        },
        "most_active_zone": "zone_center",
        "uptime": "2d 5h 23m"
    }
```

#### Frontend: Modern HTML/JS (or React)
```html
<!-- web/templates/index.html -->
<!DOCTYPE html>
<html>
<head>
    <title>Security Camera AI Tracker</title>
    <link rel="stylesheet" href="/static/css/dashboard.css">
</head>
<body>
    <div class="dashboard">
        <div class="video-container">
            <canvas id="videoCanvas"></canvas>
            <div class="detections-overlay">
                <span class="detection-count">3 objects detected</span>
            </div>
        </div>
        
        <div class="controls-panel">
            <h3>Camera Control</h3>
            <div class="preset-buttons">
                <button onclick="moveToPreset(1)">Left Zone</button>
                <button onclick="moveToPreset(2)">Center</button>
                <button onclick="moveToPreset(3)">Right Zone</button>
            </div>
            
            <div class="tracking-toggle">
                <label>
                    <input type="checkbox" id="autoTracking" checked>
                    Auto-tracking enabled
                </label>
            </div>
        </div>
        
        <div class="stats-panel">
            <h3>Statistics</h3>
            <div class="stat">
                <span class="label">Total Detections:</span>
                <span class="value" id="totalDetections">0</span>
            </div>
            <div class="stat">
                <span class="label">Right → Left:</span>
                <span class="value" id="rtlCount">0</span>
            </div>
            <div class="stat">
                <span class="label">Left → Right:</span>
                <span class="value" id="ltrCount">0</span>
            </div>
            
            <canvas id="directionChart"></canvas>
        </div>
        
        <div class="events-log">
            <h3>Event Log</h3>
            <ul id="eventsList">
                <!-- Events populated via JavaScript -->
            </ul>
        </div>
    </div>
    
    <script src="/static/js/dashboard.js"></script>
</body>
</html>
```

```javascript
// web/static/js/dashboard.js
const ws = new WebSocket('ws://localhost:8000/ws/video');
const canvas = document.getElementById('videoCanvas');
const ctx = canvas.getContext('2d');

// Receive video frames
ws.onmessage = (event) => {
    const blob = event.data;
    const img = new Image();
    img.onload = () => {
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    };
    img.src = URL.createObjectURL(blob);
};

// Manual camera control
async function moveToPreset(presetId) {
    const response = await fetch(`/api/camera/preset/${presetId}`, {
        method: 'POST'
    });
    const data = await response.json();
    addEvent(`Camera moving to preset ${presetId}`);
}

// Update statistics
async function updateStats() {
    const response = await fetch('/api/tracking/stats');
    const stats = await response.json();
    
    document.getElementById('totalDetections').textContent = stats.total_detections;
    document.getElementById('rtlCount').textContent = stats.directions.right_to_left;
    document.getElementById('ltrCount').textContent = stats.directions.left_to_right;
}

setInterval(updateStats, 5000);
```

### Deployment Options

#### Option 1: Render.com (Recommended for Backend)
**Best for:** Python backend with always-on service

**Pros:**
- Free tier available
- Native Python/Docker support
- Database included
- Auto-deploy from GitHub
- WebSocket support

**Cons:**
- Free tier spins down after inactivity (30s cold start)
- Limited to 750 hours/month free

**Setup:**
```yaml
# render.yaml
services:
  - type: web
    name: security-camera-ai
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn src.web.app:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: CAMERA_IP
        sync: false
      - key: CAMERA_USERNAME
        sync: false
      - key: CAMERA_PASSWORD
        sync: false
```

#### Option 2: Vercel (For Static Dashboard)
**Best for:** Frontend-only demo mode

**Pros:**
- Instant deployment
- Excellent for portfolio
- Custom domain
- Edge network (fast)

**Cons:**
- Serverless (no long-running processes)
- Can't handle continuous video stream
- **Cannot control real camera** (no persistent connection)

**Use Case:** Demo mode with pre-recorded video

```json
// vercel.json
{
  "builds": [
    {
      "src": "web/api/*.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "web/$1"
    }
  ]
}
```

#### Option 3: Railway.app
**Best for:** Full-stack with background tasks

**Pros:**
- $5 free credit/month
- Better performance than Render free tier
- No sleep on inactivity
- Good for real-time apps

**Cons:**
- Requires credit card
- More expensive after free tier

#### Option 4: Hybrid Approach (Recommended for Portfolio)

**Architecture:**
1. **Vercel** - Host static demo dashboard with pre-recorded footage
2. **Local/Home Server** - Run real tracking system
3. **ngrok/Cloudflare Tunnel** - Expose local API to public (optional)

```
┌─────────────────────────────────────────┐
│  Vercel (Public Portfolio)              │
│  - Static demo with sample video        │
│  - Pre-recorded tracking results        │
│  - Screenshots and charts                │
│  - GitHub link to source code           │
└─────────────────────────────────────────┘
                 +
┌─────────────────────────────────────────┐
│  Local Setup (Real Implementation)      │
│  - Live camera feed                      │
│  - Real PTZ control                      │
│  - AI tracking                           │
│  - Local dashboard access                │
└─────────────────────────────────────────┘
```

### Recommended Portfolio Approach

**Phase 1: Local Dashboard** ✅
```bash
# Run locally for development
uvicorn src.web.app:app --reload --host 0.0.0.0 --port 8000
```

**Phase 2: Static Demo for Portfolio** ✅
- Create demo mode with pre-recorded video
- Show tracking in action
- Deploy to Vercel (free)
- Add to portfolio website

**Phase 3: Video Documentation** ✅
- Record screen capture of system working
- Upload to YouTube/Loom
- Embed in README and portfolio
- Include in LinkedIn projects

### Portfolio Project Structure

```
security-video-automation/
├── src/                    # Core tracking system
├── web/
│   ├── app.py             # FastAPI backend
│   ├── static/
│   │   ├── css/
│   │   ├── js/
│   │   └── demo/
│   │       └── sample_video.mp4  # Demo footage
│   └── templates/
│       ├── index.html     # Live dashboard
│       └── demo.html      # Portfolio demo page
├── docs/
│   ├── DEPLOYMENT.md      # Deployment instructions
│   ├── DEMO.md           # How to run demo
│   └── screenshots/       # For README
└── README.md              # Include live demo link
```

### README Addition for Portfolio

```markdown
## 🎬 Live Demo

**[View Live Demo →](https://security-camera-ai.vercel.app)**

The demo runs on pre-recorded footage showing:
- Real-time object detection
- Motion direction analysis (right-to-left tracking)
- Automatic camera preset triggering
- Event logging and statistics

### Demo Video
[![Demo Video](https://img.youtube.com/vi/YOUR_VIDEO_ID/maxresdefault.jpg)](https://www.youtube.com/watch?v=YOUR_VIDEO_ID)

## Features Showcase

- 🎥 **Live Video Processing** - Real-time RTSP stream handling
- 🤖 **AI Object Detection** - YOLOv8 person/vehicle detection
- 📍 **Motion Tracking** - Direction analysis and trajectory prediction
- 🎮 **PTZ Control** - Automated camera movements via ONVIF
- 📊 **Web Dashboard** - Real-time monitoring and statistics
- ⚙️ **Configurable Rules** - YAML-based tracking configuration
```

## Commit Message Workflow

### Interactive Staging

```bash
# Stage specific changes
git add -p src/camera/ptz_controller.py

# Review what's staged
git diff --staged

# Commit with message
git commit -m "feat(camera): add preset timeout handling"
```

### Amending Last Commit

```bash
# If you forgot something
git add forgotten_file.py
git commit --amend --no-edit

# Or change commit message
git commit --amend -m "feat(camera): add preset timeout and retry logic"
```

### Conventional Commits CLI Tool (Optional)

```bash
# Install commitizen for guided commits
pip install commitizen

# Use interactive commit
cz commit
```

## Workflow Summary

```
1. Create feature branch
   └─> git checkout -b feature/my-feature

2. Make changes & commit (conventional commits)
   └─> git commit -m "feat(scope): description"

3. Push to remote
   └─> git push -u origin feature/my-feature

4. Create Pull Request on GitHub
   └─> Fill in PR template
   └─> Request review

5. Address feedback
   └─> Make changes
   └─> Push updates

6. Merge to main (after approval)
   └─> Use GitHub UI
   └─> Delete feature branch

7. Pull latest main
   └─> git checkout main
   └─> git pull origin main
```

## Questions?

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed contribution guidelines.
