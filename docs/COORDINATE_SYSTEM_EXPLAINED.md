# Bounding Box Coordinate System - Complete Explanation

## Overview

This document explains how bounding box coordinates flow through the entire system, from YOLO detection to display on screen.

## Coordinate Spaces

### 1. **Backend Detection Space (800×600)**
- **Source:** YOLO object detector input
- **Configuration:** `config/ai_config.yaml` → `input_size: 416` (but bboxes returned at frame resolution)
- **Purpose:** Where YOLO processes frames and detects objects
- **Coordinates:** Bounding boxes returned with 800×600 frame reference
- **Range:** X: [0-800], Y: [0-600]

### 2. **Camera Stream Space (800×600)**
- **Source:** RTSP stream from Dahua IP camera (`rtsp://192.168.1.107:554/stream1`)
- **Resolution:** 800×600 (stream/12 preset)
- **Frame Rate:** 15 FPS
- **Aspect Ratio:** 4:3
- **Coordinates:** Same as backend (box coordinates directly map to frame)

### 3. **Frame Processing Space (800×600)**
- **Location:** `desktop_app/main.py` StreamWorker → update_frame()
- **Current Frame:** Received from stream as 800×600
- **Overlay Drawing:** Bounding boxes drawn directly on this frame
- **Scaling Factors:**
  - `scale_x = frame_width / 800 = 800 / 800 = 1.0`
  - `scale_y = frame_height / 600 = 600 / 600 = 1.0`
  - ➜ **No scaling occurs** (frame stays 800×600)

### 4. **Display Space (variable)**
- **Location:** PyQt5 QLabel widget
- **Label Size:** Depends on window size, typically 1200×900 or larger
- **Display Logic:** `pixmap.scaledToWidth()` or `scaledToHeight()`
- **Aspect Ratio:** Preserved (4:3 maintained)
- **Black Bars:** Appear on one axis when label size differs from 4:3 ratio

## Data Flow

```
Camera Stream (800×600)
    ↓
StreamWorker.run() reads frame
    ↓
frame_ready.emit(frame) → update_frame() slot
    ↓
draw_detections_overlay(frame) 
    ├─ Fetch detections from API (800×600 space)
    ├─ Scale: x' = x * 1.0, y' = y * 1.0 (no change)
    ├─ Clamp: x' = clamp(x', 0, 800), y' = clamp(y', 0, 600)
    └─ Draw on 800×600 frame
    ↓
Frame with overlay (800×600)
    ↓
Convert BGR to RGB (if overlay enabled)
    ↓
Create QImage from frame data
    ↓
Create QPixmap from QImage (800×600)
    ↓
PyQt Display Logic:
    ├─ scaledToWidth(label_width) → may be 1200×900
    ├─ Check if height > label_height
    ├─ If yes, scaledToHeight(label_height) → may be different scale
    ├─ Preserve aspect ratio during scaling
    └─ Black bars appear if label not 4:3 ratio
    ↓
Displayed in Label
    └─ Black bars on sides or top/bottom if needed
```

## Coordinate Transformation Example

**Scenario 1: Box at (100, 50) to (200, 150) in YOLO output**

1. **Backend Space:** Box is at (100, 50, 200, 150)
2. **Scale to Frame:** 
   - `x1' = 100 * 1.0 = 100`
   - `y1' = 50 * 1.0 = 50`
   - `x2' = 200 * 1.0 = 200`
   - `y2' = 150 * 1.0 = 150`
3. **Clamp (redundant if already in bounds):**
   - `x1' = clamp(100, 0, 800) = 100` ✓
   - `y1' = clamp(50, 0, 600) = 50` ✓
   - `x2' = clamp(200, 0, 800) = 200` ✓
   - `y2' = clamp(150, 0, 600) = 150` ✓
4. **Draw on Frame:** Box drawn at (100, 50) to (200, 150) on 800×600 frame
5. **Display:**
   - PyQt scales frame to fit label
   - If label is 1200×900: scale factor = 1200/800 = 1.5
   - Box appears at (150, 75) to (300, 225) in display space
   - But this is AUTOMATIC by PyQt - we don't need to adjust

## Black Bars Explanation

### When Do Black Bars Appear?

**Case 1: Label is wider than 4:3 ratio**
```
Label: 1600 × 900 (1.78 ratio)
Frame: 800 × 600 (1.33 ratio)
Scaled to height: 1200 × 900 (fits)
Black bars: (1600 - 1200) / 2 = 200 pixels on each side
```

**Case 2: Label is taller than 4:3 ratio**
```
Label: 800 × 700 (1.14 ratio)
Frame: 800 × 600 (1.33 ratio)
Scaled to width: 800 × 600 (fits)
Black bars: (700 - 600) / 2 = 50 pixels on top/bottom
```

### Why Coordinates Are Still Correct

✓ **Important:** When PyQt scales the QPixmap and adds black bars, the QLabel handles positioning automatically.

