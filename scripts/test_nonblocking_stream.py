"""Test video stream with non-blocking buffer"""
import requests
import time

print("Starting tracking engine...")
try:
    r = requests.post('http://localhost:8000/api/tracking/start', timeout=2)
    print(f"✓ Tracking started (status: {r.status_code})" if r.status_code == 200 else f"✗ Error: {r.status_code}")
except Exception as e:
    print(f"✗ Error: {e}")

print("\n" + "="*80)
print("VIDEO STREAM TEST - NON-BLOCKING BUFFER")
print("="*80)
print("\nOptimizations applied:")
print("  ✓ Direct frame buffer for web (read_direct())")
print("  ✓ Non-blocking streaming (no contention with tracking)")
print("  ✓ JPEG quality: 15 (balanced)")
print("\nDashboard: http://localhost:8000")
print("\nExpected results:")
print("  ✓ Video plays smoothly WITHOUT freezing")
print("  ✓ PTZ tracking responds immediately")
print("  ✓ No frame drops or stuttering")
print("\nMonitoring for 60 seconds...")
print("-" * 80)

start = time.time()
try:
    while time.time() - start < 60:
        try:
            r = requests.get('http://localhost:8000/api/statistics', timeout=1)
            if r.status_code == 200:
                stats = r.json()
                elapsed = int(time.time() - start)
                print(f"[{elapsed:02d}s] Frames: {stats.get('frames_processed', 0)} | Detections: {stats.get('detections', 0)} | Tracks: {stats.get('tracks', 0)}")
        except:
            pass
        time.sleep(5)
except KeyboardInterrupt:
    pass

print("-" * 80)
print("\n✅ Test complete! Check dashboard for smooth video playback.")
