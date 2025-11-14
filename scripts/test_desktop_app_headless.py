#!/usr/bin/env python3
"""Test desktop app in headless mode (no display)"""

import sys
import cv2
import time
import requests
from threading import Thread

# Simulate what the desktop app does
class HeadlessTest:
    def __init__(self, camera_rtsp: str, backend_url: str = "http://localhost:8000"):
        self.camera_rtsp = camera_rtsp
        self.backend_url = backend_url
        self.running = True
        self.frame_count = 0
        self.frame_times = []
        
    def test_stream_decode(self):
        """Test H.264 RTSP stream decoding"""
        print("\n1. Testing H.264 stream decoding...")
        
        cap = cv2.VideoCapture(self.camera_rtsp)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimal buffer
        
        if not cap.isOpened():
            print(f"✗ Failed to open stream: {self.camera_rtsp}")
            return False
        
        print("✓ Stream opened")
        
        # Grab 10 frames (RTSP may need a moment to start)
        start_time = time.time()
        frames_read = 0
        
        for i in range(10):
            ret, frame = cap.read()
            if ret:
                current_time = time.time()
                self.frame_times.append(current_time)
                self.frame_count += 1
                frames_read += 1
            else:
                # Try a few more times with delay
                time.sleep(0.5)
                ret, frame = cap.read()
                if ret:
                    frames_read += 1
                    self.frame_count += 1
        
        elapsed = time.time() - start_time
        cap.release()
        
        if frames_read == 0:
            print(f"✗ No frames read after {elapsed:.1f}s")
            return False
        
        # Calculate FPS if we got frames
        if len(self.frame_times) > 1:
            time_span = self.frame_times[-1] - self.frame_times[0]
            if time_span > 0:
                fps = len(self.frame_times) / time_span
                print(f"✓ Decoded {frames_read} frames in {elapsed:.2f}s")
                print(f"✓ Stream FPS: {fps:.1f}")
                return True
        
        print(f"✓ Successfully opened and read {frames_read} frames")
        return True
    
    def test_backend_connection(self):
        """Test connection to backend"""
        print("\n2. Testing backend connection...")
        
        try:
            # Test statistics endpoint
            r = requests.get(f"{self.backend_url}/api/statistics", timeout=2)
            if r.status_code == 200:
                stats = r.json()
                print(f"✓ Backend responding")
                print(f"  - Frames processed: {stats.get('frames_processed', 'N/A')}")
                print(f"  - Detections: {stats.get('detections', 'N/A')}")
                print(f"  - Tracking active: {stats.get('tracking_active', False)}")
                return True
        except Exception as e:
            print(f"✗ Backend connection failed: {e}")
        
        return False
    
    def test_presets(self):
        """Test camera presets"""
        print("\n3. Testing camera presets...")
        
        try:
            r = requests.get(f"{self.backend_url}/api/camera/presets", timeout=2)
            if r.status_code == 200:
                presets = r.json()  # Returns list directly
                print(f"✓ Got {len(presets)} presets")
                for preset in presets[:5]:
                    print(f"  - {preset['name']} (token: {preset['token']})")
                return True
        except Exception as e:
            print(f"✗ Failed to get presets: {e}")
        
        return False
    
    def test_tracking_control(self):
        """Test tracking start/stop"""
        print("\n4. Testing tracking control...")
        
        try:
            # Check current status
            r = requests.get(f"{self.backend_url}/api/tracking/status", timeout=2)
            if r.status_code == 200:
                status = r.json()
                print(f"✓ Current tracking status: {status.get('tracking_active')}")
                
                # This is just checking communication, not full start/stop cycle
                # (would interfere with actual running tracking)
                return True
        except Exception as e:
            print(f"✗ Tracking control failed: {e}")
        
        return False
    
    def run_all_tests(self):
        """Run all tests"""
        print("="*60)
        print("DESKTOP APP - HEADLESS INTEGRATION TEST")
        print("="*60)
        
        tests = [
            ("Stream Decoding", self.test_stream_decode),
            ("Backend Connection", self.test_backend_connection),
            ("Camera Presets", self.test_presets),
            ("Tracking Control", self.test_tracking_control),
        ]
        
        results = {}
        for name, test_func in tests:
            try:
                results[name] = test_func()
            except Exception as e:
                print(f"\n✗ Exception in {name}: {e}")
                results[name] = False
        
        # Summary
        print("\n" + "="*60)
        print("RESULTS")
        print("="*60)
        
        passed = sum(1 for v in results.values() if v)
        total = len(results)
        
        for name, passed_flag in results.items():
            status = "✓" if passed_flag else "✗"
            print(f"{status} {name}")
        
        print(f"\n{passed}/{total} tests passed")
        
        if passed == total:
            print("\n✓ All tests passed! Desktop app is ready to use.")
            print("\nTo launch GUI:")
            print("  python desktop_app/main.py")
            return True
        else:
            print("\n✗ Some tests failed. Check errors above.")
            return False

if __name__ == "__main__":
    camera_rtsp = "rtsp://admin:Windows98@192.168.1.107:554/11"
    backend_url = "http://localhost:8000"
    
    test = HeadlessTest(camera_rtsp, backend_url)
    success = test.run_all_tests()
    
    sys.exit(0 if success else 1)