The QLabel:
- Displays the scaled pixmap centered within itself
- Black bars appear as part of the label background
- **Coordinates on the frame stay the same** - boxes move proportionally with frame content

### If Boxes Appear in Black Bars (Bug)

**Possible causes:**
1. **Backend detection at wrong resolution:** Check `config/ai_config.yaml` `input_size`
2. **Frame being resized before overlay:** Search for `cv2.resize()` in `desktop_app/main.py`
3. **Coordinate scaling applied twice:** Check for duplicate `* scale_x` operations
4. **Display coordinates mixed with frame coordinates:** Check draw_detections_overlay logic

**How to verify:**
```python
# At start of draw_detections_overlay():
frame_height, frame_width = frame.shape[:2]
print(f"[FRAME SIZE] {frame_width}×{frame_height}")

# After clamping:
if x1 < 0 or x2 > frame_width or y1 < 0 or y2 > frame_height:
    print(f"[WARNING] Box outside bounds: ({x1}, {y1}, {x2}, {y2})")
```

## Current Implementation

### File: `desktop_app/main.py`

**Lines 770-795: Detection Fetching**
- Fetches cached detections from backend API
- Interval: 0.2s (5 FPS, synchronized with detection rate)
- Timeout: 50ms (non-blocking)

**Lines 798-805: Coordinate Scaling**
```python
BACKEND_WIDTH, BACKEND_HEIGHT = 800, 600
scale_x = frame_width / BACKEND_WIDTH   # = 1.0 currently
scale_y = frame_height / BACKEND_HEIGHT  # = 1.0 currently
```

**Lines 807-825: Coordinate Transformation**
```python
# Scale up from backend to frame space
x1 = int(x1 * scale_x)
x2 = int(x2 * scale_x)
y1 = int(y1 * scale_y)
y2 = int(y2 * scale_y)

# Clamp to valid frame boundaries
x1 = max(0, min(x1, max_valid_x - 1))
x2 = max(x1 + 1, min(x2, max_valid_x))
y1 = max(0, min(y1, max_valid_y - 1))
y2 = max(y1 + 1, min(y2, max_valid_y))

# Skip invalid boxes
if x2 <= x1 or y2 <= y1:
    continue
```

**Lines 837-860: Drawing**
- cv2.rectangle() for box outline
- cv2.putText() for label with semi-transparent background
- All coordinates already transformed and clamped

## Performance Implications

**Frame Scaling Cost:**
- Stream: 15 FPS from camera (fixed)
- Detection: 5 FPS (every 3rd frame, async thread)
- Display: ~15 FPS (matching stream)
- Scaling: None on frame (stays 800×600)
- PyQt Scaling: Automatic, minimal cost

**Memory:**
- 800×600 BGR frame: ~1.4 MB
- Frame + detections: ~1.5 MB per frame
- Cached 30-frame buffer: ~45 MB

## Troubleshooting

### Symptom: Boxes lag behind subject
**Solution:** Already fixed! Detection fetch is now 0.2s, stale detections cleared immediately.

### Symptom: Boxes appear in black bars
**Check:**
1. Verify frame size: `print(f"Frame: {frame_width}×{frame_height}")`
2. Verify detection coordinates: `print(f"Detected box: {bbox}")`
3. Verify scaling: `print(f"Scale: {scale_x}, {scale_y}")`
4. Verify clamping: Add `if` statement to log warnings

### Symptom: Boxes disappear at frame edges
**Expected behavior** - Clamping prevents invalid coordinates. If you see boxes getting cut off unexpectedly, check:
1. Are backend detections extending beyond 0-800 / 0-600?
2. Is scaling factor calculated correctly?
3. Are there any image processing steps between detection and display?

## Future Improvements

1. **Display-Space Coordinates:** If UI needs display-space coordinates for analytics, add separate calculation layer
2. **Adaptive Scaling:** If frame size changes, automatically recalculate scale factors
3. **Black Bar Detection:** Add logic to detect label aspect ratio and log black bar presence
4. **Confidence-based Rendering:** Only draw boxes above certain confidence threshold
5. **Tracking History:** Show trails or historical positions of tracked subjects

## Testing Commands

```bash
# Check current frame size being processed
grep -n "print.*Frame Size\|print.*SUCCESS.*Drew" desktop_app/main.py

# Monitor bounding box coordinates live
tail -f logs/desktop_app.log | grep "SUCCESS\|SKIP\|Box"

# Verify detection API is working
curl http://localhost:8000/api/detections/current | jq '.[] | .bbox'
```

## References

- **Config:** `config/ai_config.yaml` - YOLO input size
- **Backend:** `src/automation/tracking_engine.py` - Detection caching
- **Desktop UI:** `desktop_app/main.py` - Overlay drawing
- **PyQt Scaling:** PyQt5 QPixmap.scaledToWidth/Height documentation
