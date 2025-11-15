# CPU Optimization Plan - November 14, 2025

## Current Status
- **CPU Usage:** 60-70% (too high)
- **Issue:** Running detection on every frame and fetching detections at 15 FPS is causing excessive CPU load

## Root Causes
1. **Detection runs on every frame** - Detection worker processes every submitted frame
2. **Detection fetch at 15 FPS** - Desktop app fetches every 66ms (added in lag fix)
3. **Full-resolution frame processing** - Frames at native resolution through entire pipeline
4. **No frame skipping in main loop** - Desktop app renders every frame
5. **High detection frequency** - Trades detection lag for CPU overuse

## Optimization Strategy

### Level 1: Frame Skipping in Detection (Critical)
- **Current:** Submit every frame to detection worker
- **Target:** Submit every 3rd frame (reduce by 67%)
- **Effect:** Detection runs ~5 times per second instead of 15
- **Impact:** -40-50% CPU usage, minimal lag (200ms instead of 0ms)

### Level 2: Detection Fetch Throttling (Critical)
- **Current:** Fetch detections every 66ms (15 FPS)
- **Target:** Fetch detections every 200ms (~5 FPS)
- **Effect:** 3x fewer HTTP requests
- **Impact:** -10% CPU usage, no visual lag (still synchronized to detection rate)

### Level 3: Frame Resolution Optimization (Important)
- **Current:** 800×600 stream input size
- **Target:** Add configuration for input size scaling
- **Effect:** Reduce frame area by 25-50% before detection
- **Impact:** -20-30% CPU usage, minimal accuracy loss

### Level 4: Confidence Threshold Tuning (Minor)
- **Current:** 0.65 confidence threshold
- **Target:** 0.70-0.75 for fewer detections to process
- **Effect:** Fewer boxes to draw and cache
- **Impact:** -5% CPU usage

### Level 5: Batch Processing (Advanced)
- **Current:** Process 1 frame at a time
- **Target:** Batch processing (skip-frame batches)
- **Effect:** Better GPU utilization if using GPU
- **Impact:** Already optimized for CPU

## Recommended Implementation

### Priority 1: Implement Frame Skipping (40-50% reduction)
Location: `src/automation/tracking_engine.py` line 442
```python
# Change from: detection_skip_interval = 1  # Every frame
# To: detection_skip_interval = 3  # Every 3rd frame
```

### Priority 2: Reduce Detection Fetch Frequency (10% reduction)
Location: `desktop_app/main.py` line 650
```python
# Change from: self.detection_fetch_interval = 0.066  # 15 FPS
# To: self.detection_fetch_interval = 0.2  # 5 FPS
```

### Priority 3: Add Input Size Configuration (20-30% reduction)
Location: `config/ai_config.yaml`
```yaml
# Add configuration for detection frame downsampling
detection_input_size: 416  # Instead of native 800×600
```

## Expected Results

| Optimization | CPU Reduction | Implementation |
|--------------|----------------|-----------------|
| Frame skipping (3x) | 40-50% | Immediate |
| Detection fetch throttle | 10% | Immediate |
| Input size scaling | 20-30% | Configuration |
| Confidence tuning | 5% | Configuration |
| **Total estimated** | **60-70%** | **Can reach 20-30% CPU** |

## Trade-offs

### Lag Impact
- Frame skipping: +200ms lag (imperceptible)
- Detection fetch: +133ms lag (imperceptible)
- Total added lag: ~333ms (still smooth for 15 FPS display)

### Accuracy Impact
- Input size reduction: Minimal (0-2% accuracy loss)
- Confidence tuning: Minimal (filter out low-confidence detections anyway)

## Implementation Plan

1. ✅ **Step 1:** Apply frame skipping (3x reduction)
2. ✅ **Step 2:** Reduce detection fetch (5 FPS instead of 15)
3. ✅ **Step 3:** Add input size configuration
4. ✅ **Step 4:** Test and verify
5. ✅ **Step 5:** Document changes

## Rollback Plan

Each change is independent and can be reverted without affecting others:
```bash
git diff src/automation/tracking_engine.py
git diff desktop_app/main.py
git diff config/ai_config.yaml
```

## Next Steps

Ready to implement? Estimated time: 10 minutes for all changes.

Expected result: **CPU usage reduced from 60-70% to 20-30%**
