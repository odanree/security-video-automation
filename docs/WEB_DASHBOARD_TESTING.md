# Web Dashboard Testing Guide

## Overview

The web dashboard provides a professional interface for monitoring and controlling the security camera AI tracking system. This guide walks you through testing all features.

## Prerequisites

✅ **Dependencies Installed:**
```bash
pip install fastapi uvicorn jinja2 python-multipart websockets
```

✅ **Camera Configuration:**
- Camera IP and credentials in `config/camera_config.yaml`
- RTSP stream URL configured
- PTZ presets set up (see [CAMERA_SETUP.md](CAMERA_SETUP.md))

## Starting the Dashboard

### Method 1: Using Startup Script (Recommended)
```bash
# From project root
python start_dashboard.py
```

### Method 2: Direct Uvicorn Command
```bash
# Navigate to src directory
cd src

# Start server
uvicorn web.app:app --reload --host 0.0.0.0 --port 8000
```

### Method 3: From Project Root
```bash
# Using full module path
uvicorn src.web.app:app --reload --host 0.0.0.0 --port 8000
```

**Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

## Accessing the Dashboard

Open your browser to:
- **Local:** http://localhost:8000
- **Network:** http://YOUR_IP:8000 (accessible from other devices on network)

## Testing Checklist

### ✅ 1. Initial Load

**Test:**
- Dashboard loads without errors
- All UI sections visible (header, stats, video, controls, events)

**Expected:**
- Dark theme interface
- Connection status shows "Connected" or "Disconnected"
- Stats cards show "0" initially

**Troubleshooting:**
- If page doesn't load: Check console for errors
- If styles missing: Verify `/static/css/style.css` exists
- If JS errors: Check browser console (F12)

---

### ✅ 2. Video Stream

**Test:**
- Video container displays MJPEG stream
- Detection overlays appear when objects detected
- Frame rate updates in real-time

**Expected:**
- Live camera feed displays
- Bounding boxes around detected persons/vehicles
- FPS counter updates (15-30 FPS typical)

**Troubleshooting:**
- **No video:** Check RTSP URL in `camera_config.yaml`
- **Black screen:** Camera may be offline or credentials wrong
- **Stream timeout:** Verify network connectivity to camera
- **No detections:** Ensure YOLOv8 model loaded (`yolov8n.pt`)

**Test Commands:**
```bash
# Test RTSP stream directly
ffplay "rtsp://username:password@192.168.1.100:554/stream1"

# Check if camera accessible
ping 192.168.1.100
```

---

### ✅ 3. WebSocket Real-Time Updates

**Test:**
- Open browser DevTools (F12) → Network → WS tab
- Verify WebSocket connection to `/ws/updates`
- Stats should update every 1-2 seconds

**Expected:**
- WebSocket shows "101 Switching Protocols" (connected)
- Messages received with JSON data: `{"total_detections": 5, "active_tracks": 2, ...}`
- Stats cards update automatically

**Troubleshooting:**
- **WebSocket fails:** Check console for errors
- **Connection closes immediately:** Server may not support WebSockets
- **No updates:** Backend may not be sending data

**Browser Console Check:**
```javascript
// Should see:
WebSocket connected
```

---

### ✅ 4. Statistics Cards

**Test:**
- Detections counter increases when objects appear
- Active tracks shows currently tracked subjects
- FPS displays current frame rate
- Events counter increments

**Expected Values:**
- **Detections:** 0-100+ (depends on activity)
- **Active Tracks:** 0-10 (simultaneous tracked objects)
- **FPS:** 15-30 (real-time processing)
- **Events:** Cumulative count

**Troubleshooting:**
- **Stats stuck at 0:** AI detector may not be running
- **FPS too low (<10):** CPU overload, try smaller model (`yolov8n.pt`)
- **Events not logging:** Check backend event recording

---

### ✅ 5. Manual PTZ Control

#### Directional Pad

**Test:**
1. Click **Up** button
2. Click **Down** button
3. Click **Left** button
4. Click **Right** button

