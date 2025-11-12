"""
Test different stream URLs to find the correct one for your camera
"""

import cv2
import sys

def test_stream(url: str, timeout: int = 5) -> bool:
    """
    Test if a stream URL works
    
    Args:
        url: Stream URL to test
        timeout: Timeout in seconds
        
    Returns:
        True if stream works
    """
    print(f"\nTesting: {url}")
    print("-" * 60)
    
    try:
        cap = cv2.VideoCapture(url)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        if not cap.isOpened():
            print("❌ Failed to open stream")
            return False
        
        print("✓ Stream opened")
        
        # Try to read a frame
        ret, frame = cap.read()
        
        if not ret or frame is None:
            print("❌ Failed to read frame")
            cap.release()
            return False
        
        print(f"✓ Frame read successfully")
        print(f"  Resolution: {frame.shape[1]}x{frame.shape[0]}")
        print(f"  FPS: {cap.get(cv2.CAP_PROP_FPS)}")
        
        cap.release()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Test common stream URLs"""
    
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_stream_urls.py <camera_ip> [username] [password]")
        print("\nExample:")
        print("  python scripts/test_stream_urls.py 192.168.1.107")
        print("  python scripts/test_stream_urls.py 192.168.1.107 admin admin")
        sys.exit(1)
    
    camera_ip = sys.argv[1]
    username = sys.argv[2] if len(sys.argv) > 2 else "admin"
    password = sys.argv[3] if len(sys.argv) > 3 else "admin"
    
    print("=" * 60)
    print("STREAM URL TESTER")
    print("=" * 60)
    print(f"Camera IP: {camera_ip}")
    print(f"Username: {username}")
    print(f"Password: {password}")
    
    # Common RTSP URL patterns
    rtsp_urls = [
        f"rtsp://{username}:{password}@{camera_ip}:554/live",
        f"rtsp://{username}:{password}@{camera_ip}:554/stream1",
        f"rtsp://{username}:{password}@{camera_ip}:554/stream2",
        f"rtsp://{username}:{password}@{camera_ip}:554/Streaming/Channels/101",
        f"rtsp://{username}:{password}@{camera_ip}:554/Streaming/Channels/1",
        f"rtsp://{username}:{password}@{camera_ip}:554/cam/realmonitor?channel=1&subtype=0",
        f"rtsp://{username}:{password}@{camera_ip}:554/h264",
        f"rtsp://{username}:{password}@{camera_ip}:554/video",
        f"rtsp://{username}:{password}@{camera_ip}:554/",
        f"rtsp://{username}:{password}@{camera_ip}/live",
    ]
    
    # Common HTTP URL patterns
    http_urls = [
        f"http://{camera_ip}:8080/video",
        f"http://{username}:{password}@{camera_ip}:8080/video",
        f"http://{camera_ip}/video.cgi",
        f"http://{username}:{password}@{camera_ip}/video.cgi",
        f"http://{camera_ip}:80/cgi-bin/mjpeg?channel=0&subtype=1",
    ]
    
    working_urls = []
    
    print("\n" + "=" * 60)
    print("TESTING RTSP URLS")
    print("=" * 60)
    
    for url in rtsp_urls:
        if test_stream(url):
            working_urls.append(url)
    
    print("\n" + "=" * 60)
    print("TESTING HTTP URLS")
    print("=" * 60)
    
    for url in http_urls:
        if test_stream(url):
            working_urls.append(url)
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if working_urls:
        print(f"\n✓ Found {len(working_urls)} working URL(s):\n")
        for i, url in enumerate(working_urls, 1):
            print(f"{i}. {url}")
        
        print("\nUpdate your camera_config.yaml with the working URL:")
        print("```yaml")
        print("stream:")
        print(f"  rtsp_url: \"{working_urls[0]}\"")
        print("```")
    else:
        print("\n❌ No working stream URLs found")
        print("\nTroubleshooting:")
        print("1. Verify camera IP is correct")
        print("2. Check username/password")
        print("3. Ensure camera streaming is enabled")
        print("4. Check firewall settings")
        print("5. Try accessing camera web interface")
        print("6. Consult camera manual for correct RTSP path")


if __name__ == "__main__":
    main()
