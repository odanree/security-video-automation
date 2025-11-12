"""
PTZ Test Script

Test PTZ camera movements and presets using the PTZController.
Useful for verifying camera connectivity and preset configuration.

Usage:
    python scripts/test_ptz.py <camera_ip> <username> <password> [options]

Examples:
    # Test all features
    python scripts/test_ptz.py 192.168.1.100 admin password123
    
    # Test only presets
    python scripts/test_ptz.py 192.168.1.100 admin password123 --presets-only
    
    # Test continuous movement
    python scripts/test_ptz.py 192.168.1.100 admin password123 --continuous-only
    
    # Test specific preset tokens
    python scripts/test_ptz.py 192.168.1.100 admin password123 --preset-tokens 1,2,3
"""

import sys
import time
import argparse
from typing import List

# Add parent directory to path to import src modules
sys.path.insert(0, '.')

from src.camera.ptz_controller import PTZController


def print_header():
    """Print script header"""
    print("=" * 60)
    print("  PTZ Camera Test Script")
    print("  Testing Camera Movement & Presets")
    print("=" * 60)
    print()


def test_connection(ptz: PTZController) -> bool:
    """Test basic camera connection"""
    print("🔌 Testing Connection...")
    try:
        status = ptz.get_status()
        if status:
            print("✓ Camera connected successfully")
            print(f"  Current position: pan={status['position']['pan']:.2f}, "
                  f"tilt={status['position']['tilt']:.2f}, "
                  f"zoom={status['position']['zoom']:.2f}")
            print()
            return True
        else:
            print("✗ Failed to get camera status")
            print()
            return False
    except Exception as e:
        print(f"✗ Connection test failed: {e}")
        print()
        return False


def test_presets(ptz: PTZController, preset_tokens: List[str] = None) -> bool:
    """
    Test moving between camera presets
    
    Args:
        ptz: PTZ controller instance
        preset_tokens: List of preset tokens to test (None = test all)
    """
    print("📍 Testing Preset Movements...")
    print()
    
    # Get available presets
    presets = ptz.get_presets()
    
    if not presets:
        print("⚠️  No presets found on camera")
        print("   Please configure presets using camera web interface")
        print()
        return False
    
    print(f"Found {len(presets)} preset(s):")
    for preset in presets:
        print(f"  • {preset.name} (Token: {preset.token})")
    print()
    
    # Filter presets if specific tokens provided
    if preset_tokens:
        presets = [p for p in presets if p.token in preset_tokens]
        if not presets:
            print(f"⚠️  None of the specified tokens {preset_tokens} were found")
            print()
            return False
    
    # Test each preset
    print("Testing preset movements...")
    print()
    
    for idx, preset in enumerate(presets, 1):
        print(f"[{idx}/{len(presets)}] Moving to preset: {preset.name} (Token: {preset.token})")
        
        success = ptz.goto_preset(preset.token, speed=0.5)
        
        if success:
            print(f"  ✓ Command sent successfully")
            print(f"  ⏳ Waiting 3 seconds for camera to reach position...")
            time.sleep(3)
            
            # Get current position
            position = ptz.get_position()
            if position:
                print(f"  📍 Current position: pan={position.pan:.2f}, "
                      f"tilt={position.tilt:.2f}, zoom={position.zoom:.2f}")
        else:
            print(f"  ✗ Failed to move to preset")
        
        print()
    
    print("✓ Preset test complete")
    print()
    return True


def test_continuous_move(ptz: PTZController) -> bool:
    """Test continuous pan/tilt movements"""
    print("🎮 Testing Continuous Movement...")
    print()
    
    movements = [
        ("Pan right", 0.5, 0.0, 2.0),
        ("Pan left", -0.5, 0.0, 2.0),
        ("Tilt up", 0.0, 0.3, 2.0),
        ("Tilt down", 0.0, -0.3, 2.0),
        ("Pan right + Tilt up", 0.3, 0.3, 2.0),
    ]
    
    for idx, (description, pan_vel, tilt_vel, duration) in enumerate(movements, 1):
        print(f"[{idx}/{len(movements)}] {description}")
        print(f"  Velocity: pan={pan_vel}, tilt={tilt_vel}")
        print(f"  Duration: {duration}s")
        
        success = ptz.continuous_move(
            pan_velocity=pan_vel,
            tilt_velocity=tilt_vel,
            duration=duration
        )
        
        if success:
            print(f"  ✓ Movement completed")
        else:
            print(f"  ✗ Movement failed")
        
        print(f"  ⏳ Waiting 1 second before next movement...")
        time.sleep(1)
        print()
    
    print("✓ Continuous movement test complete")
    print()
    return True


def test_absolute_move(ptz: PTZController) -> bool:
    """Test absolute positioning"""
    print("🎯 Testing Absolute Positioning...")
    print()
    
    positions = [
        ("Center", 0.0, 0.0, 0.0),
        ("Right", 0.5, 0.0, 0.0),
        ("Left", -0.5, 0.0, 0.0),
        ("Up", 0.0, 0.3, 0.0),
        ("Down", 0.0, -0.3, 0.0),
    ]
    
    for idx, (description, pan, tilt, zoom) in enumerate(positions, 1):
        print(f"[{idx}/{len(positions)}] Moving to: {description}")
        print(f"  Target: pan={pan}, tilt={tilt}, zoom={zoom}")
        
        success = ptz.absolute_move(pan=pan, tilt=tilt, zoom=zoom, speed=0.7)
        
        if success:
            print(f"  ✓ Command sent successfully")
            time.sleep(2)
            
            position = ptz.get_position()
            if position:
                print(f"  📍 Actual position: pan={position.pan:.2f}, "
                      f"tilt={position.tilt:.2f}, zoom={position.zoom:.2f}")
        else:
            print(f"  ✗ Movement failed")
        
        print()
    
    print("✓ Absolute positioning test complete")
    print()
    return True


