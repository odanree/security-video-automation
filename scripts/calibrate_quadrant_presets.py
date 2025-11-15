"""
Calibrate Quadrant Tracking Presets
====================================

This script helps you set up quadrant tracking by:
1. Showing live camera feed
2. Allowing you to manually position the camera for each quadrant
3. Saving those positions as camera presets
4. Updating the tracking_rules.yaml configuration

Usage:
    python scripts/calibrate_quadrant_presets.py

Instructions:
    - Use arrow keys to pan/tilt the camera
    - Use +/- keys to zoom in/out
    - Press SPACE to save the current position for the quadrant
    - Press Q to quit
"""

import sys
import os
import time
import yaml
import cv2
import threading
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.camera.ptz_controller import PTZController
from src.video.stream_handler import VideoStreamHandler
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class QuadrantCalibrator:
    """Interactive calibrator for quadrant tracking presets"""
    
    def __init__(self):
        """Initialize calibrator"""
        # Load camera configuration from YAML
        config_path = project_root / 'config' / 'camera_config.yaml'
        
        with open(config_path, 'r') as f:
            camera_config_data = yaml.safe_load(f)
        
        # Get first camera config
        camera = camera_config_data['cameras'][0]
        
        # Initialize PTZ controller
        self.ptz = PTZController(
            camera_ip=camera['ip'],
            port=camera['port'],
            username=camera['username'],
            password=camera['password']
        )
        
        # Initialize video stream
        rtsp_url = camera['stream']['rtsp_url']
        logger.info(f"Connecting to video stream: {rtsp_url}")
        self.stream = VideoStreamHandler(
            stream_url=rtsp_url,
            name="CalibrationStream",
            buffer_size=1
        )
        self.stream.start()
        
        # Wait for stream to start
        time.sleep(2)
        
        # Quadrant definitions
        self.quadrants = [
            {
                'name': 'top_left',
                'description': 'Top-Left quadrant (0-50% X, 0-50% Y)',
                'preset_name': 'QuadTopLeft',
                'saved': False,
                'token': None
            },
            {
                'name': 'top_right',
                'description': 'Top-Right quadrant (50-100% X, 0-50% Y)',
                'preset_name': 'QuadTopRight',
                'saved': False,
                'token': None
            },
            {
                'name': 'bottom_left',
                'description': 'Bottom-Left quadrant (0-50% X, 50-100% Y)',
                'preset_name': 'QuadBottomLeft',
                'saved': False,
                'token': None
            },
            {
                'name': 'bottom_right',
                'description': 'Bottom-Right quadrant (50-100% X, 50-100% Y)',
                'preset_name': 'QuadBottomRight',
                'saved': False,
                'token': None
            }
        ]
        
        self.current_quadrant_index = 0
        
    def print_instructions(self):
        """Print control instructions"""
        print("\n" + "=" * 60)
        print("QUADRANT CALIBRATION - CAMERA CONTROLS")
        print("=" * 60)
        print("\nLive Video Feed:")
        print("  A video window will open showing the camera view")
        print("  The current quadrant will be highlighted in GREEN")
        print("  Grid lines show the quadrant boundaries")
        print("\nManual PTZ Controls (use video window):")
        print("  Arrow Keys or WASD:")
        print("    ↑ / W     - Tilt UP")
        print("    ↓ / S     - Tilt DOWN")
        print("    ← / A     - Pan LEFT")
        print("    → / D     - Pan RIGHT")
        print("\n  Zoom:")
        print("    + / =     - Zoom IN")
        print("    - / _     - Zoom OUT")
        print("\n  Actions:")
        print("    SPACE     - Save current position as preset")
        print("    N         - Move to next quadrant")
        print("    P         - Move to previous quadrant")
        print("    1-4       - Jump to specific quadrant")
        print("    Q / ESC   - Quit calibration")
        print("\n" + "=" * 60 + "\n")
        
    def print_current_quadrant(self):
        """Display current quadrant being calibrated"""
        quad = self.quadrants[self.current_quadrant_index]
        status = "✅ SAVED" if quad['saved'] else "⚠️  NOT SAVED"
        
        print(f"\n{'─' * 60}")
        print(f"Quadrant {self.current_quadrant_index + 1} of {len(self.quadrants)}: {quad['name'].upper()}")
        print(f"Description: {quad['description']}")
        print(f"Preset Name: {quad['preset_name']}")
        print(f"Status: {status}")
        print(f"{'─' * 60}")
        print("\nPosition the camera to cover this quadrant, then press SPACE to save.")
        
    def manual_control(self, command: str):
        """
        Execute manual PTZ control command
        
        Args:
            command: Control command (up, down, left, right, zoom_in, zoom_out)
        """
        duration = 0.3  # Short movement duration
        speed = 0.5
        
        try:
            if command == 'up':
                self.ptz.continuous_move(0, speed, 0, duration)
                print("↑ Tilting UP...")
            elif command == 'down':
                self.ptz.continuous_move(0, -speed, 0, duration)
                print("↓ Tilting DOWN...")
            elif command == 'left':
                self.ptz.continuous_move(-speed, 0, 0, duration)
                print("← Panning LEFT...")
            elif command == 'right':
                self.ptz.continuous_move(speed, 0, 0, duration)
                print("→ Panning RIGHT...")
            elif command == 'zoom_in':
                self.ptz.continuous_move(0, 0, speed, duration)
                print("🔍 Zooming IN...")
            elif command == 'zoom_out':
                self.ptz.continuous_move(0, 0, -speed, duration)
                print("🔍 Zooming OUT...")
                
        except Exception as e:
            logger.error(f"Manual control error: {e}")
            
    def save_current_position(self):
        """Save current camera position as preset for current quadrant"""
        quad = self.quadrants[self.current_quadrant_index]
        
        print(f"\n💾 Saving preset '{quad['preset_name']}'...")
        
        try:
            token = self.ptz.set_preset(quad['preset_name'])
            
            if token:
                quad['saved'] = True
                quad['token'] = token
                print(f"✅ Preset saved successfully! Token: {token}")
                
                # Auto-advance to next quadrant
                if self.current_quadrant_index < len(self.quadrants) - 1:
                    time.sleep(0.5)
                    self.current_quadrant_index += 1
                    self.print_current_quadrant()
                else:
                    print("\n🎉 All quadrants calibrated!")
                    self.print_summary()
            else:
                print("❌ Failed to save preset")
                
        except Exception as e:
            logger.error(f"Error saving preset: {e}")
            print(f"❌ Error: {e}")
            
    def print_summary(self):
        """Print summary of saved presets"""
        print("\n" + "=" * 60)
        print("CALIBRATION SUMMARY")
        print("=" * 60)
        
        all_saved = all(q['saved'] for q in self.quadrants)
        
        for i, quad in enumerate(self.quadrants, 1):
            status = "✅" if quad['saved'] else "❌"
            token = quad['token'] if quad['saved'] else "N/A"
            print(f"{status} {i}. {quad['name']:15} - {quad['preset_name']:20} (Token: {token})")
            
        print("=" * 60)
        
        if all_saved:
            print("\n✅ All presets saved successfully!")
            print("\nNext step: Update config/tracking_rules.yaml")
            self.update_config()
        else:
            print("\n⚠️  Some presets not saved. Complete calibration before using quadrant tracking.")
            
    def update_config(self):
        """Update tracking_rules.yaml with new preset tokens"""
        config_file = project_root / 'config' / 'tracking_rules.yaml'
        
        print(f"\n📝 Updating {config_file}...")
        
        try:
            # Load current config
            with open(config_file, 'r') as f:
                config_data = yaml.safe_load(f)
                
            # Update quadrant presets
            if 'tracking' not in config_data:
                config_data['tracking'] = {}
            if 'quadrant_tracking' not in config_data['tracking']:
                config_data['tracking']['quadrant_tracking'] = {}
            if 'quadrants' not in config_data['tracking']['quadrant_tracking']:
                config_data['tracking']['quadrant_tracking']['quadrants'] = {}
                
            quadrants_config = config_data['tracking']['quadrant_tracking']['quadrants']
            
            for quad in self.quadrants:
                if quad['saved']:
                    quadrant_name = quad['name']
                    if quadrant_name not in quadrants_config:
                        quadrants_config[quadrant_name] = {}
                        
                    quadrants_config[quadrant_name]['preset'] = quad['preset_name']
                    
                    # Preserve other settings
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
                    
            # Save updated config
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
                
            print("✅ Configuration updated successfully!")
            print(f"\nUpdated quadrant presets in {config_file}")
            print("\nYou can now enable quadrant tracking by setting:")
            print("  tracking.quadrant_tracking.enabled: true")
            
        except Exception as e:
            logger.error(f"Error updating config: {e}")
            print(f"❌ Failed to update config: {e}")
            print("\nManually update config/tracking_rules.yaml with these presets:")
            for quad in self.quadrants:
                if quad['saved']:
                    print(f"  {quad['name']}:")
                    print(f"    preset: \"{quad['preset_name']}\"")
                    
    def run(self):
        """Run interactive calibration with live video feed"""
        self.print_instructions()
        self.print_current_quadrant()
        
        print("\nReady! Use controls to position camera, then press SPACE to save.")
        print("Video window will open shortly...")
        
        running = True
        
        # Create display window
        window_name = "Quadrant Calibration - Live Feed"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 1280, 720)
        
        try:
            while running:
                # Get and display video frame
                frame = self.stream.read()
                
                if frame is not None:
                    # Add overlay with current quadrant info
                    quad = self.quadrants[self.current_quadrant_index]
                    status_text = f"Quadrant {self.current_quadrant_index + 1}/4: {quad['name']}"
                    saved_text = "SAVED ✓" if quad['saved'] else "NOT SAVED - Press SPACE to save"
                    
                    # Draw semi-transparent overlay at top
                    overlay = frame.copy()
                    cv2.rectangle(overlay, (0, 0), (frame.shape[1], 80), (0, 0, 0), -1)
                    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
                    
                    # Add text
                    cv2.putText(frame, status_text, (20, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                    cv2.putText(frame, saved_text, (20, 60), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, 
                               (0, 255, 0) if quad['saved'] else (0, 165, 255), 2)
                    
                    # Draw quadrant grid overlay
                    h, w = frame.shape[:2]
                    mid_x, mid_y = w // 2, h // 2
                    
                    # Draw grid lines
                    cv2.line(frame, (mid_x, 0), (mid_x, h), (255, 255, 0), 1)
                    cv2.line(frame, (0, mid_y), (w, mid_y), (255, 255, 0), 1)
                    
                    # Highlight current quadrant
                    if self.current_quadrant_index == 0:  # top_left
                        cv2.rectangle(frame, (0, 0), (mid_x, mid_y), (0, 255, 0), 3)
                    elif self.current_quadrant_index == 1:  # top_right
                        cv2.rectangle(frame, (mid_x, 0), (w, mid_y), (0, 255, 0), 3)
                    elif self.current_quadrant_index == 2:  # bottom_left
                        cv2.rectangle(frame, (0, mid_y), (mid_x, h), (0, 255, 0), 3)
                    elif self.current_quadrant_index == 3:  # bottom_right
                        cv2.rectangle(frame, (mid_x, mid_y), (w, h), (0, 255, 0), 3)
                    
                    cv2.imshow(window_name, frame)
                
                # Handle keyboard input (OpenCV waitKey)
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q') or key == 27:  # Q or ESC
                    running = False
                elif key == ord('w') or key == 82:  # W or Up arrow
                    self.manual_control('up')
                elif key == ord('s') or key == 84:  # S or Down arrow
                    self.manual_control('down')
                elif key == ord('a') or key == 81:  # A or Left arrow
                    self.manual_control('left')
                elif key == ord('d') or key == 83:  # D or Right arrow
                    self.manual_control('right')
                elif key == ord('+') or key == ord('='):
                    self.manual_control('zoom_in')
                elif key == ord('-') or key == ord('_'):
                    self.manual_control('zoom_out')
                elif key == ord(' '):  # Space
                    self.save_current_position()
                elif key == ord('n'):  # Next quadrant
                    if self.current_quadrant_index < len(self.quadrants) - 1:
                        self.current_quadrant_index += 1
                        self.print_current_quadrant()
                elif key == ord('p'):  # Previous quadrant
                    if self.current_quadrant_index > 0:
                        self.current_quadrant_index -= 1
                        self.print_current_quadrant()
                elif key in [ord('1'), ord('2'), ord('3'), ord('4')]:  # Jump to quadrant
                    index = int(chr(key)) - 1
                    if 0 <= index < len(self.quadrants):
                        self.current_quadrant_index = index
                        self.print_current_quadrant()
                        
        finally:
            # Cleanup
            cv2.destroyAllWindows()
            self.stream.stop()
            
        print("\n\n👋 Calibration ended")
        self.print_summary()


def main():
    """Main entry point"""
    print("\n🎯 Quadrant Tracking Calibration Tool")
    print("=" * 60)
    
    try:
        calibrator = QuadrantCalibrator()
        calibrator.run()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Calibration interrupted by user")
    except Exception as e:
        logger.error(f"Calibration failed: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        return 1
        
    return 0


if __name__ == "__main__":
    sys.exit(main())
