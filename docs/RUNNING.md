# Running the Security Camera AI Tracking System

## Quick Start

### Option 1: Interactive Runner (Easiest)
```bash
python run.py
```

This will present a menu with common options:
1. Run with video display (recommended for testing)
2. Run headless (no video display)
3. Run for 60 seconds
4. Debug mode
5. Detection only (no PTZ)

### Option 2: Direct Execution

**Basic usage:**
```bash
python src/main.py
```

**With video display:**
```bash
python src/main.py --display
```

**Debug mode:**
```bash
python src/main.py --log-level DEBUG --display
```

**Run for specific duration:**
```bash
python src/main.py --display --duration 60
```

**Detection only (no PTZ control):**
```bash
python src/main.py --display --no-ptz
```

## Command-Line Options

```
python src/main.py [OPTIONS]

Options:
  --config-dir DIR       Configuration directory (default: config)
  --display              Display video window with tracking visualization
  --duration SECONDS     Run duration in seconds (default: run indefinitely)
  --log-level LEVEL      Logging level: DEBUG, INFO, WARNING, ERROR (default: INFO)
  --log-file PATH        Log file path (default: logs/tracking.log)
  --no-ptz               Disable PTZ camera control (detection only)
  -h, --help             Show help message
```

## Keyboard Controls (when --display is enabled)

- **`q`** - Quit application
- **`p`** - Pause/resume tracking
- **`s`** - Print statistics to console

## What Happens When You Run

1. **Loads configuration** from `config/` directory
2. **Validates** all settings (cameras, zones, AI model)
3. **Connects to camera** via RTSP stream
4. **Initializes PTZ controller** (ONVIF)
5. **Loads AI model** (YOLOv8)
6. **Starts tracking engine** in background thread
7. **Processes video frames**:
   - Detects objects (person, car, truck, etc.)
   - Tracks movement direction
   - Triggers PTZ presets based on zones
8. **Logs events** to console and file

## Expected Output

```
============================================================
SECURITY CAMERA AI TRACKING SYSTEM
============================================================
Configuration directory: config
Display video: True
Log level: INFO

Loading configuration...
Validating configurations...
✓ All configurations validated successfully

============================================================
CAMERA CONFIGURATION
============================================================

Enabled cameras: 1

  Camera: Front Camera (camera_1)
    IP: 192.168.1.107:8080
    RTSP: rtsp://admin:admin@192.168.1.107:554/live
    ...

Initializing system components...
Initializing PTZ controller...
✓ PTZ controller connected
Initializing video stream...
✓ Video stream started
Initializing AI object detector...
✓ Object detector loaded: models/yolov8n.pt
  Device: cpu
  Confidence threshold: 0.6
...

============================================================
TRACKING SYSTEM STARTED
============================================================
Press 'q' to quit, 'p' to pause/resume, 's' for stats

Tracking Statistics:
  Frames processed: 150
  Total detections: 23
  Total tracks: 15
  PTZ movements: 3
  ...
```

## Logs

Logs are saved to `logs/tracking.log` by default.

View real-time logs:
```bash
# Windows PowerShell
Get-Content logs/tracking.log -Wait

# Linux/Mac
tail -f logs/tracking.log
```

## Troubleshooting

### Camera connection fails
- Check camera IP and credentials in `config/camera_config.yaml`
- Test with `python scripts/discover_camera.py <camera_ip>`
- Verify RTSP URL format

### No video stream
- Ensure RTSP port 554 is accessible
- Try HTTP stream URL if RTSP fails
- Check camera stream settings

### AI model download slow
- Model downloads automatically on first run
- YOLOv8n is ~6MB (fastest)
- Pre-download: `yolo detect predict model=yolov8n.pt`

### No PTZ movements
- Verify presets are configured in camera
- Check preset tokens in `config/camera_config.yaml`
- Run with `--log-level DEBUG` to see detailed PTZ logs
- Test presets: `python scripts/test_ptz.py <camera_ip>`

### High CPU usage
- Increase `process_every_n_frames` in `config/camera_config.yaml`
- Use GPU: Set `device: cuda` in `config/ai_config.yaml`
- Use smaller model: `yolov8n.pt` instead of `yolov8l.pt`

## Performance Tips

1. **Use GPU** if available (20-30x faster):
   ```yaml
   # config/ai_config.yaml
   inference:
     device: "cuda"  # or "mps" for Apple Silicon
   ```

2. **Skip frames** to reduce CPU load:
   ```yaml
   # config/camera_config.yaml
   global:
     process_every_n_frames: 3  # Process every 3rd frame
   ```

3. **Lower resolution**:
   ```yaml
   # config/camera_config.yaml
   stream:
     resolution: [1280, 720]  # Instead of 1920x1080
   ```

4. **Adjust confidence threshold**:
   ```yaml
   # config/tracking_rules.yaml
   detection:
     min_confidence: 0.7  # Higher = fewer false positives, faster
   ```

## Next Steps

- **Configure camera presets**: Use camera web interface to set up zones
- **Tune tracking rules**: Edit `config/tracking_rules.yaml` for your scene
- **Test with real camera**: Point at area with movement
- **Review logs**: Check `logs/tracking.log` for events
- **Build web dashboard**: See Task 13 for web interface

## Examples

### Test with detection only (no camera control)
```bash
python src/main.py --display --no-ptz
```
Good for testing detection accuracy without moving the camera.

### Run for 2 minutes with stats
```bash
python src/main.py --display --duration 120
```
Automatically stops after 2 minutes and shows final statistics.

### Debug mode (see all events)
```bash
python src/main.py --display --log-level DEBUG
```
Shows detailed logs of every detection, track, and PTZ movement.

### Headless server mode
```bash
python src/main.py
```
No video window, runs in background. Stop with Ctrl+C.
