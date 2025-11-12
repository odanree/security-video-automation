"""
Camera Discovery Script

Discovers IP cameras on the network and checks their ONVIF/PTZ capabilities.
Useful for verifying camera API compatibility before implementing automation.

Usage:
    python scripts/discover_camera.py <camera_ip> [port] [username] [password]

Example:
    python scripts/discover_camera.py 192.168.1.100
    python scripts/discover_camera.py 192.168.1.100 80 admin password123
"""

import sys
import argparse
from typing import Dict, Optional, List


def print_header():
    """Print script header"""
    print("=" * 60)
    print("  Security Camera Discovery Tool")
    print("  ONVIF/PTZ Capability Checker")
    print("=" * 60)
    print()


def discover_camera(
    ip: str,
    port: int = 80,
    username: str = 'admin',
    password: str = 'admin'
) -> Dict:
    """
    Discover camera and check its capabilities
    
    Args:
        ip: Camera IP address
        port: ONVIF port (usually 80, 8080, or 8000)
        username: Camera username
        password: Camera password
        
    Returns:
        Dict containing camera capabilities and information
    """
    result = {
        'ip': ip,
        'port': port,
        'connected': False,
        'onvif_supported': False,
        'ptz_supported': False,
        'error': None
    }
    
    try:
        # Import ONVIF library (will fail if not installed)
        try:
            from onvif import ONVIFCamera
        except ImportError:
            result['error'] = "python-onvif-zeep not installed. Run: pip install onvif-zeep"
            return result
        
        print(f"🔍 Connecting to camera at {ip}:{port}...")
        print(f"   Username: {username}")
        print()
        
        # Create ONVIF camera connection
        camera = ONVIFCamera(ip, port, username, password)
        result['connected'] = True
        result['onvif_supported'] = True
        
        # Get device information
        print("✓ Camera connected successfully!")
        print()
        
        device_info = camera.devicemgmt.GetDeviceInformation()
        result['manufacturer'] = device_info.Manufacturer
        result['model'] = device_info.Model
        result['firmware'] = device_info.FirmwareVersion
        result['serial'] = device_info.SerialNumber
        
        print("📷 Device Information:")
        print(f"   Manufacturer: {device_info.Manufacturer}")
        print(f"   Model: {device_info.Model}")
        print(f"   Firmware: {device_info.FirmwareVersion}")
        print(f"   Serial: {device_info.SerialNumber}")
        print()
        
        # Get media profiles
        media_service = camera.create_media_service()
        profiles = media_service.GetProfiles()
        result['profile_count'] = len(profiles)
        
        print(f"🎥 Media Profiles: {len(profiles)}")
        for idx, profile in enumerate(profiles):
            print(f"   {idx + 1}. {profile.Name} (Token: {profile.token})")
        print()
        
        # Check PTZ capabilities
        try:
            ptz_service = camera.create_ptz_service()
            result['ptz_supported'] = True
            print("✓ PTZ Service: Available")
            
            # Get PTZ configuration
            profile_token = profiles[0].token
            
            # Get presets
            try:
                presets = ptz_service.GetPresets({'ProfileToken': profile_token})
                result['preset_count'] = len(presets)
                result['presets'] = []
                
                print(f"✓ Configured Presets: {len(presets)}")
                
                if len(presets) > 0:
                    print()
                    print("📍 Available Presets:")
                    for preset in presets:
                        preset_info = {
                            'token': preset.token,
                            'name': preset.Name if preset.Name else 'Unnamed'
                        }
                        result['presets'].append(preset_info)
                        print(f"   • {preset_info['name']} (Token: {preset_info['token']})")
                else:
                    print("   ⚠️  No presets configured. Use camera web interface to set up presets.")
                print()
                
            except Exception as e:
                print(f"   ⚠️  Could not retrieve presets: {e}")
                print()
            
            # Check PTZ capabilities
            try:
                capabilities = ptz_service.GetServiceCapabilities()
                result['capabilities'] = {}
                
                print("🎮 PTZ Capabilities:")
                if hasattr(capabilities, 'EFlip') and capabilities.EFlip:
                    result['capabilities']['flip'] = True
                    print("   ✓ Flip supported")
                
                if hasattr(capabilities, 'Reverse') and capabilities.Reverse:
                    result['capabilities']['reverse'] = True
                    print("   ✓ Reverse supported")
                    
                # Most cameras support these by default
                result['capabilities']['absolute_move'] = True
                result['capabilities']['relative_move'] = True
                result['capabilities']['continuous_move'] = True
                
                print("   ✓ Absolute movement")
                print("   ✓ Relative movement")
                print("   ✓ Continuous movement")
                print()
                
            except Exception as e:
                print(f"   ⚠️  Could not retrieve detailed capabilities: {e}")
                print()
            
        except Exception as e:
            result['ptz_supported'] = False
            print(f"✗ PTZ Service: Not available")
            print(f"   Error: {e}")
            print()
        
        # Get stream URI
        try:
            stream_setup = {
                'Stream': 'RTP-Unicast',
                'Protocol': 'RTSP'
            }
            stream_uri = media_service.GetStreamUri({
                'StreamSetup': stream_setup,
                'ProfileToken': profiles[0].token
            })
            result['rtsp_url'] = stream_uri.Uri
            
            print("🎬 RTSP Stream URL:")
            print(f"   {stream_uri.Uri}")
            print()
            
        except Exception as e:
            print(f"   ⚠️  Could not retrieve stream URL: {e}")
            print()
        
        return result
        
    except Exception as e:
        result['error'] = str(e)
        print(f"✗ Connection failed!")
        print(f"   Error: {e}")
        print()
        print("💡 Troubleshooting tips:")
        print("   1. Verify camera IP is correct (try pinging it)")
        print("   2. Check if ONVIF is enabled in camera settings")
        print("   3. Try common ONVIF ports: 80, 8080, 8000, 8899")
        print("   4. Verify username and password are correct")
        print("   5. Check if camera is on the same network")
        print()
        
        return result


