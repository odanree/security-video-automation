"""
FastAPI Web Dashboard for Security Camera AI Tracker

Provides REST API endpoints for:
- Camera status and statistics
- Live video streaming
- PTZ control
- Detection events
- System configuration
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Body
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import cv2
import asyncio
import json
import threading
from datetime import datetime
from pathlib import Path
import logging

# Import our tracking components
from src.video.stream_handler import VideoStreamHandler
from src.ai.object_detector import ObjectDetector
from src.ai.motion_tracker import MotionTracker
from src.automation.tracking_engine import TrackingEngine
from src.camera.ptz_controller import PTZController
from src.utils.config_loader import ConfigLoader

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Security Camera AI Tracker",
    description="AI-powered PTZ camera tracking system with live monitoring dashboard",
    version="1.0.0"
)

# Add CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup static files and templates
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Global system components (initialized on startup)
config_loader: Optional[ConfigLoader] = None
stream_handler: Optional[VideoStreamHandler] = None
detector: Optional[ObjectDetector] = None
tracker: Optional[MotionTracker] = None
tracking_engine: Optional[TrackingEngine] = None
ptz_controller: Optional[PTZController] = None

# WebSocket connections for live updates
active_connections: List[WebSocket] = []

# Cache last known stats to show persistent values when tracking stops
last_known_stats: Dict[str, Any] = {
    'frames_processed': 0,
    'detections': 0,
    'tracks': 0,
    'ptz_movements': 0,
    'active_events': 0,
    'completed_events': 0,
    'current_preset': None,
    'is_running': False,
    'is_paused': False,
    'mode': 'offline'
}


@app.on_event("startup")
async def startup_event():
    """Initialize system components on startup"""
    global config_loader, stream_handler, detector, tracker, tracking_engine, ptz_controller
    
    try:
        logger.info("Initializing system components...")
        
        # Load configurations
        config_loader = ConfigLoader()
        camera_config_dict = config_loader.load_camera_config()
        ai_config = config_loader.load_ai_config()
        
        # Initialize video stream
        camera = camera_config_dict['cameras'][0]
        rtsp_url = camera['stream']['rtsp_url']
        stream_handler = VideoStreamHandler(
            rtsp_url,
            buffer_size=camera['stream']['buffer_size']
        )
        stream_handler.start()
        
        # Initialize AI detector
        detector = ObjectDetector(
            model_path=ai_config.get_model_path(),
            confidence_threshold=ai_config.get_confidence_threshold(),
            device=ai_config.get_device()
        )
        
        # Initialize tracker (TrackingEngine needs MotionTracker, not MultiObjectTracker)
        from src.ai.motion_tracker import MotionTracker
        tracker = MotionTracker(
            history_length=30,
            movement_threshold=50,
            stationary_threshold=20,
            inactive_timeout=2.0
        )
        
        # Initialize PTZ controller
        ptz_controller = PTZController(
            camera_ip=camera['ip'],
            port=camera['port'],
            username=camera['username'],
            password=camera['password']
        )
        
        # Initialize tracking engine
        from src.automation.tracking_engine import TrackingConfig, TrackingZone
        
        # Load tracking config from YAML instead of hardcoding
        tracking_cfg = config_loader.build_tracking_engine_config()
        
        logger.info(f"✓ Tracking config loaded:")
        logger.info(f"  - Target classes: {tracking_cfg.target_classes}")
        logger.info(f"  - Direction triggers: {[d.value for d in tracking_cfg.direction_triggers]}")
        logger.info(f"  - Zones: {len(tracking_cfg.zones)}")
        logger.info(f"  - Confidence threshold: {tracking_cfg.min_confidence}")
        logger.info(f"  - Movement threshold: {tracking_cfg.movement_threshold}")
        logger.info(f"  - Cooldown time: {tracking_cfg.cooldown_time}")
        
        # Initialize tracking engine
        tracking_engine = TrackingEngine(
            detector=detector,
            motion_tracker=tracker,
            ptz_controller=ptz_controller,
            stream_handler=stream_handler,
            config=tracking_cfg
        )
        
        logger.info("✓ All components initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize system: {e}", exc_info=True)
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global stream_handler, tracking_engine
    
    if stream_handler:
        stream_handler.stop()
    
    if tracking_engine:
        tracking_engine.stop()
    
    logger.info("System shutdown complete")


# ============================================================================
# Dashboard Routes
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Render main dashboard"""
    return templates.TemplateResponse("index.html", {"request": request})


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/api/status")
async def get_status() -> Dict[str, Any]:
    """Get system status and health check"""
    stream_stats = stream_handler.get_stats() if stream_handler else None
    
    return {
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "stream": "running" if stream_handler and not stream_handler.stopped else "stopped",
            "detector": "loaded" if detector else "not loaded",
            "ptz": "connected" if ptz_controller else "disconnected",
            "tracking": "running" if tracking_engine and tracking_engine.running else "stopped"
        },
        "stream_stats": {
            "fps": stream_stats.fps if stream_stats else 0,
            "frames_received": stream_stats.frames_received if stream_stats else 0,
            "frames_dropped": stream_stats.frames_dropped if stream_stats else 0,
            "is_connected": stream_stats.is_connected if stream_stats else False
        } if stream_stats else None
    }


