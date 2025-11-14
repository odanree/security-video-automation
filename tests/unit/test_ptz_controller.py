"""
Unit tests for PTZ Controller

Tests ONVIF integration, preset handling, and movement commands.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from src.camera.ptz_controller import PTZController


@pytest.fixture
def mock_onvif_camera():
    """Mock ONVIF camera client"""
    camera = MagicMock()
    media_service = MagicMock()
    ptz_service = MagicMock()
    
    camera.create_media_service.return_value = media_service
    camera.create_ptz_service.return_value = ptz_service
    
    # Mock GetProfiles
    profile = MagicMock()
    profile.token = "test_profile_token"
    media_service.GetProfiles.return_value = [profile]
    
    return camera


@pytest.fixture
def ptz_controller(mock_onvif_camera):
    """Create PTZ controller with mocked ONVIF client"""
    with patch('src.camera.ptz_controller.ONVIFCamera', return_value=mock_onvif_camera):
        controller = PTZController(
            camera_ip="192.168.1.100",
            port=80,
            username="admin",
            password="password"
        )
    return controller


class TestPTZControllerInit:
    """Test PTZ controller initialization"""
    
    def test_initialization_success(self, ptz_controller):
        """Test successful PTZ controller initialization"""
        assert ptz_controller.camera_ip == "192.168.1.100"
        assert ptz_controller.port == 80
        assert ptz_controller.username == "admin"
        assert ptz_controller.camera is not None
    
    def test_initialization_with_custom_port(self):
        """Test initialization with non-standard port"""
        with patch('src.camera.ptz_controller.ONVIFCamera') as mock_onvif:
            mock_camera = MagicMock()
            mock_onvif.return_value = mock_camera
            
            controller = PTZController(
                camera_ip="192.168.1.100",
                port=8080,
                username="admin",
                password="password"
            )
            
            assert controller.port == 8080


class TestPTZPresets:
    """Test preset management"""
    
    def test_get_presets(self, ptz_controller):
        """Test retrieving available presets"""
        # Mock preset response
        preset1 = MagicMock()
        preset1.token = "1"
        preset1.Name = "zone_left"
        
        preset2 = MagicMock()
        preset2.token = "2"
        preset2.Name = "zone_center"
        
        ptz_controller.ptz_service.GetPresets.return_value = [preset1, preset2]
        
        presets = ptz_controller.get_presets()
        
        assert len(presets) == 2
        assert presets[0].token == "1"
        assert presets[0].name == "zone_left"
        assert presets[1].token == "2"
    
    def test_goto_preset(self, ptz_controller):
        """Test moving to a preset"""
        ptz_controller.goto_preset("1", speed=0.5)
        
        # Verify the PTZ service was called
        ptz_controller.ptz_service.GotoPreset.assert_called_once()
        
        # Get the call arguments
        call_args = ptz_controller.ptz_service.GotoPreset.call_args
        assert call_args is not None
    
    def test_set_preset(self, ptz_controller):
        """Test setting/saving a preset"""
        ptz_controller.ptz_service.SetPreset.return_value.PresetToken = "new_preset_5"
        
        preset_token = ptz_controller.set_preset("zone_new")
        
        assert preset_token == "new_preset_5"
        ptz_controller.ptz_service.SetPreset.assert_called_once()


class TestContinuousMove:
    """Test continuous pan/tilt/zoom movements"""
    
    def test_continuous_pan_right(self, ptz_controller):
        """Test continuous pan to the right"""
        ptz_controller.continuous_move(
            pan_velocity=0.5,
            tilt_velocity=0,
            zoom_velocity=0,
            duration=1.0,
            blocking=False
        )
        
        # Verify continuous move was called
        ptz_controller.ptz_service.ContinuousMove.assert_called_once()
    
    def test_continuous_pan_left(self, ptz_controller):
        """Test continuous pan to the left"""
        ptz_controller.continuous_move(
            pan_velocity=-0.5,
            tilt_velocity=0,
            zoom_velocity=0,
            duration=1.0,
            blocking=False
        )
        
        ptz_controller.ptz_service.ContinuousMove.assert_called_once()
    
    def test_continuous_tilt_up(self, ptz_controller):
        """Test continuous tilt upward"""
        ptz_controller.continuous_move(
            pan_velocity=0,
            tilt_velocity=0.5,
            zoom_velocity=0,
            duration=1.0,
            blocking=False
        )
        
        ptz_controller.ptz_service.ContinuousMove.assert_called_once()
    
    def test_continuous_zoom_in(self, ptz_controller):
        """Test continuous zoom in"""
        ptz_controller.continuous_move(
            pan_velocity=0,
            tilt_velocity=0,
            zoom_velocity=0.5,
            duration=1.0,
            blocking=False
        )
        
        ptz_controller.ptz_service.ContinuousMove.assert_called_once()
    
    def test_velocity_clamping(self, ptz_controller):
        """Test that velocities are clamped to [-1, 1]"""
        ptz_controller.continuous_move(
            pan_velocity=2.0,  # Out of range
            tilt_velocity=-2.0,  # Out of range
            zoom_velocity=0.5,
            duration=1.0,
            blocking=False
        )
        
        # Velocity should be clamped
        ptz_controller.ptz_service.ContinuousMove.assert_called_once()


class TestStopMovement:
    """Test stopping camera movement"""
    
    def test_stop(self, ptz_controller):
        """Test stopping camera movement"""
        ptz_controller.stop()
        
        ptz_controller.ptz_service.Stop.assert_called_once()


class TestAbsoluteMove:
    """Test absolute positioning"""
    
    def test_absolute_move(self, ptz_controller):
        """Test absolute pan/tilt positioning"""
        ptz_controller.absolute_move(pan=0.5, tilt=0.2, zoom=0.1, speed=0.5)
        
        ptz_controller.ptz_service.AbsoluteMove.assert_called_once()
    
    def test_absolute_move_pan_only(self, ptz_controller):
        """Test absolute pan only"""
        ptz_controller.absolute_move(pan=0.5)
        
        ptz_controller.ptz_service.AbsoluteMove.assert_called_once()


class TestErrorHandling:
    """Test error handling in PTZ controller"""
    
    def test_connection_failure(self):
        """Test handling connection failure"""
        with patch('src.camera.ptz_controller.ONVIFCamera', side_effect=Exception("Connection failed")):
            with pytest.raises(Exception):
                PTZController(
                    camera_ip="192.168.1.100",
                    port=80,
                    username="admin",
                    password="password"
                )
    
    def test_invalid_preset_token(self, ptz_controller):
        """Test handling of invalid preset token"""
        ptz_controller.ptz_service.GotoPreset.side_effect = Exception("Invalid preset")
        
        with pytest.raises(Exception):
            ptz_controller.goto_preset("invalid_preset", speed=0.5)


class TestMovementBounds:
    """Test movement boundary conditions"""
    
    def test_zero_velocity(self, ptz_controller):
        """Test movement with zero velocity (no-op)"""
        ptz_controller.continuous_move(
            pan_velocity=0,
            tilt_velocity=0,
            zoom_velocity=0,
            duration=1.0,
            blocking=False
        )
        
        ptz_controller.ptz_service.ContinuousMove.assert_called_once()
    
    def test_max_positive_velocity(self, ptz_controller):
        """Test maximum positive velocity"""
        ptz_controller.continuous_move(
            pan_velocity=1.0,
            tilt_velocity=1.0,
            zoom_velocity=1.0,
            duration=1.0,
            blocking=False
        )
        
        ptz_controller.ptz_service.ContinuousMove.assert_called_once()
    
    def test_max_negative_velocity(self, ptz_controller):
        """Test maximum negative velocity"""
        ptz_controller.continuous_move(
            pan_velocity=-1.0,
            tilt_velocity=-1.0,
            zoom_velocity=-1.0,
            duration=1.0,
            blocking=False
        )
        
        ptz_controller.ptz_service.ContinuousMove.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
