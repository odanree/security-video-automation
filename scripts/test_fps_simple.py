#!/usr/bin/env python3
"""Test streaming performance - simple frame rate monitor"""

import requests
import time

print("Testing streaming performance (60 seconds)...\n")

start = time.time()
frame_counts = []

for i in range(12):
    try:
        r = requests.get('http://localhost:8000/api/statistics', timeout=2)
        if r.status_code == 200:
            stats = r.json()
            elapsed = time.time() - start
            frames = stats.get('frames_processed', 0)
            frame_counts.append((elapsed, frames))
            
            if i > 0:
                prev_elapsed, prev_frames = frame_counts[i-1]
                fps = (frames - prev_frames) / (elapsed - prev_elapsed) if (elapsed - prev_elapsed) > 0 else 0
                print(f"[{elapsed:6.1f}s] Frames: {frames:6d} | FPS: {fps:5.1f} | Detections: {stats.get('detections', 0):3d} | Tracks: {stats.get('tracks', 0):3d}")
            else:
                print(f"[{elapsed:6.1f}s] Frames: {frames:6d} | FPS:   -- | Detections: {stats.get('detections', 0):3d} | Tracks: {stats.get('tracks', 0):3d}")
    except Exception as e:
        print(f"Error: {e}")
    
    time.sleep(5)

print("\n" + "="*70)
if len(frame_counts) > 1:
    total_time = frame_counts[-1][0]
    total_frames = frame_counts[-1][1]
    avg_fps = total_frames / total_time if total_time > 0 else 0
    print(f"✓ Average FPS: {avg_fps:.1f}")
    print(f"✓ Total Frames: {total_frames}")
    print(f"✓ Test Duration: {total_time:.1f}s")
