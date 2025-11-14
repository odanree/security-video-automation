"""Test persistent stats: start tracking, monitor, then stop"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

print("Testing persistent stats fix...")
print("=" * 80)

# Start tracking
print("\n1️⃣  Starting tracking engine...")
r = requests.post(f"{BASE_URL}/api/tracking/start", timeout=2)
print(f"   Response: {r.json()}")
time.sleep(2)

# Get stats while running
print("\n2️⃣  Checking stats while TRACKING IS RUNNING...")
for i in range(3):
    r = requests.get(f"{BASE_URL}/api/statistics", timeout=2)
    stats = r.json()
    print(f"   Attempt {i+1}: detections={stats.get('detections')}, tracks={stats.get('tracks')}, running={stats.get('is_running')}")
    time.sleep(0.5)

# Stop tracking
print("\n3️⃣  Stopping tracking engine...")
r = requests.post(f"{BASE_URL}/api/tracking/stop", timeout=2)
print(f"   Response: {r.json()}")
time.sleep(1)

# Get stats after stopping - should PERSIST (not reset to 0)
print("\n4️⃣  Checking stats AFTER TRACKING STOPPED (should NOT flicker to 0)...")
for i in range(3):
    r = requests.get(f"{BASE_URL}/api/statistics", timeout=2)
    stats = r.json()
    is_running = stats.get('is_running')
    detections = stats.get('detections')
    tracks = stats.get('tracks')
    
    # Check for flickering
    if is_running:
        marker = " ⚠️  ERROR: Running should be False!"
    elif detections == 0:
        marker = " ⚠️  ERROR: Stats reset to 0!"
    else:
        marker = " ✅ PASS: Stats persisted!"
    
    print(f"   Attempt {i+1}: detections={detections}, tracks={tracks}, running={is_running}{marker}")
    time.sleep(0.5)

print("\n" + "=" * 80)
print("✅ Persistent stats test complete!")
