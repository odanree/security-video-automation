import cv2
import time

rtsp_url = "rtsp://admin:Windows98@192.168.1.107:554/11"
cap = cv2.VideoCapture(rtsp_url)

# Set low-latency settings
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
cap.set(cv2.CAP_PROP_FPS, 30)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

if not cap.isOpened():
    print("Failed to open stream")
    exit(1)

print("Testing actual camera FPS...")
fps_samples = []
frame_times = []

for i in range(60):
    start = time.time()
    ret, frame = cap.read()
    elapsed = time.time() - start
    
    frame_times.append(elapsed)
    
    if ret:
        actual_fps = 1.0 / elapsed if elapsed > 0 else 0
        fps_samples.append(actual_fps)
        if i % 10 == 0:
            print(f"Frame {i}: {actual_fps:.1f} FPS (capture took {elapsed*1000:.1f}ms)")
    else:
        print(f"Frame {i}: Failed to read")

cap.release()

avg_fps = sum(fps_samples) / len(fps_samples) if fps_samples else 0
avg_capture_time = sum(frame_times) / len(frame_times) * 1000

print(f"\nCamera actual FPS: {avg_fps:.1f}")
print(f"Average frame capture time: {avg_capture_time:.1f}ms")
print(f"Latency from camera alone: {avg_capture_time:.1f}ms")