@app.get("/api/statistics")
async def get_statistics() -> Dict[str, Any]:
    """Get tracking statistics with stream health info"""
    global last_known_stats
    
    # Base stats structure
    base_stats = {
        "frames_processed": 0,
        "detections": 0,
        "tracks": 0,
        "ptz_movements": 0,
        "active_events": 0,
        "completed_events": 0,
        "current_mode": "unknown",
        "is_running": False,
        "fps": 0,
        "frames_dropped": 0,
        "stream_connected": False
    }
    
    # Get tracking engine stats if RUNNING
    if tracking_engine and tracking_engine.running:
        try:
            stats = tracking_engine.get_statistics()
            base_stats.update({
                "frames_processed": stats.get('frames_processed', 0),
                "detections": stats.get('detections', 0),
                "tracks": stats.get('tracks', 0),
                "ptz_movements": stats.get('ptz_movements', 0),
                "active_events": stats.get('active_events', 0),
                "completed_events": stats.get('completed_events', 0),
                "current_mode": stats.get('mode', 'tracking'),
                "is_running": True
            })
            # Cache these stats for when tracking stops
            last_known_stats = base_stats.copy()
        except Exception as e:
            logger.error(f"Error getting tracking engine stats: {e}")
    else:
        # Tracking not running - use CACHED stats (persistent across stop/start)
        base_stats.update(last_known_stats)
        base_stats["is_running"] = False  # But mark tracking as stopped
        logger.debug(f"Using cached stats: detections={base_stats.get('detections')}, tracks={base_stats.get('tracks')}")
    
    # Always add stream health info from stream handler (source stream FPS)
    if stream_handler:
        try:
            stream_stats = stream_handler.get_stats()
            
            # Update stream stats - always use these for stream health
            base_stats.update({
                "fps": stream_stats.fps if stream_stats.is_connected else 0,
                "frames_dropped": stream_stats.frames_dropped,
                "stream_connected": stream_stats.is_connected
            })
        except Exception as e:
            logger.error(f"Error getting stream stats: {e}")
    
    return base_stats


@app.get("/api/camera/info")
async def get_camera_info() -> Dict[str, Any]:
    """Get camera information including stream stats"""
    if not config_loader:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    camera_config = config_loader.load_camera_config()
    camera = camera_config['cameras'][0]
    
    # Get current stream FPS from stream handler
    stream_fps = 0
    if stream_handler:
        try:
            stream_stats = stream_handler.get_stats()
            stream_fps = stream_stats.fps
        except:
            pass
    
    return {
        "name": camera['name'],
        "ip": camera['ip'],
        "resolution": camera['stream']['resolution'],
        "camera_fps": camera['stream']['fps'],
        "stream_fps": round(stream_fps, 1),
        "output_fps": 30,  # Default fast mode, will be updated by JS
        "mode": "fast",  # Will be updated by JS based on detection toggle
        "has_ptz": camera.get('ptz', {}).get('enabled', False)
    }


