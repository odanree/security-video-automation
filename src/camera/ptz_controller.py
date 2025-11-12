"""
PTZ Camera Controller

Controls PTZ (Pan-Tilt-Zoom) cameras using the ONVIF protocol.
Provides methods for preset-based movement and continuous control.

Example:
    from src.camera.ptz_controller import PTZController
    
    # Initialize controller
    ptz = PTZController(
        camera_ip='192.168.1.100',
        username='admin',
        password='password123'
    )
    
    # Move to preset
    ptz.goto_preset('1', speed=0.8)
    
    # Continuous movement
    ptz.continuous_move(pan_velocity=0.5, tilt_velocity=0, duration=2.0)
"""

import time
import logging
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

# ONVIF imports (will be imported dynamically to handle missing dependency gracefully)
try:
    from onvif import ONVIFCamera
    ONVIF_AVAILABLE = True
except ImportError:
    ONVIF_AVAILABLE = False
    ONVIFCamera = None


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CameraPosition:
    """Represents a camera's PTZ position"""
    pan: float      # -1.0 to 1.0 (left to right)
    tilt: float     # -1.0 to 1.0 (down to up)
    zoom: float     # 0.0 to 1.0 (wide to telephoto)


@dataclass
class PresetInfo:
    """Information about a camera preset"""
    token: str
    name: str
    position: Optional[CameraPosition] = None


