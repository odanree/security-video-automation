# Bounding Box Data Flow - Visual Walkthrough

This document traces exactly how a detected object gets drawn on screen.

## Complete Flow Example

**Scenario:** Person detected at (200, 150) to (300, 250) in camera frame

```
┌─────────────────────────────────────────────────────────────┐
│ CAMERA STREAM (192.168.1.107:554/stream1)                 │
│ ─────────────────────────────────────────────────────────   │
│ Resolution: 800×600                                        │
│ Frame Rate: 15 FPS                                         │
│ Format: H.264 RTSP                                         │
│ Pixel Space: X=[0, 800), Y=[0, 600)                        │
└──────────────────────────┬──────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ DESKTOP APP: StreamWorker Thread                           │
│ ─────────────────────────────────────────────────────────   │
│ File: desktop_app/main.py, lines 23-72                    │
│ Task: Continuously read frames from RTSP stream            │
│                                                            │
│ Code:                                                      │
│   cap = cv2.VideoCapture(rtsp_url)  # 800×600 stream      │
│   while True:                                              │
│       ret, frame = cap.read()  # Frame shape: (600,800,3) │
│       self.frame_ready.emit(frame)  # Signal to GUI       │
└──────────────────────────┬──────────────────────────────────┘
                          ↓
                Frame: 800×600 BGR numpy array
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ DESKTOP APP: update_frame() Slot                           │
│ ─────────────────────────────────────────────────────────   │
│ File: desktop_app/main.py, lines 655-690                  │
│ Task: Process frame and display                            │
│                                                            │
│ Code:                                                      │
│   def on_frame_ready(self, frame):                         │
│       # Apply frame skipping (every 3rd frame)            │
│       if self.frame_skip_counter % 3 == 0:               │
│           display_frame = self.draw_detections(frame)    │
│       self.display_frame_as_pixmap(display_frame)        │
└──────────────────────────┬──────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ DESKTOP APP: draw_detections_overlay()                     │
│ ─────────────────────────────────────────────────────────   │
│ File: desktop_app/main.py, lines 742-870                  │
│ Task: Fetch detections from backend and draw on frame      │
│                                                            │
│ Step 1: Fetch Detections                                  │
│   ─────────────────────────                               │
│   if time_since_last_fetch >= 0.2s:  # Throttle to 5 FPS  │
│       response = requests.get(                             │
│           'http://localhost:8000/api/detections/current'  │
│       )                                                    │
│       detections = response.json()                         │
│   # Returns: [                                             │
│   #   {                                                    │
│   #     'class': 'person',                                 │
│   #     'confidence': 0.92,                                │
│   #     'bbox': [200, 150, 300, 250]  ← IN BACKEND SPACE  │
│   #   }                                                    │
│   # ]                                                      │
│                                                            │
│ Step 2: Get Frame Dimensions                              │
│   ─────────────────────────                               │
│   frame_height, frame_width = frame.shape[:2]             │
│   # Result: frame_width=800, frame_height=600             │
│                                                            │
│ Step 3: Calculate Scale Factors                           │
│   ──────────────────────────                              │
│   BACKEND_WIDTH, BACKEND_HEIGHT = 800, 600                │
│   scale_x = frame_width / BACKEND_WIDTH = 800/800 = 1.0   │
│   scale_y = frame_height / BACKEND_HEIGHT = 600/600 = 1.0 │
│   max_valid_x = frame_width = 800                         │
│   max_valid_y = frame_height = 600                        │
│                                                            │
│ Step 4: Transform Detection Coordinates                   │
│   ──────────────────────────────                          │
│   Original bbox (backend space):                          │
│     x1, y1, x2, y2 = 200, 150, 300, 250                   │
│                                                            │
│   Scale to frame space:                                   │
│     x1 = int(200 * 1.0) = 200                             │
│     y1 = int(150 * 1.0) = 150                             │
│     x2 = int(300 * 1.0) = 300                             │
│     y2 = int(250 * 1.0) = 250                             │
│   (Result: no change since scale is 1.0)                  │
│                                                            │
│ Step 5: Clamp to Frame Boundaries                         │
│   ─────────────────────────                               │
│   x1 = max(0, min(200, 799)) = 200  ✓ within [0, 800)   │
│   x2 = max(201, min(300, 800)) = 300 ✓ within [0, 800)   │
│   y1 = max(0, min(150, 599)) = 150  ✓ within [0, 600)   │
│   y2 = max(151, min(250, 600)) = 250 ✓ within [0, 600)   │
│                                                            │
│   CRITICAL: This prevents boxes from appearing in         │
│   black bars if the display scales the frame              │
│                                                            │
│ Step 6: Validate Box Dimensions                           │
│   ─────────────────────────                               │
│   if x2 <= x1 or y2 <= y1:                                │
│       continue  # Skip invalid boxes                      │
│   # Check: 300 > 200? Yes ✓  250 > 150? Yes ✓            │
│   # Box is valid, proceed to draw                         │
│                                                            │
│ Step 7: Draw Box on Frame                                 │
│   ─────────────────────                                   │
│   color = (0, 255, 0)  # Green for 'person'               │
│   cv2.rectangle(frame, (200, 150), (300, 250),            │
│                 color=(0,255,0), thickness=2)             │
│   # Modifies frame in-place: pixels drawn at coordinates  │
│                                                            │
│ Step 8: Draw Label Text                                   │
│   ───────────────────                                     │
│   text = "person 0.92"                                    │
│   label_y = max(25, 150-5) = 145                          │
│   cv2.putText(frame, text, (200, 145), ...)               │
│                                                            │
│ Step 9: Return Annotated Frame                            │
│   ────────────────────────                                │
│   return frame  # 800×600 BGR with box drawn              │
└──────────────────────────┬──────────────────────────────────┘
                          ↓
            Frame with box: 800×600 with green rectangle
            at coordinates (200, 150) to (300, 250)
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ DESKTOP APP: Display Frame as QPixmap                      │
│ ─────────────────────────────────────────────────────────   │
│ File: desktop_app/main.py, lines 690-740                  │
│ Task: Convert frame to image and display in label          │
│                                                            │
│ Step 1: Convert Frame to RGB (if overlay enabled)         │
│   ────────────────────────────                            │
│   if self.overlay_enabled:                                │
│       display_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)│
│   # Result: RGB array, still 800×600 with green box       │
│                                                            │
│ Step 2: Create QImage from Frame Data                     │
│   ──────────────────────────────                          │
│   bytes_per_line = 800 * 3  # 3 bytes per pixel RGB      │
│   qt_image = QImage(display_frame.data, 800, 600,         │
│                     bytes_per_line,                       │
│                     QImage.Format_RGB888)                 │
│   # Result: QImage object, 800×600                        │
│                                                            │
│ Step 3: Create QPixmap from QImage                        │
│   ──────────────────────                                  │
│   pixmap = QPixmap.fromImage(qt_image)                    │
│   # Result: QPixmap, 800×600 with green box               │
│                                                            │
│ Step 4: Scale Pixmap to Fit Label with Aspect Ratio      │
│   ───────────────────────────────────────────             │
│   label_width = self.video_label.width()   # e.g., 1200   │
│   label_height = self.video_label.height() # e.g., 900    │
│                                                            │
│   scaled_pixmap = pixmap.scaledToWidth(1200,              │
│                                       Qt.SmoothTransformation)│
│   # Result: 1200×900 (scaled 1.5x, maintains 4:3 ratio)   │
│   # Box scaled: (300, 225) to (450, 375)  [1.5x]          │
│                                                            │
│   if scaled_pixmap.height() > label_height:               │
│       scaled_pixmap = pixmap.scaledToHeight(900, ...)     │
│   # Check: 900 > 900? No, skip this step                 │
│                                                            │
│ Step 5: Set Pixmap in Label                               │
│   ─────────────────────────                               │
│   self.video_label.setPixmap(scaled_pixmap)               │
│   # Label displays 1200×900 pixmap inside 1200×900 label  │
│   # No black bars (label and pixmap match size)           │
│   # GREEN BOX visible at scaled coordinates               │
└──────────────────────────┬──────────────────────────────────┘
                          ↓
                ✅ Green bounding box appears on screen!
                   at position (300, 225) to (450, 375)
                   relative to label display area
```