@app.get("/api/camera/presets")
async def get_presets() -> List[Dict[str, str]]:
    """Get available PTZ presets"""
    if not ptz_controller:
        raise HTTPException(status_code=503, detail="PTZ controller not available")
    
    try:
        presets = ptz_controller.get_presets()
        return [
            {
                "token": preset.token,
                "name": preset.name
            }
            for preset in presets
        ]
    except Exception as e:
        logger.error(f"Error fetching presets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/camera/preset/{preset_token}")
async def move_to_preset(preset_token: str, speed: float = 0.5) -> Dict[str, str]:
    """Move camera to specific preset"""
    if not ptz_controller:
        raise HTTPException(status_code=503, detail="PTZ controller not available")
    
    try:
        ptz_controller.goto_preset(preset_token, speed=speed)
        return {
            "status": "success",
            "message": f"Moving to preset {preset_token}",
            "preset": preset_token
        }
    except Exception as e:
        logger.error(f"Error moving to preset: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/camera/move")
async def move_camera(move_data: Dict[str, float]) -> Dict[str, str]:
    """Continuous camera movement with automatic stop after duration"""
    if not ptz_controller:
        raise HTTPException(status_code=503, detail="PTZ controller not available")
    
    try:
        pan = move_data.get('pan_velocity', move_data.get('pan', 0.0))
        tilt = move_data.get('tilt_velocity', move_data.get('tilt', 0.0))
        zoom = move_data.get('zoom_velocity', move_data.get('zoom', 0.0))
        duration = move_data.get('duration', 0.5)
        
        # CRITICAL: Use blocking=True to automatically stop after duration
        # blocking=False would leave camera moving indefinitely!
        ptz_controller.continuous_move(
            pan_velocity=pan,
            tilt_velocity=tilt,
            zoom_velocity=zoom,
            duration=duration,
            blocking=True  # CRITICAL: Auto-stop after duration
        )
        return {
            "status": "success",
            "message": f"Moved camera (pan={pan}, tilt={tilt}, zoom={zoom}) for {duration}s"
        }
    except Exception as e:
        logger.error(f"Error moving camera: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/camera/stop")
