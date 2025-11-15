#!/usr/bin/env python3
"""Comprehensive diagnostics for bounding box issues"""

import requests
import json
import time
import sys

BACKEND_URL = "http://localhost:8000"

def check_system_status():
    """Check overall system status"""
    print("\n" + "="*70)
    print("SYSTEM STATUS CHECK")
    print("="*70)
    
    try:
        response = requests.get(f"{BACKEND_URL}/api/status", timeout=2)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Backend Status: {data}")
            return True
        else:
            print(f"❌ Backend Status Error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend Unreachable: {e}")
        return False

def check_camera_connection():
    """Check camera connection"""
    print("\n" + "="*70)
    print("CAMERA CONNECTION CHECK")
    print("="*70)
    
    try:
        response = requests.get(f"{BACKEND_URL}/api/camera/status", timeout=2)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Camera Connected: {data}")
            return True
        else:
            print(f"❌ Camera Error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Camera Check Failed: {e}")
        return False

def check_tracking_status():
    """Check tracking status"""
    print("\n" + "="*70)
    print("TRACKING STATUS CHECK")
    print("="*70)
    
    try:
        response = requests.get(f"{BACKEND_URL}/api/tracking/status", timeout=2)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Tracking Status:")
            print(f"   Active: {data.get('active', False)}")
            print(f"   Mode: {data.get('mode', 'unknown')}")
            print(f"   Detections: {data.get('detections', 0)}")
            return data.get('active', False)
        else:
            print(f"❌ Tracking Error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Tracking Check Failed: {e}")
        return False

def check_detections():
    """Check current detections"""
    print("\n" + "="*70)
    print("DETECTION CHECK")
    print("="*70)
    
    try:
        response = requests.get(f"{BACKEND_URL}/api/detections/current", timeout=2)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Detections Retrieved: {len(data)}")
            
            if data:
                print("\n   Detection Details:")
                for i, det in enumerate(data[:5]):  # Show first 5
                    print(f"\n   [{i+1}] {det.get('class')}")
                    print(f"       BBox: {det.get('bbox')}")
                    print(f"       Confidence: {det.get('confidence'):.2f}")
                
                if len(data) > 5:
                    print(f"\n   ... and {len(data) - 5} more")
                
                return True
            else:
                print("⚠️  No detections (tracking may not be active)")
                return False
        else:
            print(f"❌ Detection Error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Detection Check Failed: {e}")
        return False

def start_tracking():
    """Start tracking if not already running"""
    print("\n" + "="*70)
    print("STARTING TRACKING")
    print("="*70)
    
    try:
        response = requests.post(f"{BACKEND_URL}/api/tracking/start", timeout=2)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Tracking Started: {data}")
            return True
        else:
            print(f"❌ Start Error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Start Failed: {e}")
        return False

def run_full_diagnostic():
    """Run complete diagnostic"""
    print("\n\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*15 + "BOUNDING BOX DIAGNOSTIC TOOL" + " "*26 + "║")
    print("╚" + "="*68 + "╝")
    
    # 1. Check backend
    if not check_system_status():
        print("\n❌ Backend is not running. Start it with:")
        print("   python start_dashboard.py")
        sys.exit(1)
    
    # 2. Check camera
    if not check_camera_connection():
        print("\n⚠️  Camera may not be connected")
    
    # 3. Check tracking
    tracking_active = check_tracking_status()
    
    # 4. Start tracking if needed
    if not tracking_active:
        print("\n⚠️  Tracking is not active. Starting...")
        start_tracking()
        time.sleep(2)
        tracking_active = check_tracking_status()
    
    # 5. Check detections
    if tracking_active:
        has_detections = check_detections()
        
        if has_detections:
            print("\n" + "="*70)
            print("✅ EVERYTHING LOOKS GOOD!")
            print("="*70)
            print("\nTo see bounding boxes in the desktop app:")
            print("  1. Click '🔳 Toggle Detection Overlay' button")
            print("  2. Detections should now appear as colored boxes on video")
            print("\nIf you still don't see boxes:")
            print("  - Ensure overlay is ON (button should show 'Overlay: ON' in green)")
            print("  - Make sure there are objects to detect (people, cars, bicycles, etc.)")
            print("  - Check detection confidence is above threshold (0.65)")
        else:
            print("\n" + "="*70)
            print("⚠️  NO DETECTIONS FOUND")
            print("="*70)
            print("\nPossible reasons:")
            print("  1. No objects in camera view")
            print("  2. Objects are too small or far away")
            print("  3. Confidence threshold is too high (0.65)")
            print("  4. AI model not detecting properly")
            print("\nTry:")
            print("  - Move closer to camera")
            print("  - Ensure good lighting")
            print("  - Lower confidence threshold in config/ai_config.yaml")
    else:
        print("\n⚠️  Could not start tracking")
    
    print("\n" + "="*70)
    print("Diagnostic complete!")
    print("="*70 + "\n")

if __name__ == "__main__":
    run_full_diagnostic()
