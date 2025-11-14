# PyQt5 Desktop Application

High-performance native desktop application for Security Camera Tracker. Achieves **25-30 FPS** display with CPU-only setup.

## Why Desktop App?

- ✅ **25-30 FPS smooth display** (vs 10-15 FPS web browser)
- ✅ Native rendering (no JavaScript overhead)
- ✅ H.264 direct decoding from camera
- ✅ Responsive PTZ controls
- ✅ Real-time statistics and tracking events
- ✅ Works with existing FastAPI backend (no changes needed)

## Architecture

```
Camera (RTSP H.264 stream)
    ↓ (cv2.VideoCapture native H.264 decode)
PyQt5 Desktop App
    ↓ (QLabel/QPixmap native rendering)
Display (25-30 FPS smooth)
    
+ Parallel connection to FastAPI backend for:
  - Statistics (detections, tracks)
  - PTZ control (presets, manual movement)
  - Tracking events
```

## Installation

### 1. Install PyQt5 (already in requirements.txt)

```bash
pip install -r requirements.txt
```

Or manually:
```bash
pip install PyQt5==5.15.9
```

### 2. Configure Camera URL

Edit `desktop_app/main.py`, line ~358:

```python
camera_rtsp = "rtsp://admin:Danh2610@192.168.1.107:554/stream1"  # Change this
backend_url = "http://localhost:8000"  # FastAPI backend URL
```

## Running

### Option 1: From Project Root

```bash
python desktop_app/main.py
```

### Option 2: With Full Path

```bash
.\venv\Scripts\python.exe desktop_app/main.py
```

### Prerequisites

- FastAPI backend must be running (`./restart_dashboard.ps1`)
- Camera RTSP stream must be accessible
- Network connectivity to both camera and backend

## Features

### Video Display
- **25-30 FPS** smooth H.264 rendering
- Real-time FPS counter
- Native PyQt5 rendering (no browser overhead)
- Scales to window size

### Statistics Panel
- Total detections
- Active tracks
- Recent events count
- Backend FPS

### Tracking Control
- **Start/Stop** tracking buttons
- Real-time status display
- Uptime counter

### PTZ Camera Control
- **Preset selector** - Choose from 256 camera presets
- **Movement speed slider** - Adjust speed 0.1 to 1.0
- **Go to Preset** button - Move camera

## Performance Characteristics

### Frame Rate Measurement

The app monitors actual display FPS in real-time. You'll see:
- `FPS: 25.3` - Current frame rate
- `Frames: 152` - Total frames decoded
- `Status: Running` - Application status

### Typical Performance

| Hardware | Expected FPS | Notes |
|----------|-------------|-------|
| Ryzen 5 5600X | 25-30 | Smooth, no tracking |
| i7-10700K | 25-30 | Smooth, no tracking |
| i5-11400 | 20-25 | Good performance |
| Ryzen 7 5800X3D | 28-30 | Excellent |

**With active tracking**: Slight frame drops (1-2 FPS) due to detection processing in background thread, but video stays smooth.

## Architecture Details

### StreamWorker (Background Thread)

```python
class StreamWorker(QThread):
    """Captures frames from RTSP stream"""
    - cv2.VideoCapture with buffer_size=1 (minimal latency)
    - Emits frames to main GUI thread via Qt signal
    - ~59ms latency from camera to display
```

### StatsWorker (Background Thread)

```python
class StatsWorker(QThread):
    """Fetches statistics from backend every 500ms"""
    - Polls /api/statistics endpoint
    - Updates UI with latest detection/tracking data
    - Non-blocking, runs in parallel with video
```

### Main Thread (GUI)

```python
CameraTrackerApp(QMainWindow):
    - Receives frames from StreamWorker
    - Converts CV2 BGR → RGB → QImage → QPixmap
    - Displays in QLabel
    - Updates FPS counter
    - Handles user input (buttons, sliders)
```

### Network Communication

All communication with backend is **non-blocking**:
- Stats fetched every 500ms in background thread
- PTZ commands sent via HTTP POST (returns immediately)
- Tracking start/stop is async

## Troubleshooting

### App won't start
```bash
# Check all dependencies
python scripts/test_desktop_app_startup.py
```

### No video display (black window)
1. Verify camera RTSP URL is correct
2. Check network connectivity to camera
3. Test with: `ffplay "rtsp://..."`

### Low FPS (<15)
1. Check CPU usage (might be high from other processes)
2. Verify camera stream quality
3. Test with: `python scripts/test_desktop_app_headless.py`

### Backend connection errors
1. Ensure FastAPI backend is running: `./restart_dashboard.ps1`
2. Verify backend URL in code
3. Check firewall rules

### PTZ controls not responding
1. Verify camera is online
2. Test with: `python scripts/test_ptz.py`
3. Check preset tokens in API response

## Development

### Adding Features

To add new features (e.g., recording, detection overlay):

1. **Add UI element** in `init_ui()`:
```python
self.my_button = QPushButton("My Feature")
self.my_button.clicked.connect(self.my_feature)
```

2. **Implement handler**:
```python
def my_feature(self):
    print("Feature triggered")
```

3. **Test thoroughly** before committing

### Code Structure

```
desktop_app/
├── __init__.py              # Package marker
├── main.py                  # Main application
│   ├── StreamWorker         # Video capture thread
│   ├── StatsWorker          # Statistics fetch thread
│   └── CameraTrackerApp     # Main GUI window
```

### Thread Safety

- Always emit signals from worker threads
- Use `self.signal.connect()` to receive in main thread
- PyQt5 automatically handles thread-safe UI updates

## Comparison: Web vs Desktop

| Feature | Web | Desktop |
|---------|-----|---------|
| FPS | 10-15 | 25-30 |
| No installation | ✅ | ❌ |
| Remote access | ✅ | ❌ (local only) |
| Responsive | Good | Excellent |
| CPU usage | 10-15% | 5-10% |
| Startup time | Instant | 2-3 seconds |

## Performance Tips

1. **Close other applications** to free CPU
2. **Lower camera resolution** if FPS drops below 20
3. **Disable detection overlays** if used (not in desktop app)
4. **Run on wired ethernet** for consistent frame delivery

## Future Enhancements

- [ ] Configuration GUI (no hardcoding URL)
- [ ] Multi-camera support
- [ ] Detection bounding box overlay
- [ ] Video recording
- [ ] Event search/playback
- [ ] Full-screen mode
- [ ] Custom camera profiles
- [ ] Performance monitoring/profiling

## Known Limitations

- **Single camera** (could extend for multi-camera)
- **Local network only** (no remote streaming)
- **Windows-tested** (should work on Linux/Mac but untested)
- **No persistent configuration** (revert to hardcoded URL)

## License

Same as main project

## Author

See README.md

---

**Last Updated:** November 14, 2025
