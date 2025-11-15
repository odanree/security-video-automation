# Bounding Box Detection Fix

**Issue:** Bounding boxes were not appearing on the desktop app overlay after addressing the lagging box issue.

**Root Cause:** Race condition between the detection worker thread and the main tracking loop. The detection worker runs asynchronously (50-100ms per frame), but `last_detections` was being set to an empty list whenever detections weren't ready yet.

## Fix Applied

**File:** `src/automation/tracking_engine.py` (lines 449-459)

**Change:** Modified detection caching logic to persist last non-empty detections:

```python
# OLD CODE (was clearing detections):
self.last_detections = detections

# NEW CODE (keeps last valid detections):
if detections:
    self.last_detections = detections
# If empty, keep the previous detections
```

This ensures the `/api/detections/current` endpoint always returns the most recent valid detections, even when the detection worker is still processing the current frame.

## How to Test

### 1. Start Backend (ALREADY RUNNING)
The backend is currently running. Don't restart it!

### 2. Start Desktop App
In a NEW PowerShell terminal:
```powershell
cd C:\Users\Danh\Desktop\security-video-automation
.\venv\Scripts\python.exe desktop_app/main.py
```

### 3. Enable Detection Overlay
1. Click the **"🔳 Toggle Detection Overlay"** button
2. Status should change from "Overlay: OFF" to "Overlay: ON" (green text)

### 4. Start Tracking
1. Click **"▶️ Start Tracking"** button
2. Wait a few seconds for detections to accumulate

### 5. Verify Bounding Boxes Appear
You should now see:
- ✅ Colored bounding boxes around detected objects
- ✅ Green boxes for persons
- ✅ Blue boxes for cars
- ✅ Orange boxes for bicycles
- ✅ Labels showing class name and confidence

## What Was Changed

### Files Modified:
1. **src/automation/tracking_engine.py**
   - Modified detection caching to persist last valid detections
   - Added debug logging for detection counts

2. **src/utils/config_loader.py**
   - Fixed UTF-8 encoding for YAML files (Windows compatibility)
   - Added quadrant_tracking parameter to config builder

3. **desktop_app/main.py**
   - Added quadrant toggle button and method
   - Overlay drawing code already correct (no changes needed)

## Debug Commands (Use SEPARATE Terminal)

If you want to verify detections are being cached:

```powershell
# In a NEW terminal (not the one running backend):
cd C:\Users\Danh\Desktop\security-video-automation
.\venv\Scripts\python.exe -c "import requests; r = requests.get('http://localhost:8000/api/detections/current'); print('Detections:', len(r.json()))"
```

Expected output: `Detections: X` where X > 0

## Common Issues

### Issue: Overlay shows but no boxes
**Solution:** Make sure tracking is started (click ▶️ button)

### Issue: "Backend offline" message
**Solution:** Backend isn't running. Start it with `.\venv\Scripts\python.exe start_dashboard.py`

### Issue: Boxes appear but lag behind subject
**Solution:** This is expected! The fix maintains last detections, so there's a 50-100ms delay. This is normal for async detection.

## Expected Behavior

- **Detection latency:** 50-100ms (normal for YOLO processing)
- **Frame rate:** 15 FPS (camera output)
- **Box persistence:** Boxes stay visible even between detection frames
- **Overlay toggle:** Works instantly (no server restart needed)

---

**Status:** ✅ Fix applied, backend running
**Next Step:** Test in desktop app with overlay enabled
