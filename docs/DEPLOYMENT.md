# Deployment Guide

## Overview

This guide covers deploying the Security Camera AI Automation system for different use cases:
- **Production** - Running on local network with real camera
- **Portfolio Demo** - Public-facing demo for showcasing
- **Development** - Local testing and development

## 🎯 Portfolio Deployment Strategy

### Recommended Approach: Hybrid Setup

```
┌──────────────────────────────────────────────┐
│         PUBLIC PORTFOLIO DEMO                │
│         (Vercel/Netlify)                     │
│                                              │
│  ✓ Pre-recorded demo video                  │
│  ✓ Static dashboard with sample data        │
│  ✓ Screenshots and visualizations           │
│  ✓ Project documentation                    │
│  ✓ GitHub repository link                   │
│                                              │
│  URL: https://security-ai-demo.vercel.app   │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│         LOCAL/PRIVATE DEPLOYMENT             │
│         (Home Server/Raspberry Pi)           │
│                                              │
│  ✓ Live camera feed                         │
│  ✓ Real-time AI detection                   │
│  ✓ Actual PTZ control                       │
│  ✓ Full tracking automation                 │
│                                              │
│  Access: http://192.168.1.100:8000          │
└──────────────────────────────────────────────┘
```

## Portfolio Demo Deployment

### Option 1: Vercel (Recommended) ⭐

**Best for:** Static demo with pre-recorded video

#### Setup Steps

1. **Create demo mode**
   ```python
   # src/web/demo.py
   from fastapi import FastAPI
   from fastapi.staticfiles import StaticFiles
   from fastapi.responses import FileResponse
   
   app = FastAPI(title="Security Camera AI - Demo")
   
   app.mount("/static", StaticFiles(directory="web/static"), name="static")
   
   @app.get("/")
   async def demo_page():
       return FileResponse("web/templates/demo.html")
   
   @app.get("/api/demo/stats")
   async def demo_stats():
       # Return pre-calculated statistics
       return {
           "total_detections": 1234,
           "tracking_events": 456,
           "directions": {
               "left_to_right": 550,
               "right_to_left": 684
           }
       }
   ```

2. **Prepare demo assets**
   ```bash
   mkdir -p web/static/demo
   # Add: sample_video.mp4, screenshots, charts
   ```

3. **Create `vercel.json`**
   ```json
   {
     "builds": [
       {
         "src": "src/web/demo.py",
         "use": "@vercel/python"
       }
     ],
     "routes": [
       {
         "src": "/(.*)",
         "dest": "src/web/demo.py"
       }
     ]
   }
   ```

4. **Deploy**
   ```bash
   # Install Vercel CLI
   npm i -g vercel
   
   # Deploy
   vercel --prod
   ```

5. **Add to portfolio**
   - Add live demo link to README
   - Include in portfolio website
   - Share on LinkedIn/Twitter

### Option 2: GitHub Pages (Static Only)

**Best for:** Documentation and screenshots

1. **Create `docs/` folder with static HTML**
2. **Enable GitHub Pages** in repository settings
3. **Access at:** `https://yourusername.github.io/security-video-automation`

### Option 3: Render.com (Full Backend)

**Best for:** Demo with limited real-time features

#### Setup

1. **Use `render.yaml`** (already created)

2. **Set environment variables** in Render dashboard:
   ```
   DEMO_MODE=True
   DEMO_VIDEO_PATH=/app/web/static/demo/sample.mp4
   ```

3. **Deploy**
   - Connect GitHub repo in Render
   - Auto-deploys on push to main

4. **Free tier limitations:**
   - Spins down after 15 minutes inactivity
   - 30-second cold start on first request
   - 750 hours/month limit

## Production Deployment (Local Network)

### Option 1: Docker (Recommended)

