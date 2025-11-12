"""
Configuration Loader
Loads and validates YAML configuration files for the security camera system
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class CameraConfig:
    """Camera configuration"""
    id: str
    name: str
    enabled: bool
    ip: str
    port: int
    username: str
    password: str
    stream: Dict[str, Any]
    ptz: Dict[str, Any]
    
    def get_rtsp_url(self) -> str:
        """Get RTSP URL from configuration"""
        return self.stream.get('rtsp_url', '')
    
    def get_preset_by_name(self, name: str) -> Optional[str]:
        """Get preset token by preset name"""
        presets = self.ptz.get('presets', [])
        for preset in presets:
            if preset.get('name') == name:
                return preset.get('token')
        return None
    
    def get_preset_names(self) -> List[str]:
        """Get list of all preset names"""
        presets = self.ptz.get('presets', [])
        return [p.get('name') for p in presets if p.get('name')]


@dataclass
class TrackingConfig:
    """Tracking rules configuration"""
    enabled: bool
    mode: str
    target_classes: List[str]
    detection: Dict[str, Any]
    motion: Dict[str, Any]
    zones: List[Dict[str, Any]]
    direction_triggers: Dict[str, Any]
    ptz: Dict[str, Any]
    filters: Dict[str, Any]
    events: Dict[str, Any]
    notifications: Dict[str, Any] = field(default_factory=dict)
    advanced: Dict[str, Any] = field(default_factory=dict)
    
    def get_zone_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get zone configuration by name"""
        for zone in self.zones:
            if zone.get('name') == name:
                return zone
        return None
    
    def is_direction_enabled(self, direction: str) -> bool:
        """Check if a direction trigger is enabled"""
        trigger = self.direction_triggers.get(direction, {})
        return trigger.get('enabled', False)


@dataclass
class AIConfig:
    """AI model configuration"""
    object_detection: Dict[str, Any]
    face_detection: Dict[str, Any] = field(default_factory=dict)
    license_plate: Dict[str, Any] = field(default_factory=dict)
    pose_estimation: Dict[str, Any] = field(default_factory=dict)
    training: Dict[str, Any] = field(default_factory=dict)
    
    def get_model_path(self) -> str:
        """Get path to object detection model"""
        model_config = self.object_detection.get('model', {})
        model_type = model_config.get('type', 'yolov8')
        model_size = model_config.get('size', 'n')
        
        # Default path if not specified
        default_path = f"models/{model_type}{model_size}.pt"
        return model_config.get('path', default_path)
    
    def get_device(self) -> str:
        """Get inference device (cpu, cuda, mps)"""
        inference = self.object_detection.get('inference', {})
        return inference.get('device', 'cpu')
    
    def get_confidence_threshold(self) -> float:
        """Get global confidence threshold"""
        inference = self.object_detection.get('inference', {})
        return inference.get('confidence_threshold', 0.6)