**Expected:**
- Camera pans/tilts in corresponding direction
- Movement smooth and responsive
- Speed controlled by slider

**Troubleshooting:**
- **No movement:** Check PTZ enabled in config
- **Wrong direction:** Verify camera orientation
- **Timeout errors:** Camera may not support continuous movement

#### Preset Selection

**Test:**
1. Open preset dropdown
2. Select "zone_left" preset
3. Camera moves to saved position

**Expected:**
- Dropdown populated with presets from camera
- Camera moves to preset within 1-2 seconds
- Smooth transition

**Troubleshooting:**
- **Empty dropdown:** Camera presets not configured
- **Move fails:** Check preset token matches camera
- **See:** [scripts/calibrate_presets.py](../scripts/calibrate_presets.py)

#### Speed Slider

**Test:**
1. Adjust slider to 25%
2. Test directional movement (slower)
3. Adjust slider to 100%
4. Test directional movement (faster)

**Expected:**
- Slider updates speed display percentage
- Lower speed = slower pan/tilt
- Higher speed = faster movement

---

### ✅ 6. Automated Tracking Control

**Test:**
1. Click **Start Tracking** button
2. Walk in front of camera (right to left)
3. Observe camera automatically move to follow
4. Click **Stop Tracking** button

**Expected:**
- Status badge changes to "Active"
- Camera moves to presets based on subject position
- Detections logged in events
- Status returns to "Inactive" when stopped

**Troubleshooting:**
- **Tracking doesn't start:** Check tracking engine initialized
- **Camera doesn't move:** Verify tracking rules in config
- **Wrong preset triggered:** Review zone definitions in config

---

### ✅ 7. System Status Indicators

**Test:**
- Check **Camera** status (✓ Connected or ✗ Disconnected)
- Check **AI Model** status (✓ Loaded or ✗ Not Loaded)
- Check **PTZ** status (✓ Enabled or ✗ Disabled)

**Expected:**
- All show ✓ (green check) if properly configured
- Updates every 10 seconds via polling

**Troubleshooting:**
- **Camera Disconnected:** Check IP/credentials
- **AI Not Loaded:** Run `python src/main.py` once to download model
- **PTZ Disabled:** Set `ptz_enabled: true` in config

---

### ✅ 8. Events Log

**Test:**
1. Walk in front of camera
2. Check events table updates with new detections
3. Verify timestamp, object class, confidence, direction

**Expected:**
- New events appear in real-time
- Table scrollable if many events
- Each event shows:
  - **Type:** "Detection"
  - **Timestamp:** HH:MM:SS
  - **Class:** "person", "car", etc.
  - **Confidence:** 0.0-1.0 (e.g., 0.87 = 87%)
  - **Direction:** "left_to_right", "right_to_left", etc.

**Troubleshooting:**
- **No events:** AI may not be detecting objects
- **Events not updating:** Check browser console for API errors
- **Old events missing:** Events stored in memory (cleared on restart)

---

### ✅ 9. Responsive Design (Mobile/Tablet)

**Test:**
1. Open dashboard on phone/tablet
2. Resize browser window to mobile size
3. Test controls still functional

**Expected:**
- Layout adapts to smaller screens
- Stats grid stacks vertically
- Controls remain accessible
- Video container resizes properly

**CSS Breakpoints:**
- **Mobile:** < 768px
- **Tablet:** 768px - 1024px
- **Desktop:** > 1024px

---

### ✅ 10. Error Handling

**Test:**
1. Disconnect camera network cable
2. Check connection status updates
3. Reconnect cable
4. Verify recovery

**Expected:**
- Connection status changes to "Disconnected"
- Video stream shows error message
- WebSocket attempts reconnect
- System recovers when camera back online

**Troubleshooting:**
- **No error shown:** Error handling may need improvement
- **Page crashes:** Add try/catch in JavaScript
- **No reconnect:** WebSocket reconnect logic issue

---

## API Testing (Advanced)

### Using cURL

