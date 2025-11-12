"""Generate test image for object detector demo"""
import cv2
import numpy as np

# Create a simple test frame (640x480)
frame = np.ones((480, 640, 3), dtype=np.uint8) * 200

# Add text
cv2.putText(
    frame,
    "No webcam available - Testing detector initialization",
    (50, 240),
    cv2.FONT_HERSHEY_SIMPLEX,
    0.7,
    (50, 50, 50),
    2
)

# Save test image
cv2.imwrite('test_image.jpg', frame)
print("✓ Created test image: test_image.jpg")