class ConfigLoader:
    """Load and manage configuration files"""
    
    def __init__(self, config_dir: str = "config"):
        """
        Initialize configuration loader
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)
        
        if not self.config_dir.exists():
            raise ValueError(f"Configuration directory not found: {config_dir}")
    
    def load_yaml(self, filename: str) -> Dict[str, Any]:
        """
        Load a YAML configuration file
        
        Args:
            filename: Name of the YAML file
            
        Returns:
            Dictionary containing configuration data
        """
        filepath = self.config_dir / filename
        
        if not filepath.exists():
            raise FileNotFoundError(f"Configuration file not found: {filepath}")
        
        try:
            with open(filepath, 'r') as f:
                config = yaml.safe_load(f)
                
            # Replace environment variables
            config = self._replace_env_vars(config)
            
            return config
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing YAML file {filename}: {e}")
    
    def _replace_env_vars(self, config: Any) -> Any:
        """
        Recursively replace environment variable placeholders
        
        Args:
            config: Configuration data (dict, list, or primitive)
            
        Returns:
            Configuration with environment variables replaced
        """
        if isinstance(config, dict):
            return {k: self._replace_env_vars(v) for k, v in config.items()}
        elif isinstance(list, list):
            return [self._replace_env_vars(item) for item in config]
        elif isinstance(config, str):
            # Replace ${VAR_NAME} with environment variable value
            if config.startswith('${') and config.endswith('}'):
                var_name = config[2:-1]
                return os.getenv(var_name, config)  # Return original if not found
            return config
        else:
            return config
    
    def load_camera_config(self) -> Dict[str, Any]:
        """Load camera configuration"""
        return self.load_yaml('camera_config.yaml')
    
    def load_tracking_config(self) -> TrackingConfig:
        """Load tracking rules configuration"""
        config = self.load_yaml('tracking_rules.yaml')
        tracking = config.get('tracking', {})
        
        return TrackingConfig(
            enabled=tracking.get('enabled', True),
            mode=tracking.get('mode', 'AUTO'),
            target_classes=tracking.get('target_classes', ['person']),
            detection=tracking.get('detection', {}),
            motion=tracking.get('motion', {}),
            zones=tracking.get('zones', []),
            direction_triggers=tracking.get('direction_triggers', {}),
            ptz=tracking.get('ptz', {}),
            filters=tracking.get('filters', {}),
            events=tracking.get('events', {}),
            notifications=tracking.get('notifications', {}),
            advanced=tracking.get('advanced', {})
        )
    
    def load_ai_config(self) -> AIConfig:
        """Load AI model configuration"""
        config = self.load_yaml('ai_config.yaml')
        
        return AIConfig(
            object_detection=config.get('object_detection', {}),
            face_detection=config.get('face_detection', {}),
            license_plate=config.get('license_plate', {}),
            pose_estimation=config.get('pose_estimation', {}),
            training=config.get('training', {})
        )
    
    def get_enabled_cameras(self) -> List[CameraConfig]:
        """
        Get list of enabled cameras
        
        Returns:
            List of CameraConfig objects for enabled cameras
        """
        config = self.load_camera_config()
        cameras = config.get('cameras', [])
        
        enabled_cameras = []
        for cam in cameras:
            if cam.get('enabled', False):
                enabled_cameras.append(CameraConfig(
                    id=cam.get('id', ''),
                    name=cam.get('name', ''),
                    enabled=cam.get('enabled', True),
                    ip=cam.get('ip', ''),
                    port=cam.get('port', 80),
                    username=cam.get('username', ''),
                    password=cam.get('password', ''),
                    stream=cam.get('stream', {}),
                    ptz=cam.get('ptz', {})
                ))
        
        return enabled_cameras
    
    def get_camera_by_id(self, camera_id: str) -> Optional[CameraConfig]:
        """
        Get camera configuration by ID
        
        Args:
            camera_id: Camera identifier
            
        Returns:
            CameraConfig object or None if not found
        """
        cameras = self.get_enabled_cameras()
        for cam in cameras:
            if cam.id == camera_id:
                return cam
        return None
    
    def get_global_settings(self) -> Dict[str, Any]:
        """Get global camera settings"""
        config = self.load_camera_config()
        return config.get('global', {})
    
    def validate_config(self) -> bool:
        """
        Validate all configuration files
        
        Returns:
            True if all configurations are valid
        """
        try:
            # Load all configs to check for errors
            self.load_camera_config()
            self.load_tracking_config()
            self.load_ai_config()
            
            # Check if at least one camera is enabled
            cameras = self.get_enabled_cameras()
            if not cameras:
                print("Warning: No cameras enabled in configuration")
                return False
            
            # Validate tracking zones
            tracking = self.load_tracking_config()
            for zone in tracking.zones:
                x_range = zone.get('x_range', [])
                y_range = zone.get('y_range', [])
                
                if len(x_range) != 2 or len(y_range) != 2:
                    print(f"Invalid zone range for {zone.get('name')}")
                    return False
                
                if not (0 <= x_range[0] <= x_range[1] <= 1):
                    print(f"Invalid x_range for {zone.get('name')}")
                    return False
                
                if not (0 <= y_range[0] <= y_range[1] <= 1):
                    print(f"Invalid y_range for {zone.get('name')}")
                    return False
            
            print("✓ All configurations validated successfully")
            return True
            
        except Exception as e:
            print(f"Configuration validation failed: {e}")
            return False


# Convenience function for loading configuration
def load_config(config_dir: str = "config") -> tuple:
    """
    Load all configuration files
    
    Args:
        config_dir: Directory containing configuration files
        
    Returns:
        Tuple of (camera_config, tracking_config, ai_config)
    """
    loader = ConfigLoader(config_dir)
    
    camera_config = loader.load_camera_config()
    tracking_config = loader.load_tracking_config()
    ai_config = loader.load_ai_config()
    
    return camera_config, tracking_config, ai_config


if __name__ == "__main__":
    """Test configuration loader"""
    import sys
    
    print("Testing configuration loader...\n")
    
    try:
        loader = ConfigLoader("config")
        
        # Validate all configs
        print("Validating configurations...")
        if not loader.validate_config():
            sys.exit(1)
        
        print("\n" + "="*60)
        print("CAMERA CONFIGURATION")
        print("="*60)
        
        cameras = loader.get_enabled_cameras()
        print(f"\nEnabled cameras: {len(cameras)}")
        
        for cam in cameras:
            print(f"\n  Camera: {cam.name} ({cam.id})")
            print(f"    IP: {cam.ip}:{cam.port}")
            print(f"    RTSP: {cam.get_rtsp_url()}")
            print(f"    Presets: {', '.join(cam.get_preset_names())}")
        
        global_settings = loader.get_global_settings()
        print(f"\n  Global Settings:")
        print(f"    Process every N frames: {global_settings.get('process_every_n_frames')}")
        print(f"    Use GPU: {global_settings.get('use_gpu')}")
        print(f"    Display video: {global_settings.get('display_video')}")
        
        print("\n" + "="*60)
        print("TRACKING CONFIGURATION")
        print("="*60)
        
        tracking = loader.load_tracking_config()
        print(f"\n  Enabled: {tracking.enabled}")
        print(f"  Mode: {tracking.mode}")
        print(f"  Target classes: {', '.join(tracking.target_classes)}")
        print(f"  Zones: {len(tracking.zones)}")
        
        for zone in tracking.zones:
            print(f"    - {zone.get('name')}: x={zone.get('x_range')}, preset={zone.get('preset')}")
        
        print(f"\n  Direction Triggers:")
        for direction, config in tracking.direction_triggers.items():
            if config.get('enabled'):
                print(f"    - {direction}: {config.get('target_zones')}")
        
        print("\n" + "="*60)
        print("AI CONFIGURATION")
        print("="*60)
        
        ai = loader.load_ai_config()
        print(f"\n  Model: {ai.get_model_path()}")
        print(f"  Device: {ai.get_device()}")
        print(f"  Confidence: {ai.get_confidence_threshold()}")
        
        print("\n✓ Configuration test completed successfully!")
        
    except Exception as e:
        print(f"\n✗ Configuration test failed: {e}")
        sys.exit(1)
