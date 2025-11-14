#!/usr/bin/env python3
"""Profile where time is spent in the streaming pipeline

Measures:
1. Frame arrival rate from camera
2. JPEG encoding time
3. Web server delivery time
"""

import requests
import time
import cv2
from collections import deque

def profile_stream():
    """Monitor stream and measure timing"""
    url = "http://localhost:8000/api/video/stream"
    
    print("================================================================================")
    print("STREAM TIMING PROFILE")
    print("================================================================================")
    print(f"\nConnecting to: {url}")
    print("Monitoring 30 seconds...\n")
    
    times = deque(maxlen=100)  # Last 100 frame times
    frame_count = 0
    start_time = time.time()
    last_sample_time = start_time
    
    response = None
    try:
        response = requests.get(url, stream=True, timeout=5)
        
        if response.status_code != 200:
            print(f"✗ Failed: {response.status_code}")
            return
        
        print("✓ Connected to stream")
        print("\nWaiting for frames...\n")
        
        boundary = b'--frame'
        last_chunk_time = time.time()
        buffer = b''
        chunk_count = 0
        
        for chunk in response.iter_content(chunk_size=4096):
            current_time = time.time()
            chunk_count += 1
            
            if chunk:
                buffer += chunk
                
                # Look for frame boundary
                if boundary in buffer:
                    start_idx = buffer.find(boundary)
                    if start_idx >= 0:
                        # Found start of frame
                        frame_count += 1
                        frame_time = current_time
                        times.append(frame_time)
                        
                        # Print every ~5 seconds
                        if current_time - last_sample_time >= 5:
                            elapsed = current_time - start_time
                            
                            if len(times) > 1:
                                # Calculate frame rate from last 100 frames
                                time_span = times[-1] - times[0]
                                if time_span > 0:
                                    fps = len(times) / time_span
                                    interval = (times[-1] - times[-2]) * 1000  # ms
                                    
                                    print(f"[{elapsed:03.0f}s] {frame_count} frames | "
                                          f"{fps:.1f} FPS | "
                                          f"Interval: {interval:.1f}ms | "
                                          f"Chunks/frame: {chunk_count:.0f}")
                                    chunk_count = 0
                            
                            last_sample_time = current_time
                        
                        # Check timeout
                        if current_time - start_time > 35:
                            break
    
    except requests.exceptions.RequestException as e:
        print(f"✗ Connection error: {e}")
        return
    
    finally:
        if response is not None:
            response.close()
    
    # Final report
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)
    
    total_time = time.time() - start_time
    if len(times) > 1:
        time_span = times[-1] - times[0]
        if time_span > 0:
            fps = len(times) / time_span
            avg_interval_ms = (time_span * 1000) / len(times)
            
            print(f"\nTotal frames received: {frame_count}")
            print(f"Time window: {total_time:.1f}s")
            print(f"Measured FPS: {fps:.1f}")
            print(f"Avg frame interval: {avg_interval_ms:.1f}ms")
            print(f"\n✓ Stream is flowing at ~{fps:.1f} FPS")
            
            if fps < 15:
                print("\n⚠️  Throughput is limited to ~10 FPS")
                print("   Possible causes:")
                print("   1. Camera is not sending 30 FPS (limited at source)")
                print("   2. Detection thread is consuming frames slower than stream")
                print("   3. Frame buffer update rate is throttled")
                print("   4. Web server frame generation is rate-limited")
            else:
                print("\n✓ Good throughput, likely detection pipeline bottleneck")

if __name__ == "__main__":
    profile_stream()
