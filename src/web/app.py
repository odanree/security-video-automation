"""
FastAPI Web Dashboard for Security Camera AI Tracker

Provides REST API endpoints for:
- Camera status and statistics
- Live video streaming
- PTZ control
- Detection events
- System configuration
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Any
import cv2
import asyncio
import json
from datetime import datetime
from pathlib import Path
import logging

# Import our tracking components
from src.video.stream_handler import VideoStreamHandler
from src.ai.object_detector import ObjectDetector
from src.ai.motion_tracker import MultiObjectTracker
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
tracker: Optional[MultiObjectTracker] = None
tracking_engine: Optional[TrackingEngine] = None
ptz_controller: Optional[PTZController] = None

# WebSocket connections for live updates
active_connections: List[WebSocket] = []


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
        
        # Initialize tracker
        tracker = MultiObjectTracker(
            max_distance=100.0,
            max_age=30
        )
        
        # Initialize PTZ controller
        ptz_controller = PTZController(
            camera_ip=camera['ip'],
            port=camera['port'],
            username=camera['username'],
            password=camera['password']
        )
        
        logger.info("✓ All components initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize system: {e}")
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
            "tracking": "running" if tracking_engine and tracking_engine.is_running else "stopped"
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
    """Get tracking statistics"""
    logger.info(f"Statistics requested - tracking_engine: {tracking_engine is not None}, stream_handler: {stream_handler is not None}")
    
    if tracking_engine:
        stats = tracking_engine.get_statistics()
        logger.info(f"Returning tracking engine stats: {stats}")
        return {
            "frames_processed": stats.get('frames_processed', 0),
            "detections": stats.get('detections', 0),
            "tracks": stats.get('tracks', 0),
            "ptz_movements": stats.get('ptz_movements', 0),
            "active_events": stats.get('active_events', 0),
            "completed_events": stats.get('completed_events', 0),
            "current_mode": stats.get('mode', 'unknown'),
            "is_running": stats.get('is_running', False)
        }
    
    # Use stream handler stats as fallback when tracking engine not running
    if stream_handler:
        try:
            stream_stats = stream_handler.get_stats()
            logger.info(f"Stream handler stats: frames_received={stream_stats.frames_received}, fps={stream_stats.fps}, stopped={stream_handler.stopped}")
            return {
                "frames_processed": stream_stats.frames_received,
                "detections": 0,
                "tracks": 0,
                "ptz_movements": 0,
                "active_events": 0,
                "completed_events": 0,
                "fps": stream_stats.fps,
                "frames_dropped": stream_stats.frames_dropped,
                "is_running": not stream_handler.stopped,
                "current_mode": "streaming"
            }
        except Exception as e:
            logger.error(f"Error getting stream stats: {e}")
    
    # Default fallback
    logger.warning("Returning default stats - no tracking engine or stream handler available")
    return {
        "frames_processed": 0,
        "detections": 0,
        "tracks": 0,
        "ptz_movements": 0,
        "active_events": 0,
        "completed_events": 0,
        "fps": 0,
        "is_running": False,
        "current_mode": "offline"
    }


@app.get("/api/camera/info")
async def get_camera_info() -> Dict[str, Any]:
    """Get camera information"""
    if not config_loader:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    camera_config = config_loader.load_camera_config()
    camera = camera_config['cameras'][0]
    
    return {
        "name": camera['name'],
        "ip": camera['ip'],
        "resolution": camera['stream']['resolution'],
        "fps": camera['stream']['fps'],
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
    """Continuous camera movement (non-blocking)"""
    if not ptz_controller:
        raise HTTPException(status_code=503, detail="PTZ controller not available")
    
    try:
        pan = move_data.get('pan_velocity', move_data.get('pan', 0.0))
        tilt = move_data.get('tilt_velocity', move_data.get('tilt', 0.0))
        duration = move_data.get('duration', 0.5)
        
        # Non-blocking movement - returns immediately
        ptz_controller.continuous_move(
            pan_velocity=pan,
            tilt_velocity=tilt,
            duration=duration,
            blocking=False  # Don't wait for movement to complete
        )
        return {
            "status": "success",
            "message": f"Moving camera (pan={pan}, tilt={tilt})"
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


@app.post("/api/tracking/start")
async def start_tracking() -> Dict[str, str]:
    """Start automated tracking"""
    global tracking_engine
    
    if tracking_engine and tracking_engine.is_running:
        return {"status": "already_running", "message": "Tracking already active"}
    
    try:
        # Initialize tracking engine if not exists
        if not tracking_engine:
            tracking_config = config_loader.load_tracking_config()
            tracking_engine = TrackingEngine(
                detector=detector,
                tracker=tracker,
                ptz_controller=ptz_controller,
                stream_handler=stream_handler,
                config=tracking_config
            )
        
        tracking_engine.start()
        return {"status": "success", "message": "Tracking started"}
        
    except Exception as e:
        logger.error(f"Error starting tracking: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tracking/stop")
async def stop_tracking() -> Dict[str, str]:
    """Stop automated tracking"""
    if not tracking_engine or not tracking_engine.is_running:
        return {"status": "not_running", "message": "Tracking not active"}
    
    try:
        tracking_engine.stop()
        return {"status": "success", "message": "Tracking stopped"}
    except Exception as e:
        logger.error(f"Error stopping tracking: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/events")
async def get_events(limit: int = 50) -> List[Dict[str, Any]]:
    """Get recent tracking events"""
    if not tracking_engine:
        return []
    
    events = tracking_engine.get_completed_events()
    
    return [
        {
            "id": event.event_id,
            "timestamp": event.timestamp.isoformat(),
            "class_name": event.detection.class_name,
            "confidence": event.detection.confidence,
            "direction": event.direction.value if event.direction else None,
            "zone": event.zone.name if event.zone else None,
            "action": event.action_taken
        }
        for event in events[-limit:]
    ]


# ============================================================================
# Video Streaming
# ============================================================================

def generate_frames(show_detections=False):
    """Generate video frames - optionally with detection overlays"""
    import time
    frame_count = 0
    last_detections = []
    last_frame_time = time.time()
    TARGET_FPS = 15 if show_detections else 30  # Lower FPS if processing
    JPEG_QUALITY = 70
    PROCESS_EVERY_N_FRAMES = 2 if show_detections else 1
    
    while True:
        if not stream_handler or stream_handler.stopped:
            logger.warning("Stream handler stopped or not available")
            break
        
        try:
            frame = stream_handler.read()
            
            if frame is None:
                time.sleep(0.0001)
                continue
            
            # Run detection if overlays are enabled
            if show_detections and detector and frame_count % PROCESS_EVERY_N_FRAMES == 0:
                last_detections = detector.detect(frame)
            
            # Draw cached detections if overlays are enabled
            if show_detections and detector and last_detections:
                frame = detector.draw_detections(frame, last_detections)
            
            # Encode frame as JPEG
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
            
            if not ret:
                logger.warning("Failed to encode frame")
                continue
            
            frame_bytes = buffer.tobytes()
            frame_count += 1
            
            # Yield frame in multipart format
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            # Adaptive frame rate
            elapsed = time.time() - last_frame_time
            target_delay = 1.0 / TARGET_FPS
            if elapsed < target_delay:
                time.sleep(target_delay - elapsed)
            last_frame_time = time.time()
            
        except Exception as e:
            logger.error(f"Error generating frame: {e}", exc_info=True)
            break


@app.get("/api/video/stream")
async def video_stream(detections: bool = False):
    """Live MJPEG video stream - optionally with detection overlays"""
    return StreamingResponse(
        generate_frames(show_detections=detections),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


# ============================================================================
# WebSocket for Real-time Updates
# ============================================================================

@app.websocket("/ws/updates")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for pushing real-time statistics and events"""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        while True:
            # Send statistics every second
            if tracking_engine:
                stats = tracking_engine.get_statistics()
            elif stream_handler:
                # Use stream handler stats as fallback
                try:
                    stream_stats = stream_handler.get_stats()
                    stats = {
                        'frames_processed': stream_stats.frames_received,
                        'detections': 0,
                        'tracks': 0,
                        'ptz_movements': 0,
                        'active_events': 0,
                        'completed_events': 0,
                        'current_preset': None,
                        'is_running': not stream_handler.stopped,
                        'is_paused': False,
                        'mode': 'streaming',
                        'fps': stream_stats.fps,
                        'frames_dropped': stream_stats.frames_dropped
                    }
                except Exception as e:
                    logger.error(f"Error getting stream stats in WebSocket: {e}")
                    stats = {
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
            else:
                # Send default stats if neither available
                stats = {
                    'frames_processed': 0,
                    'detections': 0,
                    'tracks': 0,
                    'ptz_movements': 0,
                    'active_events': 0,
                    'completed_events': 0,
                    'current_preset': None,
                    'is_running': False,
                    'is_paused': False,
                    'mode': 'idle'
                }
            
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
