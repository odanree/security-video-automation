"""
Simple Quadrant Calibration Tool (No Video Stream)
===================================================

Use this with your camera's web admin interface for viewing.

Steps:
1. Open camera admin interface in browser: http://192.168.1.107:8080
2. Run this script to control PTZ
3. Position camera for each quadrant using this script
4. View camera position in browser
5. Press SPACE to save preset

Usage:
    python scripts/calibrate_quadrant_presets_simple.py
"""

import sys
import time
import yaml
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.camera.ptz_controller import PTZController
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_camera_config():
    """Load camera configuration"""
    config_path = project_root / 'config' / 'camera_config.yaml'
    with open(config_path, 'r') as f:
        data = yaml.safe_load(f)
    return data['cameras'][0]


def update_tracking_config(quadrants):
    """Update tracking_rules.yaml with preset names"""
    config_file = project_root / 'config' / 'tracking_rules.yaml'
    
    try:
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)
            
        if 'tracking' not in config_data:
            config_data['tracking'] = {}
        if 'quadrant_tracking' not in config_data['tracking']:
            config_data['tracking']['quadrant_tracking'] = {}
        if 'quadrants' not in config_data['tracking']['quadrant_tracking']:
            config_data['tracking']['quadrant_tracking']['quadrants'] = {}
            
        quadrants_config = config_data['tracking']['quadrant_tracking']['quadrants']
        
        for quad in quadrants:
            if quad['saved']:
                quadrant_name = quad['name']
                if quadrant_name not in quadrants_config:
                    quadrants_config[quadrant_name] = {}
                    
                quadrants_config[quadrant_name]['preset'] = quad['preset_name']
                
                if 'x_range' not in quadrants_config[quadrant_name]:
                    if 'left' in quadrant_name:
                        quadrants_config[quadrant_name]['x_range'] = [0.0, 0.5]
                    else:
                        quadrants_config[quadrant_name]['x_range'] = [0.5, 1.0]
                        
                if 'y_range' not in quadrants_config[quadrant_name]:
                    if 'top' in quadrant_name:
                        quadrants_config[quadrant_name]['y_range'] = [0.0, 0.5]
                    else:
                        quadrants_config[quadrant_name]['y_range'] = [0.5, 1.0]
                        
                quadrants_config[quadrant_name]['description'] = quad['description']
                
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
            
        print(f"\n✅ Configuration updated: {config_file}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        print(f"❌ Failed to update config: {e}")
        return False


def main():
    print("\n" + "="*70)
    print("🎯 SIMPLE QUADRANT CALIBRATION")
    print("="*70)
    
    # Load camera config
    camera = load_camera_config()
    camera_ip = camera['ip']
    
    print(f"\n📹 Camera: {camera_ip}")
    print(f"\n⚠️  IMPORTANT: Open camera web viewer in your browser:")
    print(f"   http://{camera_ip}:8080")
    print(f"\n   You'll use the browser to VIEW the camera")
    print(f"   You'll use THIS script to enter preset names\n")
    
    input("Press ENTER when ready...")
    
    # Initialize PTZ controller
    print("\n🔌 Connecting to camera...")
    ptz = PTZController(
        camera_ip=camera['ip'],
        port=camera['port'],
        username=camera['username'],
        password=camera['password']
    )
    print("✅ Connected!\n")
    
    # Get available presets from camera
    print("📋 Fetching available presets from camera...")
    try:
        presets = ptz.get_presets()
        if presets:
            print("\n✅ Available presets on camera:")
            for preset in presets[:10]:  # Show first 10
                print(f"   - {preset.Name} (Token: {preset.token})")
            if len(presets) > 10:
                print(f"   ... and {len(presets) - 10} more")
        else:
            print("   No presets found on camera")
    except Exception as e:
        print(f"   ⚠️  Could not fetch presets: {e}")
        presets = []
    
    print("\n" + "="*70)
    
    # Define quadrants
    quadrants = [
        {
            'name': 'top_left',
            'description': 'Top-Left (upper-left area of view)',
            'preset_name': None,
            'saved': False
        },
        {
            'name': 'top_right',
            'description': 'Top-Right (upper-right area of view)',
            'preset_name': None,
            'saved': False
        },
        {
            'name': 'bottom_left',
            'description': 'Bottom-Left (lower-left area of view)',
            'preset_name': None,
            'saved': False
        },
        {
            'name': 'bottom_right',
            'description': 'Bottom-Right (lower-right area of view)',
            'preset_name': None,
            'saved': False
        }
    ]
    
    print("\n📝 ENTER PRESET NAMES FOR EACH QUADRANT")
    print("   You can enter either:")
    print("   - Preset NAME (e.g., 'MyPreset')")
    print("   - Preset TOKEN (e.g., 'Preset001')")
    print("   - Or press ENTER to skip")
    print("="*70 + "\n")
    
    current_index = 0
    
    # Collect preset names for each quadrant
    for i, quad in enumerate(quadrants):
        print(f"\n{'─'*70}")
        print(f"📍 QUADRANT {i + 1} of {len(quadrants)}: {quad['name'].upper()}")
        print(f"   {quad['description']}")
        print(f"{'─'*70}")
        
        while True:
            preset_input = input(f"\nEnter preset name/token for {quad['name']} (or ENTER to skip): ").strip()
            
            if not preset_input:
                print("⚠️  Skipping this quadrant")
                break
                
            # Validate preset exists
            preset_found = False
            if presets:
                for p in presets:
                    preset_name = getattr(p, 'Name', str(p.token))
                    if preset_input.lower() in [preset_name.lower(), str(p.token).lower()]:
                        quad['preset_name'] = p.token  # Use token
                        quad['saved'] = True
                        preset_found = True
                        print(f"✅ Using preset: {preset_name} (Token: {p.token})")
                        break
            
            if not preset_found:
                # Just use the input as-is
                quad['preset_name'] = preset_input
                quad['saved'] = True
                print(f"✅ Will use preset: {preset_input}")
            
            break
    
    # Show summary
    print("\n" + "="*70)
    print("📋 CONFIGURATION SUMMARY")
    print("="*70)
        quad = quadrants[current_index]
        status = "✅ SAVED" if quad['saved'] else "⚠️  NOT SAVED"
        
        print(f"\n{'─'*70}")
        print(f"📍 QUADRANT {current_index + 1} of {len(quadrants)}: {quad['name'].upper()}")
        print(f"   {quad['description']}")
        print(f"   Status: {status}")
        print(f"{'─'*70}")
        
        if not quad['saved']:
            print("\n👉 Position camera to view this quadrant in browser, then press SPACE")
        
        # Command loop
        while True:
            cmd = input("\nCommand (w/a/s/d/+/-/space/n/p/q): ").lower().strip()
            
            if cmd in ['w', 'up']:
                ptz.continuous_move(0, 0.2, 0, 0.2)
                print("↑ Tilting UP...")
                
            elif cmd in ['s', 'down']:
                ptz.continuous_move(0, -0.2, 0, 0.2)
                print("↓ Tilting DOWN...")
                
            elif cmd in ['a', 'left']:
                ptz.continuous_move(-0.2, 0, 0, 0.2)
                print("← Panning LEFT...")
                
            elif cmd in ['d', 'right']:
                ptz.continuous_move(0.2, 0, 0, 0.2)
                print("→ Panning RIGHT...")
                
            elif cmd in ['+', '=', 'zoom in']:
                ptz.continuous_move(0, 0, 0.3, 0.2)
                print("🔍 Zooming IN...")
                
            elif cmd in ['-', '_', 'zoom out']:
                ptz.continuous_move(0, 0, -0.3, 0.2)
                print("🔍 Zooming OUT...")
                
            elif cmd in ['space', ' ', 'save']:
                print(f"\n💾 Saving preset '{quad['preset_name']}'...")
                token = ptz.set_preset(quad['preset_name'])
                
                if token:
                    quad['saved'] = True
                    print(f"✅ Preset saved! Token: {token}")
                    print(f"\n🎉 Quadrant {current_index + 1} complete!")
                    time.sleep(1)
                    current_index += 1
                    break
                else:
                    print("❌ Failed to save preset")
                    
            elif cmd in ['n', 'next']:
                if current_index < len(quadrants) - 1:
                    current_index += 1
                    break
                else:
                    print("⚠️  Already at last quadrant")
                    
            elif cmd in ['p', 'prev', 'previous']:
                if current_index > 0:
                    current_index -= 1
                    break
                else:
                    print("⚠️  Already at first quadrant")
                    
            elif cmd in ['q', 'quit', 'exit']:
                print("\n👋 Exiting calibration...")
                return
                
            else:
                print(f"❓ Unknown command: {cmd}")
    
    # All quadrants saved
    print("\n" + "="*70)
    print("🎉 ALL QUADRANTS CALIBRATED!")
    print("="*70)
    
    for i, quad in enumerate(quadrants, 1):
        status = "✅" if quad['saved'] else "❌"
        print(f"{status} {i}. {quad['name']:15} - {quad['preset_name']}")
    
    print("="*70)
    
    # Update config
    print("\n📝 Updating tracking_rules.yaml...")
    if update_tracking_config(quadrants):
        print("\n✅ Configuration updated successfully!")
        print("\nNext steps:")
        print("1. Edit config/tracking_rules.yaml")
        print("2. Set: tracking.quadrant_tracking.enabled: true")
        print("3. Restart dashboard: .\\restart_dashboard.ps1")
    
    print("\n✅ Calibration complete!\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Calibration interrupted")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
