"""Monitor WebSocket statistics to detect flickering pattern"""
import asyncio
import websockets
import json
import sys

async def monitor_websocket():
    """Connect to WebSocket and log statistics"""
    uri = "ws://localhost:8000/ws/updates"
    
    print(f"Connecting to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✓ Connected to WebSocket")
            print("\nMonitoring statistics (Ctrl+C to stop)...")
            print("-" * 80)
            print(f"{'Seq':>3} | {'Frames':>6} | {'Detections':>10} | {'Tracks':>6} | {'PTZ Mvmt':>8} | {'Running':>7} | {'Mode':>10}")
            print("-" * 80)
            
            seq = 0
            prev_stats = None
            
            while True:
                message = await websocket.recv()
                stats = json.loads(message)
                
                seq += 1
                frames = stats.get('frames_processed', 0)
                detections = stats.get('detections', 0)
                tracks = stats.get('tracks', 0)
                ptz_mvmt = stats.get('ptz_movements', 0)
                running = stats.get('is_running', False)
                mode = stats.get('mode', 'unknown')
                
                # Detect changes
                change_marker = ""
                if prev_stats:
                    if (detections, tracks, ptz_mvmt) != (prev_stats['detections'], prev_stats['tracks'], prev_stats['ptz_movements']):
                        change_marker = " ⬆️"
                    if detections == 0 and prev_stats['detections'] > 0:
                        change_marker = " 🔴 ZERO SPIKE!"
                
                print(f"{seq:3d} | {frames:6d} | {detections:10d} | {tracks:6d} | {ptz_mvmt:8d} | {str(running):>7} | {mode:>10}{change_marker}")
                
                prev_stats = stats
                
    except KeyboardInterrupt:
        print("\n\nStopped monitoring")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(monitor_websocket())
