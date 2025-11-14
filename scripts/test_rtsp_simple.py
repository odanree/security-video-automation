#!/usr/bin/env python3
"""Simple RTSP connection test"""

import cv2
import time

print("Testing different RTSP paths...\n")

urls_to_test = [
    ("Config file path", "rtsp://admin:Windows98@192.168.1.107:554/11"),
    ("Common /stream1", "rtsp://admin:Windows98@192.168.1.107:554/stream1"),
    ("Common /stream0", "rtsp://admin:Windows98@192.168.1.107:554/stream0"),
    ("Dahua /stream/sub", "rtsp://admin:Windows98@192.168.1.107:554/stream/sub"),
    ("Hikvision main stream", "rtsp://admin:Windows98@192.168.1.107:554/Streaming/Channels/101"),
    ("Just IP", "rtsp://admin:Windows98@192.168.1.107"),
]

for name, url in urls_to_test:
    print(f"{name}")
    print(f"  URL: {url}")
    
    cap = cv2.VideoCapture(url)
    
    if not cap.isOpened():
        print(f"  ✗ Failed to open")
    else:
        print(f"  ✓ Opened", end="")
        
        # Try to read a frame
        ret, frame = cap.read()
        if ret:
            print(f" | ✓ Got frame: {frame.shape}")
        else:
            print(f" | ✗ No frame after wait")
            # Try again after delay
            time.sleep(1)
            ret, frame = cap.read()
            if ret:
                print(f"    (Got frame on 2nd try: {frame.shape})")
            else:
                print(f"    (Still no frame)")
    
    cap.release()
    print()