```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download YOLO model
RUN python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "src.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  security-camera-ai:
    build: .
    ports:
      - "8000:8000"
    environment:
      - CAMERA_IP=${CAMERA_IP}
      - CAMERA_USERNAME=${CAMERA_USERNAME}
      - CAMERA_PASSWORD=${CAMERA_PASSWORD}
      - RTSP_URL=${RTSP_URL}
    env_file:
      - .env
    volumes:
      - ./recordings:/app/recordings
      - ./logs:/app/logs
    restart: unless-stopped
    network_mode: host  # Access camera on local network
```

**Deploy:**
```bash
docker-compose up -d
```

### Option 2: Systemd Service (Linux)

```ini
# /etc/systemd/system/security-camera-ai.service
[Unit]
Description=Security Camera AI Tracking
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/security-video-automation
Environment="PATH=/home/pi/security-video-automation/venv/bin"
ExecStart=/home/pi/security-video-automation/venv/bin/uvicorn src.web.app:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

**Deploy:**
```bash
sudo systemctl enable security-camera-ai
sudo systemctl start security-camera-ai
sudo systemctl status security-camera-ai
```

### Option 3: Raspberry Pi

**Hardware Requirements:**
- Raspberry Pi 4 (4GB+ RAM recommended)
- 32GB+ SD card
- Camera on same network

**Setup:**
```bash
# Install dependencies
sudo apt-get update
sudo apt-get install python3-pip python3-venv libopencv-dev

# Clone and setup
git clone https://github.com/yourusername/security-video-automation.git
cd security-video-automation
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run on boot
sudo nano /etc/rc.local
# Add: /home/pi/security-video-automation/start.sh &
```

## Cloud Deployment (Advanced)

### AWS EC2

1. **Launch EC2 instance** (t3.medium recommended)
2. **Install dependencies**
3. **Configure security groups** (open port 8000)
4. **Setup nginx reverse proxy**
5. **Use Let's Encrypt for HTTPS**

### DigitalOcean Droplet

Similar to EC2, but simpler setup:
```bash
# Create droplet with Ubuntu 22.04
# SSH into droplet
ssh root@your_droplet_ip

# Setup application
git clone https://github.com/yourusername/security-video-automation.git
cd security-video-automation
./deploy.sh
```

## Making Your Deployment Portfolio-Ready

### 1. Create Demo Video

```bash
# Record screen capture
# Tools: OBS Studio, Loom, QuickTime

# Show:
- Camera feed with detections
- Subject moving right-to-left
- Camera automatically tracking
- Dashboard statistics updating
- Manual preset control
```

### 2. Add Screenshots to README

```markdown
## Screenshots

### Live Detection
![Detection](docs/screenshots/detection.png)

### Auto-Tracking in Action
![Tracking](docs/screenshots/tracking.gif)

### Dashboard
![Dashboard](docs/screenshots/dashboard.png)
```

### 3. Create Portfolio Case Study

```markdown
# Security Camera AI - Case Study

## Problem
Manual camera monitoring is time-consuming and subjects often leave the field of view before operators can react.

## Solution
AI-powered automated tracking that detects subjects, analyzes movement direction, and controls PTZ camera to maintain visual coverage.

## Technologies
- Python, FastAPI, YOLOv8
- OpenCV, ONVIF
- WebSockets for real-time updates

## Results
- 95% tracking accuracy
- <2 second response time
- Zero operator intervention required

## Challenges Overcome
1. Network latency with RTSP streams
2. ONVIF protocol compatibility
3. Real-time processing performance
```

### 4. Add to LinkedIn/Portfolio

**LinkedIn Project Section:**
```
Title: AI-Powered Security Camera Automation
Description: Built an automated tracking system using YOLOv8 for object detection and ONVIF for PTZ camera control. Analyzes motion direction and triggers camera presets to maintain subject tracking.

