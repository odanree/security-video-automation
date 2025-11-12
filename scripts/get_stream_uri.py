"""
Get RTSP stream URL directly from camera via ONVIF
"""

import sys
from onvif import ONVIFCamera

def get_stream_uri(camera_ip: str, port: int, username: str, password: str):
    """
    Get stream URI directly from camera via ONVIF
    
    Args:
        camera_ip: Camera IP address
        port: ONVIF port
        username: Camera username
        password: Camera password
    """
    try:
        print(f"Connecting to camera at {camera_ip}:{port}...")
        camera = ONVIFCamera(camera_ip, port, username, password)
        
        # Get media service
        media_service = camera.create_media_service()
        
        # Get profiles
        profiles = media_service.GetProfiles()
        
        print(f"\n✓ Found {len(profiles)} media profile(s)\n")
        
        stream_uris = []
        
        for i, profile in enumerate(profiles):
            print(f"Profile {i+1}: {profile.Name}")
            print(f"  Token: {profile.token}")
            
            # Get stream URI
            request = media_service.create_type('GetStreamUri')
            request.ProfileToken = profile.token
            request.StreamSetup = {
                'Stream': 'RTP-Unicast',
                'Transport': {'Protocol': 'RTSP'}
            }
            
            try:
                response = media_service.GetStreamUri(request)
                uri = response.Uri
                
                print(f"  ✓ RTSP URI: {uri}")
                stream_uris.append((profile.Name, uri))
                
                # Also get snapshot URI if available
                try:
                    snapshot_request = media_service.create_type('GetSnapshotUri')
                    snapshot_request.ProfileToken = profile.token
                    snapshot_response = media_service.GetSnapshotUri(snapshot_request)
                    print(f"  Snapshot URI: {snapshot_response.Uri}")
                except:
                    pass
                    
            except Exception as e:
                print(f"  ✗ Failed to get stream URI: {e}")
            
            print()
        
        # Summary
        if stream_uris:
            print("=" * 60)
            print("RECOMMENDED CONFIGURATION")
            print("=" * 60)
            print("\nUpdate your config/camera_config.yaml:\n")
            print("```yaml")
            print("stream:")
            
            # Use first stream URI
            main_uri = stream_uris[0][1]
            # Replace IP if it's 0.0.0.0 or different
            if '0.0.0.0' in main_uri:
                main_uri = main_uri.replace('0.0.0.0', camera_ip)
            
            print(f'  rtsp_url: "{main_uri}"')
            print("```")
            
            if len(stream_uris) > 1:
                print("\nAlternative streams:")
                for name, uri in stream_uris[1:]:
                    if '0.0.0.0' in uri:
                        uri = uri.replace('0.0.0.0', camera_ip)
                    print(f"  # {name}: {uri}")
        
        return stream_uris
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return []


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/get_stream_uri.py <camera_ip> [port] [username] [password]")
        print("\nExample:")
        print("  python scripts/get_stream_uri.py 192.168.1.107")
        print("  python scripts/get_stream_uri.py 192.168.1.107 8080 admin Windows98")
        sys.exit(1)
    
    camera_ip = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8080
    username = sys.argv[3] if len(sys.argv) > 3 else "admin"
    password = sys.argv[4] if len(sys.argv) > 4 else "Windows98"
    
    print("=" * 60)
    print("ONVIF STREAM URI RETRIEVAL")
    print("=" * 60)
    print(f"Camera IP: {camera_ip}")
    print(f"Port: {port}")
    print(f"Username: {username}")
    print()
    
    stream_uris = get_stream_uri(camera_ip, port, username, password)
    
    if not stream_uris:
        print("\n❌ No stream URIs found")
        print("\nTroubleshooting:")
        print("1. Verify ONVIF is enabled on camera")
        print("2. Check credentials are correct")
        print("3. Ensure port is correct (try 80, 8080, 8000)")