**Get System Status:**
```bash
curl http://localhost:8000/api/status
```

**Get Statistics:**
```bash
curl http://localhost:8000/api/statistics
```

**Start Tracking:**
```bash
curl -X POST http://localhost:8000/api/tracking/start
```

**Stop Tracking:**
```bash
curl -X POST http://localhost:8000/api/tracking/stop
```

**Get Camera Presets:**
```bash
curl http://localhost:8000/api/camera/presets
```

**Move to Preset:**
```bash
curl -X POST http://localhost:8000/api/camera/preset/1
```

**Continuous Move:**
```bash
curl -X POST http://localhost:8000/api/camera/move \
  -H "Content-Type: application/json" \
  -d '{"pan_velocity": 0.5, "tilt_velocity": 0, "duration": 1.0}'
```

### Using Python Requests

```python
import requests

BASE_URL = "http://localhost:8000"

# Get status
response = requests.get(f"{BASE_URL}/api/status")
print(response.json())

# Start tracking
response = requests.post(f"{BASE_URL}/api/tracking/start")
print(response.status_code)  # Should be 200

# Move camera
response = requests.post(
    f"{BASE_URL}/api/camera/move",
    json={"pan_velocity": 0.5, "tilt_velocity": 0, "duration": 1.0}
)
```

---

## Performance Benchmarks

### Expected Metrics

| Metric | Target | Acceptable | Poor |
|--------|--------|------------|------|
| **Video FPS** | 25-30 | 15-24 | <15 |
| **Detection Latency** | <100ms | 100-200ms | >200ms |
| **WebSocket Ping** | <50ms | 50-100ms | >100ms |
| **PTZ Response** | <2s | 2-4s | >4s |
| **Page Load Time** | <2s | 2-5s | >5s |

### Monitoring Performance

**Browser DevTools (F12):**
- **Network Tab:** Check API response times
- **Performance Tab:** Record page performance
- **Console:** Watch for warnings/errors

**System Resources:**
- **CPU Usage:** Should be <50%
- **Memory:** <2GB for basic operation
- **Network:** ~5-10 Mbps for video stream

---

## Common Issues & Solutions

### Issue: Video stream not loading

**Possible Causes:**
1. RTSP URL incorrect
2. Camera offline
3. Network firewall blocking
4. Wrong credentials

**Solution:**
```bash
# Test RTSP URL
ffplay "rtsp://admin:password@192.168.1.100:554/stream1"

# Ping camera
ping 192.168.1.100

# Check config
cat config/camera_config.yaml
```

---

### Issue: PTZ controls don't work

**Possible Causes:**
1. ONVIF not enabled on camera
2. Wrong port (try 80, 8080, 8000)
3. Camera doesn't support ONVIF
4. Presets not configured

**Solution:**
```bash
# Test camera discovery
python scripts/discover_camera.py 192.168.1.100

# Test PTZ
python scripts/test_ptz.py
```

---

### Issue: High CPU usage

**Possible Causes:**
1. Processing every frame
2. Using large YOLO model
3. High resolution stream

**Solution:**
```python
# In src/web/app.py, process every Nth frame
if frame_count % 3 == 0:  # Process every 3rd frame
    engine.process_frame(frame)
```

Use smaller model:
```bash
# Download yolov8n.pt (nano - fastest)
# Instead of yolov8l.pt (large - slowest)
```

---

## Next Steps

After successful testing:

1. **Configure Tracking Rules** - Edit `config/tracking_rules.yaml`
2. **Set Up Camera Presets** - Run `scripts/calibrate_presets.py`
3. **Deploy to Production** - See [DEPLOYMENT.md](DEPLOYMENT.md)
4. **Add Authentication** - Secure dashboard with login
5. **Record Events** - Set up database for event storage

---

## Feedback & Issues

If you encounter issues during testing:

1. Check logs in terminal (where uvicorn is running)
2. Check browser console (F12)
3. Review configuration files
4. See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
5. Open GitHub issue with details

---

**Happy Testing! 🚀**