Skills: Python • Computer Vision • FastAPI • IoT • Real-time Systems
Link: https://security-ai-demo.vercel.app
```

### 5. Create YouTube Demo

**Video Outline:**
1. Introduction (30s)
2. Demo of tracking in action (1-2 min)
3. Quick code walkthrough (1 min)
4. Architecture overview (30s)
5. Results and use cases (30s)

**Upload and embed in README:**
```markdown
[![Demo Video](https://img.youtube.com/vi/YOUR_ID/maxresdefault.jpg)](https://youtu.be/YOUR_ID)
```

## Environment Variables for Deployment

### Production (Local)
```env
CAMERA_IP=192.168.1.100
CAMERA_USERNAME=admin
CAMERA_PASSWORD=secure_password
RTSP_URL=rtsp://admin:secure_password@192.168.1.100:554/stream1
DEMO_MODE=False
DEBUG=False
```

### Demo (Public)
```env
DEMO_MODE=True
DEMO_VIDEO_PATH=/app/web/static/demo/sample.mp4
DEBUG=False
ALLOWED_ORIGINS=https://your-demo-url.vercel.app
```

## Monitoring & Maintenance

### Logs
```bash
# View application logs
tail -f logs/app.log

# Docker logs
docker-compose logs -f

# Systemd logs
sudo journalctl -u security-camera-ai -f
```

### Health Checks
```python
# src/web/app.py
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "camera_connected": camera.is_connected(),
        "ai_model_loaded": detector.is_ready(),
        "tracking_active": engine.is_running()
    }
```

### Performance Monitoring
- CPU usage (should be <50%)
- Memory usage (should be <2GB)
- Network latency (<100ms)
- Frame processing rate (15-30 FPS)

## Security Considerations

### For Public Demos
- ✅ Use demo mode with pre-recorded video
- ✅ No real camera credentials exposed
- ✅ Rate limiting on API endpoints
- ✅ CORS configured properly

### For Production
- 🔒 Camera on isolated VLAN
- 🔒 Strong passwords, change defaults
- 🔒 HTTPS for web interface
- 🔒 Firewall rules (only local network)
- 🔒 Regular security updates

## Cost Estimate

### Portfolio Demo (Free)
- Vercel hosting: **$0/month**
- GitHub Pages: **$0/month**
- Total: **$0/month** ✅

### Local Deployment (One-time)
- Raspberry Pi 4 (4GB): **$55**
- SD Card (32GB): **$10**
- Power Supply: **$8**
- Total: **~$73** (no recurring costs)

### Cloud Deployment (Optional)
- Render.com: **$0-7/month** (free tier or hobby)
- AWS EC2 t3.medium: **~$30/month**
- DigitalOcean Droplet: **$12-24/month**

## Recommended Deployment Path

### Phase 1: Local Development ✅
```bash
python src/main.py
# Test with real camera on local network
```

### Phase 2: Create Demo Assets ✅
- Record sample video
- Take screenshots
- Generate statistics
- Create demo HTML page

### Phase 3: Deploy Demo to Vercel ✅
```bash
vercel --prod
# Public portfolio link
```

### Phase 4: Production on Raspberry Pi (Optional)
```bash
# Run 24/7 on local network
docker-compose up -d
```

### Phase 5: Promote ✅
- Add to portfolio website
- Share on LinkedIn
- Include in resume
- Create YouTube demo

## Troubleshooting Deployment

### Demo Mode Issues
```python
# Verify demo assets exist
ls -la web/static/demo/
# Should contain: sample_video.mp4, screenshots/

# Test locally first
DEMO_MODE=True uvicorn src.web.demo:app
```

### Docker Issues
```bash
# Check logs
docker-compose logs

# Rebuild
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Network Issues
```bash
# Test camera connectivity
ping 192.168.1.100

# Test RTSP stream
ffplay rtsp://admin:password@192.168.1.100:554/stream1

# Test ONVIF
python scripts/discover_camera.py 192.168.1.100
```

## Next Steps

1. **Set up demo mode** with pre-recorded footage
2. **Deploy to Vercel** for public portfolio
3. **Create demo video** for YouTube
4. **Add project to portfolio** website
5. **Share on LinkedIn** with demo link
6. **Run production** on local network (optional)

---

**Need Help?** Open an issue on GitHub or check the troubleshooting section.