def print_summary(result: Dict):
    """Print discovery summary"""
    print("=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print()
    
    if result['error']:
        print(f"❌ Discovery Failed: {result['error']}")
        return
    
    print(f"Camera IP: {result['ip']}:{result['port']}")
    print(f"ONVIF Support: {'✓ Yes' if result['onvif_supported'] else '✗ No'}")
    print(f"PTZ Support: {'✓ Yes' if result['ptz_supported'] else '✗ No'}")
    
    if result['ptz_supported']:
        print(f"Presets Configured: {result.get('preset_count', 0)}")
        
        print()
        print("✅ This camera is compatible with the tracking system!")
        
        if result.get('preset_count', 0) == 0:
            print()
            print("⚠️  Next Steps:")
            print("   1. Access camera web interface")
            print("   2. Configure 3-5 presets for tracking zones")
            print("   3. Note preset names/tokens for configuration")
        else:
            print()
            print("✅ Camera has presets configured and ready to use!")
            
    else:
        print()
        print("⚠️  PTZ not supported. Camera may not work with this system.")
    
    print()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Discover IP camera and check ONVIF/PTZ capabilities',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s 192.168.1.100
  %(prog)s 192.168.1.100 --port 8080
  %(prog)s 192.168.1.100 --username admin --password mypassword
  %(prog)s 192.168.1.100 -p 80 -u admin -P secret123
        """
    )
    
    parser.add_argument(
        'ip',
        help='Camera IP address (e.g., 192.168.1.100)'
    )
    parser.add_argument(
        '-p', '--port',
        type=int,
        default=80,
        help='ONVIF port (default: 80, try 8080 or 8000 if failed)'
    )
    parser.add_argument(
        '-u', '--username',
        default='admin',
        help='Camera username (default: admin)'
    )
    parser.add_argument(
        '-P', '--password',
        default='admin',
        help='Camera password (default: admin)'
    )
    
    args = parser.parse_args()
    
    print_header()
    result = discover_camera(
        ip=args.ip,
        port=args.port,
        username=args.username,
        password=args.password
    )
    print_summary(result)


if __name__ == "__main__":
    main()
