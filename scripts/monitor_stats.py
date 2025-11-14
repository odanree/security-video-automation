"""Monitor WebSocket statistics to detect flickering pattern"""
import subprocess
import json
import sys
import time

def monitor_websocket():
    """Use curl to monitor WebSocket"""
    # First check if dashboard is running
    try:
        import requests
        response = requests.get("http://localhost:8000/api/status", timeout=2)
        if response.status_code != 200:
            print("❌ Dashboard not responding")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Cannot connect to dashboard: {e}")
        print("Start the dashboard first: taskkill /F /IM python.exe 2>$null; .\\restart_dashboard.ps1")
        sys.exit(1)
    
    print("✓ Dashboard is running")
    print("\nTailing the tracking engine logs to see statistics...")
    print("(Watch for detection_count, tracking_count spikes)")
    print("-" * 80)
    
    # Run the dashboard server in the background and tail logs
    # Since we can't easily monitor WebSocket with curl, let's check API directly
    
    print("\nChecking statistics via API...")
    print("-" * 80)
    print(f"{'Time':>8} | {'Frames':>6} | {'Detections':>10} | {'Tracks':>6} | {'PTZ':>6} | {'Running':>7}")
    print("-" * 80)
    
    try:
        seq = 0
        prev_detections = 0
        
        while True:
            try:
                import requests
                response = requests.get("http://localhost:8000/api/statistics", timeout=2)
                if response.status_code == 200:
                    stats = response.json()
                    seq += 1
                    
                    frames = stats.get('frames_processed', 0)
                    detections = stats.get('detections', 0)
                    tracks = stats.get('tracks', 0)
                    ptz = stats.get('ptz_movements', 0)
                    running = stats.get('is_running', False)
                    
                    # Detect zero spike
                    change_marker = ""
                    if detections == 0 and prev_detections > 0:
                        change_marker = " 🔴 ZERO!"
                    
                    current_time = time.strftime("%H:%M:%S")
                    print(f"{current_time:>8} | {frames:6d} | {detections:10d} | {tracks:6d} | {ptz:6d} | {str(running):>7}{change_marker}")
                    
                    prev_detections = detections
                    time.sleep(0.5)  # Check every 500ms
                
            except requests.exceptions.RequestException:
                print("Lost connection to dashboard")
                break
    
    except KeyboardInterrupt:
        print("\n\nStopped monitoring")

if __name__ == "__main__":
    monitor_websocket()