class PTZController:
    """
    Control PTZ camera using ONVIF protocol
    
    Provides methods for:
    - Moving to preset positions
    - Continuous pan/tilt/zoom movement
    - Absolute positioning
    - Querying current position
    - Managing presets
    """
    
    def __init__(
        self,
        camera_ip: str,
        username: str,
        password: str,
        port: int = 80,
        wsdl_dir: Optional[str] = None
    ):
        """
        Initialize PTZ controller
        
        Args:
            camera_ip: Camera IP address
            username: Camera username
            password: Camera password
            port: ONVIF port (default: 80)
            wsdl_dir: Directory containing WSDL files (optional)
            
        Raises:
            ImportError: If python-onvif-zeep is not installed
            ConnectionError: If camera connection fails
        """
        if not ONVIF_AVAILABLE:
            raise ImportError(
                "python-onvif-zeep is not installed. "
                "Install it with: pip install onvif-zeep"
            )
        
        self.camera_ip = camera_ip
        self.username = username
        self.password = password
        self.port = port
        
        logger.info(f"Connecting to camera at {camera_ip}:{port}...")
        
        try:
            # Create ONVIF camera connection
            if wsdl_dir:
                self.camera = ONVIFCamera(
                    camera_ip, port, username, password, wsdl_dir
                )
            else:
                self.camera = ONVIFCamera(
                    camera_ip, port, username, password
                )
            
            # Create service references
            self.ptz_service = self.camera.create_ptz_service()
            self.media_service = self.camera.create_media_service()
            
            # Get media profile (use first profile by default)
            profiles = self.media_service.GetProfiles()
            if not profiles:
                raise ConnectionError("No media profiles found on camera")
            
            self.media_profile = profiles[0]
            self.profile_token = self.media_profile.token
            
            logger.info(f"✓ Connected to camera successfully")
            logger.info(f"  Using profile: {self.media_profile.Name}")
            
        except Exception as e:
            logger.error(f"Failed to connect to camera: {e}")
            raise ConnectionError(f"Camera connection failed: {e}")
    
    def goto_preset(self, preset_token: str, speed: float = 1.0) -> bool:
        """
        Move camera to a preset position
        
        Args:
            preset_token: Preset identifier (e.g., '1', '2', 'entrance')
            speed: Movement speed 0.0 to 1.0 (default: 1.0)
            
        Returns:
            True if successful, False otherwise
            
        Example:
            ptz.goto_preset('1', speed=0.8)  # Move to preset 1 at 80% speed
        """
        try:
            request = self.ptz_service.create_type('GotoPreset')
            request.ProfileToken = self.profile_token
            request.PresetToken = preset_token
            
            # Set movement speed
            request.Speed = {
                'PanTilt': {'x': speed, 'y': speed},
                'Zoom': {'x': speed}
            }
            
            logger.info(f"Moving to preset {preset_token} at speed {speed}")
            self.ptz_service.GotoPreset(request)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to move to preset {preset_token}: {e}")
            return False
    
    def continuous_move(
        self,
        pan_velocity: float,
        tilt_velocity: float,
        zoom_velocity: float = 0.0,
        duration: float = 1.0
    ) -> bool:
        """
        Continuous pan/tilt/zoom movement
        
        Args:
            pan_velocity: -1.0 (left) to 1.0 (right)
            tilt_velocity: -1.0 (down) to 1.0 (up)
            zoom_velocity: -1.0 (zoom out) to 1.0 (zoom in)
            duration: Movement duration in seconds
            
        Returns:
            True if successful, False otherwise
            
        Example:
            # Pan right for 2 seconds
            ptz.continuous_move(pan_velocity=0.5, tilt_velocity=0, duration=2.0)
            
            # Tilt up for 1 second
            ptz.continuous_move(pan_velocity=0, tilt_velocity=0.3, duration=1.0)
        """
        try:
            # Clamp velocities to valid range
            pan_velocity = max(-1.0, min(1.0, pan_velocity))
            tilt_velocity = max(-1.0, min(1.0, tilt_velocity))
            zoom_velocity = max(-1.0, min(1.0, zoom_velocity))
            
            request = self.ptz_service.create_type('ContinuousMove')
            request.ProfileToken = self.profile_token
            request.Velocity = {
                'PanTilt': {'x': pan_velocity, 'y': tilt_velocity},
                'Zoom': {'x': zoom_velocity}
            }
            
            logger.debug(
                f"Continuous move: pan={pan_velocity}, tilt={tilt_velocity}, "
                f"zoom={zoom_velocity}, duration={duration}s"
            )
            
            # Start movement
            self.ptz_service.ContinuousMove(request)
            
            # Wait for specified duration
            time.sleep(duration)
            
            # Stop movement
            self.stop()
            
            return True
            
        except Exception as e:
            logger.error(f"Continuous move failed: {e}")
            return False
    
    def absolute_move(
        self,
        pan: float,
        tilt: float,
        zoom: float = 0.0,
        speed: float = 1.0
    ) -> bool:
        """
        Move to absolute position
        
        Args:
            pan: Pan position -1.0 to 1.0
            tilt: Tilt position -1.0 to 1.0
            zoom: Zoom position 0.0 to 1.0
            speed: Movement speed 0.0 to 1.0
            
        Returns:
            True if successful, False otherwise
            
        Example:
            # Move to center position
            ptz.absolute_move(pan=0.0, tilt=0.0, zoom=0.0)
        """
        try:
            # Clamp positions to valid range
            pan = max(-1.0, min(1.0, pan))
            tilt = max(-1.0, min(1.0, tilt))
            zoom = max(0.0, min(1.0, zoom))
            
            request = self.ptz_service.create_type('AbsoluteMove')
            request.ProfileToken = self.profile_token
            request.Position = {
                'PanTilt': {'x': pan, 'y': tilt},
                'Zoom': {'x': zoom}
            }
            request.Speed = {
                'PanTilt': {'x': speed, 'y': speed},
                'Zoom': {'x': speed}
            }
            
            logger.debug(f"Absolute move: pan={pan}, tilt={tilt}, zoom={zoom}")
            self.ptz_service.AbsoluteMove(request)
            
            return True
            
        except Exception as e:
            logger.error(f"Absolute move failed: {e}")
            return False
    
    def relative_move(
        self,
        pan_delta: float,
        tilt_delta: float,
        zoom_delta: float = 0.0,
        speed: float = 1.0
    ) -> bool:
        """
        Move relative to current position
        
        Args:
            pan_delta: Pan movement delta -1.0 to 1.0
            tilt_delta: Tilt movement delta -1.0 to 1.0
            zoom_delta: Zoom movement delta -1.0 to 1.0
            speed: Movement speed 0.0 to 1.0
            
        Returns:
            True if successful, False otherwise
        """
        try:
            request = self.ptz_service.create_type('RelativeMove')
            request.ProfileToken = self.profile_token
            request.Translation = {
                'PanTilt': {'x': pan_delta, 'y': tilt_delta},
                'Zoom': {'x': zoom_delta}
            }
            request.Speed = {
                'PanTilt': {'x': speed, 'y': speed},
                'Zoom': {'x': speed}
            }
            
            logger.debug(
                f"Relative move: pan_delta={pan_delta}, tilt_delta={tilt_delta}"
            )
            self.ptz_service.RelativeMove(request)
            
            return True
            
        except Exception as e:
            logger.error(f"Relative move failed: {e}")
            return False
    
    def stop(self) -> bool:
        """
        Stop all PTZ movement
        
        Returns:
            True if successful, False otherwise
        """
        try:
            request = self.ptz_service.create_type('Stop')
            request.ProfileToken = self.profile_token
            request.PanTilt = True
            request.Zoom = True
            
            self.ptz_service.Stop(request)
            logger.debug("PTZ movement stopped")
            
            return True
            
        except Exception as e:
            logger.error(f"Stop command failed: {e}")
            return False
    
    def get_position(self) -> Optional[CameraPosition]:
        """
        Get current camera position
        
        Returns:
            CameraPosition object or None if failed
        """
        try:
            request = self.ptz_service.create_type('GetStatus')
            request.ProfileToken = self.profile_token
            
            status = self.ptz_service.GetStatus(request)
            
            position = CameraPosition(
                pan=status.Position.PanTilt.x,
                tilt=status.Position.PanTilt.y,
                zoom=status.Position.Zoom.x
            )
            
            logger.debug(f"Current position: {position}")
            return position
            
        except Exception as e:
            logger.error(f"Failed to get position: {e}")
            return None
    
    def get_presets(self) -> List[PresetInfo]:
        """
        Get list of available presets
        
        Returns:
            List of PresetInfo objects
        """
        try:
            request = self.ptz_service.create_type('GetPresets')
            request.ProfileToken = self.profile_token
            
            presets = self.ptz_service.GetPresets(request)
            
            preset_list = []
            for preset in presets:
                preset_info = PresetInfo(
                    token=preset.token,
                    name=preset.Name if preset.Name else f"Preset {preset.token}"
                )
                
                # Try to get position if available
                if hasattr(preset, 'PTZPosition') and preset.PTZPosition:
                    try:
                        preset_info.position = CameraPosition(
                            pan=preset.PTZPosition.PanTilt.x,
                            tilt=preset.PTZPosition.PanTilt.y,
                            zoom=preset.PTZPosition.Zoom.x
                        )
                    except:
                        pass
                
                preset_list.append(preset_info)
            
            logger.info(f"Found {len(preset_list)} presets")
            return preset_list
            
        except Exception as e:
            logger.error(f"Failed to get presets: {e}")
            return []
    
    def set_preset(self, preset_name: str) -> Optional[str]:
        """
        Save current position as a preset
        
        Args:
            preset_name: Name for the new preset
            
        Returns:
            Preset token if successful, None otherwise
        """
        try:
            request = self.ptz_service.create_type('SetPreset')
            request.ProfileToken = self.profile_token
            request.PresetName = preset_name
            
            response = self.ptz_service.SetPreset(request)
            
            logger.info(f"Created preset '{preset_name}' with token {response}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to set preset: {e}")
            return None
    
    def remove_preset(self, preset_token: str) -> bool:
        """
        Remove a preset
        
        Args:
            preset_token: Token of preset to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            request = self.ptz_service.create_type('RemovePreset')
            request.ProfileToken = self.profile_token
            request.PresetToken = preset_token
            
            self.ptz_service.RemovePreset(request)
            
            logger.info(f"Removed preset {preset_token}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove preset: {e}")
            return False
    
    def get_status(self) -> Dict:
        """
        Get comprehensive camera status
        
        Returns:
            Dictionary with status information
        """
        try:
            request = self.ptz_service.create_type('GetStatus')
            request.ProfileToken = self.profile_token
            
            status = self.ptz_service.GetStatus(request)
            
            return {
                'position': {
                    'pan': status.Position.PanTilt.x,
                    'tilt': status.Position.PanTilt.y,
                    'zoom': status.Position.Zoom.x
                },
                'move_status': {
                    'pan_tilt': status.MoveStatus.PanTilt if hasattr(status, 'MoveStatus') else 'UNKNOWN',
                    'zoom': status.MoveStatus.Zoom if hasattr(status, 'MoveStatus') else 'UNKNOWN'
                },
                'utc_time': status.UTCTime if hasattr(status, 'UTCTime') else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            return {}
    
    def home(self) -> bool:
        """
        Move camera to home position (if supported)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            request = self.ptz_service.create_type('GotoHomePosition')
            request.ProfileToken = self.profile_token
            request.Speed = 1.0
            
            logger.info("Moving to home position")
            self.ptz_service.GotoHomePosition(request)
            
            return True
            
        except Exception as e:
            logger.warning(f"Home position not supported or failed: {e}")
            return False
    
    def __repr__(self) -> str:
        """String representation"""
        return f"PTZController(camera_ip={self.camera_ip}, port={self.port})"
