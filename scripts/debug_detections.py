#!/usr/bin/env python3
"""Debug script to check detection state"""

import requests
import time

BACKEND_URL = "http://localhost:8000"

print("Checking detection details...\n")

# 1. Check tracking status
print("1. Tracking Status:")
r = requests.get(f"{BACKEND_URL}/api/tracking/status")
status = r.json()
print(f"   Running: {status['running']}")
print(f"   Detection Count (total): {status['detections']}")
print()

# 2. Check current detections (what desktop app uses)
print("2. Current Detections (for overlay):")
r = requests.get(f"{BACKEND_URL}/api/detections/current")
current_dets = r.json()
print(f"   Count: {len(current_dets)}")
if current_dets:
    for i, det in enumerate(current_dets[:3]):
        print(f"   [{i+1}] {det['class']} - confidence: {det['confidence']:.2f}, bbox: {det['bbox']}")
else:
    print("   ⚠️  EMPTY - This is the problem!")
print()

# 3. Check frame stats
print("3. Stream Stats:")
r = requests.get(f"{BACKEND_URL}/api/status")
data = r.json()
stats = data.get('stream_stats', {})
print(f"   FPS: {stats.get('fps', 'N/A'):.1f}")
print(f"   Frames Received: {stats.get('frames_received', 0)}")
print(f"   Frames Dropped: {stats.get('frames_dropped', 0)}")
print()

# 4. Monitor for changes
print("4. Monitoring detections over 5 seconds...")
for i in range(5):
    r = requests.get(f"{BACKEND_URL}/api/detections/current")
    det_count = len(r.json())
    r2 = requests.get(f"{BACKEND_URL}/api/tracking/status")
    total = r2.json()['detections']
    print(f"   [{i+1}s] Current: {det_count}, Total: {total}")
    time.sleep(1)

print()
print("Summary:")
print("- If 'Current' is always 0 but 'Total' grows: last_detections not being set")
print("- If 'Current' shows values: Overlay should work!")
print("- If FPS is low: May have frame processing issues")
