import cv2
import time

url = 'rtsp://admin:Windows98@192.168.1.107:554/12'
print(f'Measuring actual FPS from: {url}')

cap = cv2.VideoCapture(url)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

if not cap.isOpened():
    print('Failed to open stream')
    exit(1)

print('Waiting for connection...')
time.sleep(2)

# Measure FPS over 10 seconds
frame_count = 0
start_time = time.time()
last_print = start_time

print('\nMeasuring FPS for 10 seconds...\n')

while True:
    ret, frame = cap.read()
    
    if not ret:
        print('Frame read failed')
        break
    
    frame_count += 1
    current_time = time.time()
    elapsed = current_time - start_time
    
    # Print FPS every second
    if current_time - last_print >= 1.0:
        fps = frame_count / elapsed
        print(f'  {elapsed:.1f}s: {frame_count} frames = {fps:.2f} FPS')
        last_print = current_time
    
    # Stop after 10 seconds
    if elapsed >= 10:
        break

cap.release()

total_time = time.time() - start_time
final_fps = frame_count / total_time

print(f'\n=== FINAL RESULT ===')
print(f'Total frames: {frame_count}')
print(f'Total time: {total_time:.2f}s')
print(f'Average FPS: {final_fps:.2f}')

if final_fps < 20:
    print('\n⚠️  Camera stream is locked to ~15 FPS')
    print('The camera hardware is limiting the second stream')
elif final_fps >= 25:
    print('\n✓ Camera can deliver 25-30 FPS!')
    print('The bottleneck is in the desktop app display')