def test_home_position(ptz: PTZController) -> bool:
    """Test home position (if supported)"""
    print("🏠 Testing Home Position...")
    
    success = ptz.home()
    
    if success:
        print("✓ Moved to home position")
        time.sleep(2)
    else:
        print("⚠️  Home position not supported or failed")
    
    print()
    return success


def test_stop_command(ptz: PTZController) -> bool:
    """Test stop command during movement"""
    print("🛑 Testing Stop Command...")
    print()
    
    print("Starting continuous movement...")
    ptz.continuous_move(pan_velocity=0.3, tilt_velocity=0.0, duration=5.0)
    
    print("⏳ Waiting 2 seconds...")
    time.sleep(2)
    
    print("Sending stop command...")
    success = ptz.stop()
    
    if success:
        print("✓ Stop command successful")
    else:
        print("✗ Stop command failed")
    
    print()
    return success


def print_summary(results: dict):
    """Print test summary"""
    print("=" * 60)
    print("  TEST SUMMARY")
    print("=" * 60)
    print()
    
    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)
    
    for test_name, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status:12} - {test_name}")
    
    print()
    print(f"Total: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print()
        print("✅ All tests passed! Camera is working correctly.")
    elif passed_tests > 0:
        print()
        print("⚠️  Some tests failed. Check camera configuration.")
    else:
        print()
        print("❌ All tests failed. Check camera connection and credentials.")
    
    print()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Test PTZ camera movements and presets',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s 192.168.1.100 admin password123
  %(prog)s 192.168.1.100 admin password123 --presets-only
  %(prog)s 192.168.1.100 admin password123 --preset-tokens 1,2,3
  %(prog)s 192.168.1.100 admin password123 --skip-continuous
        """
    )
    
    parser.add_argument(
        'ip',
        help='Camera IP address'
    )
    parser.add_argument(
        'username',
        help='Camera username'
    )
    parser.add_argument(
        'password',
        help='Camera password'
    )
    parser.add_argument(
        '-p', '--port',
        type=int,
        default=80,
        help='ONVIF port (default: 80)'
    )
    parser.add_argument(
        '--presets-only',
        action='store_true',
        help='Test only preset movements'
    )
    parser.add_argument(
        '--continuous-only',
        action='store_true',
        help='Test only continuous movements'
    )
    parser.add_argument(
        '--absolute-only',
        action='store_true',
        help='Test only absolute positioning'
    )
    parser.add_argument(
        '--preset-tokens',
        type=str,
        help='Comma-separated list of preset tokens to test (e.g., "1,2,3")'
    )
    parser.add_argument(
        '--skip-continuous',
        action='store_true',
        help='Skip continuous movement tests'
    )
    parser.add_argument(
        '--skip-absolute',
        action='store_true',
        help='Skip absolute positioning tests'
    )
    parser.add_argument(
        '--skip-home',
        action='store_true',
        help='Skip home position test'
    )
    
    args = parser.parse_args()
    
    # Parse preset tokens if provided
    preset_tokens = None
    if args.preset_tokens:
        preset_tokens = [token.strip() for token in args.preset_tokens.split(',')]
    
    print_header()
    
    # Initialize PTZ controller
    print(f"🔌 Connecting to camera at {args.ip}:{args.port}...")
    print(f"   Username: {args.username}")
    print()
    
    try:
        ptz = PTZController(
            camera_ip=args.ip,
            username=args.username,
            password=args.password,
            port=args.port
        )
    except Exception as e:
        print(f"❌ Failed to connect to camera: {e}")
        print()
        print("💡 Troubleshooting:")
        print("   1. Verify camera IP and credentials")
        print("   2. Check if ONVIF is enabled on camera")
        print("   3. Try different ports (80, 8080, 8000)")
        print("   4. Run discover_camera.py first to verify connectivity")
        print()
        sys.exit(1)
    
    print()
    
    # Run tests
    results = {}
    
    # Connection test (always run)
    results['Connection'] = test_connection(ptz)
    
    if not results['Connection']:
        print("❌ Connection test failed. Aborting remaining tests.")
        sys.exit(1)
    
    # Determine which tests to run
    if args.presets_only:
        results['Presets'] = test_presets(ptz, preset_tokens)
    elif args.continuous_only:
        results['Continuous Movement'] = test_continuous_move(ptz)
    elif args.absolute_only:
        results['Absolute Positioning'] = test_absolute_move(ptz)
    else:
        # Run all applicable tests
        results['Presets'] = test_presets(ptz, preset_tokens)
        
        if not args.skip_continuous:
            results['Continuous Movement'] = test_continuous_move(ptz)
        
        if not args.skip_absolute:
            results['Absolute Positioning'] = test_absolute_move(ptz)
        
        if not args.skip_home:
            results['Home Position'] = test_home_position(ptz)
        
        results['Stop Command'] = test_stop_command(ptz)
    
    # Print summary
    print_summary(results)


if __name__ == "__main__":
    main()