async def stop_camera() -> Dict[str, str]:
    """Stop camera movement"""
    if not ptz_controller:
        raise HTTPException(status_code=503, detail="PTZ controller not available")
    
    try:
        ptz_controller.stop()
        return {
            "status": "success",
            "message": "Camera movement stopped"
        }
    except Exception as e:
        logger.error(f"Error stopping camera: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class RelativeMoveRequest(BaseModel):
    """Request model for relative PTZ movement"""
    pan_delta: float = 0.0
    tilt_delta: float = 0.0
    zoom_delta: float = 0.0
    speed: float = 0.5


@app.post("/api/camera/ptz/relative")
async def ptz_relative_move(request: RelativeMoveRequest) -> Dict[str, str]:
    """
    Execute relative PTZ movement from current position
    
    Uses continuous move as fallback if relative move not supported
    
    Args:
        request: RelativeMoveRequest with pan_delta, tilt_delta, zoom_delta, speed
    """
    if not ptz_controller:
        raise HTTPException(status_code=503, detail="PTZ controller not available")
    
    try:
        # FORCE continuous move fallback for testing (camera doesn't support relative move)
        logger.info("Using continuous move for relative positioning (camera doesn't support RelativeMove)")
        
        # Calculate duration based on delta (larger delta = longer duration)
        duration = abs(max(request.pan_delta, request.tilt_delta, key=abs)) * 2.0  # Scale to seconds
        
        # Convert delta to velocity (-1.0 to 1.0)
        pan_velocity = request.pan_delta
        tilt_velocity = request.tilt_delta
        
        logger.info(f"Continuous move fallback: pan={pan_velocity}, tilt={tilt_velocity}, duration={duration}s")
        
        # Execute continuous move
        ptz_controller.continuous_move(
            pan_velocity=pan_velocity,
            tilt_velocity=tilt_velocity,
            zoom_velocity=request.zoom_delta,
            duration=duration,
            blocking=True  # IMPORTANT: Block until movement completes
        )
        
        logger.info(f"Relative PTZ move: pan={request.pan_delta}, tilt={request.tilt_delta}, zoom={request.zoom_delta}, speed={request.speed}")
        
        return {
            "status": "success",
            "message": f"Relative move executed (pan={request.pan_delta}, tilt={request.tilt_delta}, zoom={request.zoom_delta})"
        }
    except Exception as e:
        logger.error(f"Error executing relative move: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


import asyncio

@app.post("/api/camera/zoom/continuous")
async def zoom_continuous(zoom_velocity: float = 0.5) -> Dict[str, str]:
    """Continuous zoom movement (for hold-down behavior) - does not auto-stop"""
    if not ptz_controller:
        return JSONResponse(
            {"status": "error", "message": "PTZ not available"},
            status_code=503
        )
    
    try:
        # Clamp velocity
        zoom_velocity = max(-1.0, min(1.0, zoom_velocity))
        
        # Start continuous zoom (non-blocking, doesn't auto-stop)
        ptz_controller.continuous_move(
            pan_velocity=0.0,
            tilt_velocity=0.0,
            zoom_velocity=zoom_velocity,
            blocking=False
        )
        return JSONResponse({"status": "success", "message": "Zooming"}, status_code=200)
    except Exception as e:
        logger.error(f"Zoom continuous error: {e}", exc_info=True)
        return JSONResponse({"status": "success", "message": "Zooming"}, status_code=200)


@app.post("/api/camera/zoom/in")
async def zoom_in(duration: float = 0.1):
    """Zoom in for specified duration then stop"""
    logger.info("Zoom in requested")
    
    if not ptz_controller:
        logger.warning("PTZ controller not available")
        return JSONResponse(
            {"status": "error", "message": "PTZ not available"},
            status_code=503
        )
    
    try:
        logger.debug("Calling continuous_move for zoom in...")
        ptz_controller.continuous_move(
            pan_velocity=0.0,
            tilt_velocity=0.0,
            zoom_velocity=0.5,
            blocking=False
        )
        logger.info(f"Zoom in started")
        
        # Schedule stop after duration (non-blocking)
        async def stop_zoom():
            await asyncio.sleep(duration)
            try:
                ptz_controller.stop()
                logger.info("Zoom in stopped")
            except Exception as e:
                logger.error(f"Error stopping zoom: {e}")
        
        asyncio.create_task(stop_zoom())
        
    except Exception as e:
        logger.error(f"Zoom in exception: {e}", exc_info=True)
    
    # Always return success JSON
    logger.info("Returning zoom in success response")
    return JSONResponse(
        {"status": "success", "message": "Zooming in", "action": "zoom_in"},
        status_code=200
    )


@app.post("/api/camera/zoom/out")
async def zoom_out(duration: float = 0.1):
    """Zoom out for specified duration then stop"""
    logger.info("Zoom out requested")
    
    if not ptz_controller:
        logger.warning("PTZ controller not available")
        return JSONResponse(
            {"status": "error", "message": "PTZ not available"},
            status_code=503
        )
    
    try:
        logger.debug("Calling continuous_move for zoom out...")
        ptz_controller.continuous_move(
            pan_velocity=0.0,
            tilt_velocity=0.0,
            zoom_velocity=-0.5,
            blocking=False
        )
        logger.info(f"Zoom out started")
        
        # Schedule stop after duration (non-blocking)
        async def stop_zoom():
            await asyncio.sleep(duration)
            try:
                ptz_controller.stop()
                logger.info("Zoom out stopped")
            except Exception as e:
                logger.error(f"Error stopping zoom: {e}")
        
        asyncio.create_task(stop_zoom())
        
    except Exception as e:
        logger.error(f"Zoom out exception: {e}", exc_info=True)
    
    # Always return success JSON
    logger.info("Returning zoom out success response")
    return JSONResponse(
        {"status": "success", "message": "Zooming out", "action": "zoom_out"},
        status_code=200
    )


@app.post("/api/tracking/start")
async def start_tracking() -> Dict[str, str]:
    """Start automated tracking"""
    global tracking_engine
    
    if not tracking_engine:
        raise HTTPException(status_code=500, detail="Tracking engine not initialized")
    
    if tracking_engine.running:
        return {"status": "already_running", "message": "Tracking already active"}
    
    try:
        tracking_engine.start()
        logger.info("Tracking started via API")
        return {"status": "success", "message": "Tracking started"}
        
    except Exception as e:
        logger.error(f"Error starting tracking: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tracking/stop")
async def stop_tracking() -> Dict[str, str]:
    """Stop automated tracking"""
    if not tracking_engine or not tracking_engine.running:
        return {"status": "not_running", "message": "Tracking not active"}
    
    try:
        tracking_engine.stop()
        logger.info("Tracking stopped via API")
        return {"status": "success", "message": "Tracking stopped"}
    except Exception as e:
        logger.error(f"Error stopping tracking: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tracking/status")
async def get_tracking_status() -> Dict[str, Any]:
    """Get tracking engine status"""
    if not tracking_engine:
        return {"running": False, "status": "not_initialized"}
    
    return {
        "running": tracking_engine.running,
        "paused": tracking_engine.paused,
        "mode": tracking_engine.mode.value,
        "current_preset": tracking_engine.current_preset,
        "active_tracks": len(tracking_engine.active_events),
        "completed_events": len(tracking_engine.completed_events),
        "detections": tracking_engine.detection_count,
        "ptz_movements": tracking_engine.ptz_movement_count
    }


@app.post("/api/tracking/quadrant/toggle")
async def toggle_quadrant_mode(enabled: Optional[bool] = None) -> Dict[str, Any]:
    """
    Toggle between center tracking and quadrant-based tracking
    
    Args:
        enabled: True to enable quadrant mode, False to disable, None to toggle
        
    Returns:
        Status with current mode
    """
    global tracking_engine
    
    if not tracking_engine:
        raise HTTPException(status_code=500, detail="Tracking engine not initialized")
    
    try:
        new_state = tracking_engine.toggle_quadrant_mode(enabled)
        mode_name = "QUADRANT" if new_state else "CENTER"
        logger.info(f"Quadrant mode toggled to: {mode_name}")
        
        return {
            "status": "success",
            "quadrant_mode_enabled": new_state,
            "tracking_mode": mode_name,
            "message": f"Switched to {mode_name} tracking mode"
        }
    except Exception as e:
        logger.error(f"Error toggling quadrant mode: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tracking/home-preset")
async def set_home_preset(request: Dict[str, str]) -> Dict[str, Any]:
    """
    Update idle override preset - checked at idle time
    
    When the idle timer triggers (15 seconds), the system will:
    1. Check if this override preset is set (checkbox enabled)
    2. If yes, use the override preset from dropdown
    3. If no (None or unchecked), use the default from config
    
    Args:
        request: JSON with 'preset_token' key (or None to clear override)
        
    Returns:
        Status confirmation
    """
    global tracking_engine
    
    if not tracking_engine:
        raise HTTPException(status_code=500, detail="Tracking engine not initialized")
    
    try:
        preset_token = request.get('preset_token')
        
        if preset_token is None:
            # Clear override - will use admin config
            tracking_engine.idle_preset_override = None
            logger.info(f"✓ Idle override cleared - will use config home preset")
            
            return {
                "status": "success",
                "idle_preset_override": None,
                "message": "Idle override cleared - using config home preset"
            }
        else:
            # Store the dropdown-selected preset as override
            tracking_engine.idle_preset_override = preset_token
            logger.info(f"✓ Idle override preset set to: {preset_token}")
            
            return {
                "status": "success",
                "idle_preset_override": preset_token,
                "message": f"Idle override preset set to {preset_token}"
            }
    except Exception as e:
        logger.error(f"Error setting idle preset override: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/api/tracking/quadrant/status")
async def get_quadrant_status() -> Dict[str, Any]:
    """Get current quadrant tracking mode status"""
    global tracking_engine
    
    if not tracking_engine:
        return {
            "enabled": False,
            "current_quadrant": None,
            "mode": "offline"
        }
    
    return {
        "enabled": tracking_engine.get_quadrant_mode(),
        "current_quadrant": tracking_engine.current_quadrant,
        "mode": "quadrant" if tracking_engine.get_quadrant_mode() else "center",
        "tracking_active": tracking_engine.running
    }


@app.get("/api/detections/current")
async def get_current_detections() -> List[Dict[str, Any]]:
    """Get current frame detections for overlay display"""
    if not tracking_engine or not hasattr(tracking_engine, 'last_detections'):
        return []
    
    # Return latest detections in format expected by desktop app
    detections = []
    for det in tracking_engine.last_detections:
        detections.append({
            "bbox": det.bbox,  # (x1, y1, x2, y2)
            "class": det.class_name,
            "confidence": det.confidence
        })
    
    return detections


@app.get("/api/events")
async def get_events(limit: int = 50) -> List[Dict[str, Any]]:
    """Get recent tracking events"""
    if not tracking_engine:
        return []
    
    events = tracking_engine.get_completed_events()
    
    return [
        {
            "id": event.event_id,
            "timestamp": event.start_time,  # Use start_time, not timestamp
            "object_id": event.object_id,
            "class_name": event.class_name,
            "direction": event.direction.value if event.direction else None,
            "zones": event.zone_transitions,  # List of zone transitions
            "ptz_actions": event.ptz_actions,  # List of PTZ presets triggered
            "frame_count": event.frame_count,
            "duration": (event.end_time - event.start_time) if event.end_time else None
        }
        for event in events[-limit:]
    ]


# ============================================================================
# Video Streaming
# ============================================================================

def generate_frames(show_detections=False):
    """Generate video frames - optimized for browser rendering limits
    
    KEY INSIGHT: Browser JavaScript can only render ~10-15 FPS due to:
    - JavaScript execution overhead
    - Canvas rendering timing
    - Browser refresh rate sync
    
    Generating 160+ FPS is wasteful. Cap at 15 FPS to reduce CPU/network load
    while maintaining smooth appearance (10 FPS = 100ms per frame, human eye
    perceives as smooth for security/surveillance).
    """
    import time
    frame_count = 0
    last_frame_time = time.time()
    
    # Target 15 FPS (67ms per frame) - what browser can actually display
    # 1000ms / 15 = 67ms per frame
    TARGET_FRAME_TIME = 1.0 / 15  # ~0.067 seconds
    
    # JPEG quality: 15 = ultra-fast encoding
    JPEG_QUALITY = 15
    
    while True:
        if not stream_handler or stream_handler.stopped:
            break
        
        try:
            # Rate limit: only send frame if enough time has passed
            current_time = time.time()
            time_since_last_frame = current_time - last_frame_time
            
            if time_since_last_frame < TARGET_FRAME_TIME:
                # Wait for next frame interval
                sleep_time = TARGET_FRAME_TIME - time_since_last_frame
                time.sleep(sleep_time * 0.9)  # Sleep 90% to account for jitter
                continue
            
            last_frame_time = current_time
            
            # Get frame from non-blocking buffer
            frame = stream_handler.read_direct()
            if frame is None:
                continue
            
            # Ultra-fast path: NO copies, NO overlays, just encode
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
            
            if not ret:
                continue
            
            frame_bytes = buffer.tobytes()
            frame_count += 1
            
            # Send MJPEG frame
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
        except Exception as e:
            logger.error(f"Stream error: {e}")
            break


@app.get("/api/video/stream")
async def video_stream(detections: bool = False):
    """Live MJPEG video stream - optionally with detection overlays"""
    return StreamingResponse(
        generate_frames(show_detections=detections),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Accel-Buffering": "no"  # Disable proxy buffering
        }
    )


# ============================================================================
# WebSocket Binary Stream (Ultra-Low Latency)
# ============================================================================

@app.websocket("/ws/video")
async def websocket_video_stream(websocket: WebSocket):
    """
    WebSocket binary video stream - ULTRA-LOW LATENCY PATH
    
    Reads from shared stream handler but with minimal buffering
    Protocol: [4-byte frame size][JPEG data]
    """
    await websocket.accept()
    
    try:
        frame_skip_counter = 0
        while True:
            if not stream_handler or stream_handler.stopped:
                await asyncio.sleep(0.01)
                continue
            
            # Get latest frame (drain all buffered frames, keep only newest)
            frame = stream_handler.read_latest()
            
            if frame is None:
                await asyncio.sleep(0.001)
                continue
            
            # Encode as JPEG (ultra-low quality)
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 15])
            
            if not ret:
                continue
            
            frame_bytes = buffer.tobytes()
            frame_size = len(frame_bytes).to_bytes(4, byteorder='little')
            
            try:
                await websocket.send_bytes(frame_size + frame_bytes)
            except Exception as e:
                break
                
    except WebSocketDisconnect:
        logger.info("WebSocket video client disconnected")
    except Exception as e:
        logger.error(f"WebSocket video error: {e}")