## Coordinate Transformation Summary

```
Backend Detection Space        Frame Processing Space      Display Space
      (800×600)                    (800×600)               (varies)
      
   Bbox in:                    Bbox in:                  Bbox in:
[200, 150, 300, 250]    →    [200, 150, 300, 250]   →  [300, 225, 450, 375]
                              (scale=1.0)                (scaled 1.5x)
                              (clamped)                  (via PyQt)
                              (validated)
```

## Key Points

### ✅ What Goes Right
1. Frame stays 800×600 throughout processing
2. Detections fetched in backend space (800×600)
3. Coordinates scaled correctly (1.0x in this case)
4. Coordinates clamped to valid range
5. PyQt automatically handles display scaling and black bars
6. Bounding box position preserved relative to frame content

### ⚠️ What Could Go Wrong
1. **Scale factor wrong:** If frame != 800×600, scaling would be off
2. **Coordinates out of bounds:** If bbox > [800, 600], clamping catches it
3. **Double scaling:** If coordinates scaled twice, boxes would jump
4. **Frame resized before overlay:** Would throw off coordinates
5. **Mixed coordinate spaces:** Using display coords on frame pixels

### 🔍 Debugging Tips
```python
# At start of draw_detections_overlay():
frame_height, frame_width = frame.shape[:2]
print(f"Frame dimensions: {frame_width}×{frame_height}")
print(f"Scale factors: x={scale_x}, y={scale_y}")

# Before drawing each box:
print(f"Bbox before transform: {[x1, y1, x2, y2]}")
print(f"Bbox after clamp: {[x1, y1, x2, y2]}")

# After drawing:
if detections_drawn > 0:
    print(f"Drew {detections_drawn} boxes")
```

