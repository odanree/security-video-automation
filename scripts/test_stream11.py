import cv2
import time

url = 'rtsp://admin:Windows98@192.168.1.107:554/11'
print(f'Testing main stream: {url}')

cap = cv2.VideoCapture(url)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

print(f'Stream opened: {cap.isOpened()}')

if cap.isOpened():
    print('Waiting 2 seconds for connection...')
    time.sleep(2)
    
    for i in range(5):
        ret, frame = cap.read()
        if ret:
            print(f'✓ Frame {i+1}: {frame.shape}')
        else:
            print(f'✗ Frame {i+1}: Failed to read')
        time.sleep(0.3)
else:
    print('ERROR: Failed to open stream')
    
cap.release()
print('\nDone')
