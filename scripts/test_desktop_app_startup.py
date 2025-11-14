#!/usr/bin/env python3
"""Test desktop app - check if it can start and connect"""

import sys
import subprocess
import time
import requests

def test_backend():
    """Check if backend is running"""
    try:
        r = requests.get('http://localhost:8000/api/status', timeout=2)
        if r.status_code == 200:
            print("✓ Backend is running")
            return True
    except:
        pass
    print("✗ Backend not running. Start it first: .\restart_dashboard.ps1")
    return False

def test_imports():
    """Test if PyQt5 and dependencies import correctly"""
    try:
        import PyQt5
        print("✓ PyQt5 installed")
    except ImportError:
        print("✗ PyQt5 not installed")
        return False
    
    try:
        import cv2
        print("✓ OpenCV installed")
    except ImportError:
        print("✗ OpenCV not installed")
        return False
    
    try:
        import requests
        print("✓ Requests installed")
    except ImportError:
        print("✗ Requests not installed")
        return False
    
    return True

if __name__ == "__main__":
    print("="*60)
    print("DESKTOP APP STARTUP TEST")
    print("="*60)
    print()
    
    print("Checking dependencies...")
    if not test_imports():
        print("\n✗ Dependencies missing. Install with: pip install -r requirements.txt")
        sys.exit(1)
    
    print()
    print("Checking backend...")
    if not test_backend():
        sys.exit(1)
    
    print()
    print("="*60)
    print("✓ All checks passed!")
    print("="*60)
    print()
    print("To run the desktop app:")
    print("  python desktop_app/main.py")
    print()
    print("Notes:")
    print("  - Make sure FastAPI backend is running (restart_dashboard.ps1)")
    print("  - Camera RTSP URL is configured in desktop_app/main.py")
    print("  - Close window to exit")