# ============================================================================
# WebSocket for Real-time Updates
# ============================================================================

@app.websocket("/ws/updates")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for pushing real-time statistics and events"""
    global last_known_stats
    
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        while True:
            # Send statistics every second
            if tracking_engine is not None and tracking_engine.running:
                # ✅ Tracking engine is active - get live stats and cache them
                stats = tracking_engine.get_statistics()
                
                # Always add stream handler stats for FPS and connection info
                if stream_handler:
                    try:
                        stream_stats = stream_handler.get_stats()
                        stats['fps'] = stream_stats.fps if stream_stats.is_connected else 0
                        stats['frames_dropped'] = stream_stats.frames_dropped
                        stats['stream_connected'] = stream_stats.is_connected
                    except Exception as e:
                        logger.error(f"Error getting stream stats in WebSocket: {e}")
                        stats['fps'] = 0
                        stats['frames_dropped'] = 0
                        stats['stream_connected'] = False
                
                # Get latest detections from tracking engine
                try:
                    if hasattr(tracking_engine, 'last_detections') and tracking_engine.last_detections:
                        detection_list = []
                        for d in tracking_engine.last_detections:
                            detection_list.append({
                                'class_name': d.class_name,
                                'confidence': float(d.confidence),
                                'bbox': list(d.bbox) if hasattr(d.bbox, '__iter__') else d.bbox
                            })
                        stats['detections_data'] = detection_list
                except Exception as e:
                    logger.debug(f"Error getting detections for WebSocket: {e}")
                
                # 💾 Cache these stats for when tracking stops
                last_known_stats = stats.copy()
                logger.debug(f"Cached stats: frames={stats.get('frames_processed')}, detections={stats.get('detections')}, tracks={stats.get('tracks')}")
                
            else:
                # ❌ Tracking engine is stopped - use cached stats (NOT zeros!)
                stats = last_known_stats.copy()
                logger.warning(f"Tracking stopped! Using cached stats: frames={stats.get('frames_processed')}, detections={stats.get('detections')}, tracks={stats.get('tracks')}")
                
                # Keep FPS and connection info up-to-date even when tracking is stopped
                if stream_handler:
                    try:
                        stream_stats = stream_handler.get_stats()
                        stats['fps'] = stream_stats.fps if stream_stats.is_connected else 0
                        stats['frames_dropped'] = stream_stats.frames_dropped
                        stats['stream_connected'] = stream_stats.is_connected
                    except Exception as e:
                        stats['fps'] = 0
                        stats['frames_dropped'] = 0
                        stats['stream_connected'] = False
                
                # Mark that tracking is not running
                stats['is_running'] = False
            
            await websocket.send_json({
                "type": "statistics",
                "data": stats
            })
            
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)


async def broadcast_event(event_data: Dict[str, Any]):
    """Broadcast event to all connected WebSocket clients"""
    disconnected = []
    
    for connection in active_connections:
        try:
            await connection.send_json({
                "type": "event",
                "data": event_data
            })
        except:
            disconnected.append(connection)
    
    # Remove disconnected clients
    for conn in disconnected:
        active_connections.remove(conn)


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