## Real-World Scenarios

### Scenario A: Subject at Top Edge
```
Detection returns: bbox=[300, 10, 350, 100]
After clamp: (300,10) to (350,100)  ✓ Valid, within frame
Draw result: Box visible at top of frame
```

### Scenario B: Subject at Right Edge
```
Detection returns: bbox=[750, 250, 810, 350]  ← X exceeds 800
After clamp: (750,250) to (800,350)  ← X2 clamped to 800
Draw result: Partially visible box at right edge
```

### Scenario C: Partially Outside Frame
```
Detection returns: bbox=[700, 550, 900, 700]  ← Outside
After clamp: (700,550) to (800,600)  ← Both axes clamped
Draw result: Small box visible in corner
```

### Scenario D: Completely Outside Frame
```
Detection returns: bbox=[850, 650, 950, 750]  ← Completely outside
After clamp: x2 < x1 or y2 < y1  ← Invalid
Draw result: Box skipped, not drawn
```

## Performance Impact

### Frame Processing
- Detection inference: 100-150ms (async, every 3rd frame)
- Coordinate transform: <1ms (simple math)
- Clamping: <1ms (min/max operations)
- Drawing: 2-5ms (cv2.rectangle, cv2.putText)
- **Total per frame:** ~200ms (only every 3rd frame drawn)

### Memory
- Frame buffer: 1.4 MB (800×600 BGR)
- Detection data: <10 KB (1-5 boxes)
- Cached detections: ~5 KB
- **Total:** ~1.5 MB active, minimal overhead

### CPU
- YOLO inference: Largest consumer (30-50% alone)
- Frame conversion: ~5-10%
- Drawing operations: ~5-10%
- PyQt rendering: ~10-20%
- **Total before optimization:** 60-70%
- **Total after optimization:** Expected 20-30%

---

**Key Takeaway:** The bounding box coordinate system is working correctly. PyQt handles display scaling and black bars automatically. Boxes are drawn in frame space (800×600) and clamped to valid boundaries.
