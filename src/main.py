"""
Security Camera AI Tracking System - Main Application
Coordinates object detection, motion tracking, and PTZ camera control
"""

import os
import sys
import time
import argparse
import logging
from pathlib import Path
from typing import Optional, List
import cv2

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.camera.ptz_controller import PTZController
from src.ai.object_detector import ObjectDetector
from src.ai.motion_tracker import MotionTracker, MultiObjectTracker, Direction
from src.video.stream_handler import VideoStreamHandler
from src.automation.tracking_engine import TrackingEngine, TrackingConfig, TrackingZone, TrackingMode
from src.utils.config_loader import ConfigLoader


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    """
    Setup logging configuration
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional log file path
        
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger("SecurityCamera")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    simple_formatter = logging.Formatter('%(levelname)s - %(message)s')
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        # Create logs directory if it doesn't exist
        log_dir = Path(log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
    
    return logger


def initialize_components(config_loader: ConfigLoader, logger: logging.Logger) -> dict:
    """
    Initialize all system components from configuration
    
    Args:
        config_loader: Configuration loader instance
        logger: Logger instance
        
    Returns:
        Dictionary containing initialized components
    """
    logger.info("Initializing system components...")
    
    # Load configurations
    camera_config = config_loader.load_camera_config()
    tracking_config = config_loader.load_tracking_config()
    ai_config = config_loader.load_ai_config()
    
    # Get enabled cameras
    cameras = config_loader.get_enabled_cameras()
    if not cameras:
        raise ValueError("No cameras enabled in configuration")
    
    # Use first enabled camera
    camera = cameras[0]
    logger.info(f"Using camera: {camera.name} ({camera.id})")
    logger.info(f"  IP: {camera.ip}:{camera.port}")
    logger.info(f"  RTSP: {camera.get_rtsp_url()}")
    
    # Initialize PTZ controller
    logger.info("Initializing PTZ controller...")
    ptz_controller = PTZController(
        camera_ip=camera.ip,
        port=camera.port,
        username=camera.username,
        password=camera.password
    )
    
    # Test PTZ connection
    try:
        status = ptz_controller.get_status()
        logger.info(f"✓ PTZ controller connected")
    except Exception as e:
        logger.warning(f"PTZ controller connection failed: {e}")
        logger.warning("Continuing without PTZ control...")
    
    # Initialize video stream
    logger.info("Initializing video stream...")
    rtsp_url = camera.get_rtsp_url()
    buffer_size = camera.stream.get('buffer_size', 30)
    
    stream = VideoStreamHandler(rtsp_url, buffer_size=buffer_size)
    
    try:
        stream.start()
        logger.info(f"✓ Video stream started: {rtsp_url}")
    except Exception as e:
        logger.error(f"Failed to start video stream: {e}")
        raise
    
    # Initialize object detector
    logger.info("Initializing AI object detector...")
    model_path = ai_config.get_model_path()
    device = ai_config.get_device()
    confidence = ai_config.get_confidence_threshold()
    
    detector = ObjectDetector(
        model_path=model_path,
        device=device,
        confidence_threshold=confidence
    )
    
    logger.info(f"✓ Object detector loaded: {model_path}")
    logger.info(f"  Device: {device}")
    logger.info(f"  Confidence threshold: {confidence}")
    
    # Initialize motion tracker
    logger.info("Initializing motion tracker...")
    history_length = tracking_config.motion.get('history_length', 30)
    movement_threshold = tracking_config.motion.get('movement_threshold', 50)
    
    motion_tracker = MotionTracker(
        history_length=history_length,
        movement_threshold=movement_threshold
    )
    
    logger.info(f"✓ Motion tracker initialized")
    
    # Build tracking configuration
    logger.info("Building tracking configuration...")
    tracking_zones = []
    
    for zone_config in tracking_config.zones:
        zone = TrackingZone(
            name=zone_config['name'],
            x_range=tuple(zone_config['x_range']),
            y_range=tuple(zone_config['y_range']),
            preset=zone_config['preset'],
            priority=zone_config.get('priority', 1)
        )
        tracking_zones.append(zone)
        logger.info(f"  Zone: {zone.name} -> Preset {zone.preset}")
    
    # Direction triggers
    direction_triggers = {}
    for direction_name, trigger_config in tracking_config.direction_triggers.items():
        if trigger_config.get('enabled', False):
            direction_triggers[direction_name] = trigger_config
            logger.info(f"  Trigger: {direction_name} -> {trigger_config.get('target_zones', [])}")
    
    # Create TrackingConfig
    tracking_cfg = TrackingConfig(
        zones=tracking_zones,
        target_classes=tracking_config.target_classes,
        min_confidence=tracking_config.detection.get('min_confidence', 0.6),
        movement_threshold=movement_threshold,
        cooldown_time=tracking_config.ptz.get('cooldown_time', 3.0),
        direction_triggers=direction_triggers,
        mode=TrackingMode[tracking_config.mode.upper()]
    )
    
    # Initialize tracking engine
    logger.info("Initializing tracking engine...")
    
    tracking_engine = TrackingEngine(
        detector=detector,
        ptz_controller=ptz_controller,
        motion_tracker=motion_tracker,
        config=tracking_cfg
    )
    
    logger.info(f"✓ Tracking engine initialized")
    logger.info(f"  Mode: {tracking_config.mode}")
    logger.info(f"  Target classes: {', '.join(tracking_config.target_classes)}")
    logger.info(f"  Zones: {len(tracking_zones)}")
    
    return {
        'camera': camera,
        'ptz_controller': ptz_controller,
        'stream': stream,
        'detector': detector,
        'motion_tracker': motion_tracker,
        'tracking_engine': tracking_engine,
        'tracking_config': tracking_cfg,
        'global_settings': config_loader.get_global_settings()
    }


def run_tracking_system(
    components: dict,
    logger: logging.Logger,
    display_video: bool = False,
    duration: Optional[int] = None
) -> None:
    """
    Run the main tracking system loop
    
    Args:
        components: Dictionary of initialized components
        logger: Logger instance
        display_video: Whether to display video window
        duration: Optional duration in seconds (None = run indefinitely)
    """
    stream = components['stream']
    tracking_engine = components['tracking_engine']
    global_settings = components['global_settings']
    
    # Start tracking engine
    tracking_engine.start()
    logger.info("=" * 60)
    logger.info("TRACKING SYSTEM STARTED")
    logger.info("=" * 60)
    logger.info("Press 'q' to quit, 'p' to pause/resume, 's' for stats")
    
    start_time = time.time()
    frame_count = 0
    last_stats_time = start_time
    stats_interval = 10  # Print stats every 10 seconds
    
    process_every_n = global_settings.get('process_every_n_frames', 2)
    
    try:
        while True:
            # Check duration
            if duration and (time.time() - start_time) > duration:
                logger.info(f"Duration limit reached ({duration}s)")
                break
            
            # Read frame
            try:
                frame = stream.read()
            except Exception as e:
                logger.error(f"Failed to read frame: {e}")
                time.sleep(1)
                continue
            
            frame_count += 1
            
            # Process every Nth frame
            if frame_count % process_every_n == 0:
                tracking_engine.process_frame(frame)
            
            # Display video (optional)
            if display_video:
                # Draw detections and tracking info on frame
                display_frame = frame.copy()
                
                # Get latest events
                if tracking_engine.events:
                    latest = tracking_engine.events[-1]
                    
                    # Draw detection boxes
                    for detection in latest.detections:
                        x1, y1, x2, y2 = detection.bbox
                        cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        
                        # Draw label
                        label = f"{detection.class_name} {detection.confidence:.2f}"
                        cv2.putText(
                            display_frame, label, (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2
                        )
                    
                    # Draw zone boundaries
                    h, w = frame.shape[:2]
                    for zone in tracking_engine.config.zones:
                        x1 = int(zone.x_range[0] * w)
                        x2 = int(zone.x_range[1] * w)
                        y1 = int(zone.y_range[0] * h)
                        y2 = int(zone.y_range[1] * h)
                        
                        cv2.rectangle(display_frame, (x1, y1), (x2, y2), (255, 0, 0), 1)
                        cv2.putText(
                            display_frame, zone.name, (x1 + 5, y1 + 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1
                        )
                
                # Show frame
                cv2.imshow('Security Camera Tracking', display_frame)
                
                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q'):
                    logger.info("Quit requested by user")
                    break
                elif key == ord('p'):
                    if tracking_engine.is_paused:
                        tracking_engine.resume()
                        logger.info("Tracking resumed")
                    else:
                        tracking_engine.pause()
                        logger.info("Tracking paused")
                elif key == ord('s'):
                    print_statistics(tracking_engine, logger)
            
            # Print periodic statistics
            if time.time() - last_stats_time >= stats_interval:
                print_statistics(tracking_engine, logger)
                last_stats_time = time.time()
    
    except KeyboardInterrupt:
        logger.info("\nShutdown requested by user (Ctrl+C)")
    
    finally:
        # Cleanup
        logger.info("Shutting down tracking system...")
        
        tracking_engine.stop()
        stream.stop()
        
        if display_video:
            cv2.destroyAllWindows()
        
        # Final statistics
        logger.info("\n" + "=" * 60)
        logger.info("FINAL STATISTICS")
        logger.info("=" * 60)
        print_statistics(tracking_engine, logger)
        
        elapsed_time = time.time() - start_time
        logger.info(f"Total runtime: {elapsed_time:.1f} seconds")
        logger.info(f"Total frames: {frame_count}")
        logger.info(f"Average FPS: {frame_count / elapsed_time:.1f}")
        
        logger.info("\n✓ System shutdown complete")


def print_statistics(tracking_engine: TrackingEngine, logger: logging.Logger) -> None:
    """Print tracking statistics"""
    stats = tracking_engine.get_statistics()
    
    logger.info("\nTracking Statistics:")
    logger.info(f"  Frames processed: {stats['frames_processed']}")
    logger.info(f"  Total detections: {stats['total_detections']}")
    logger.info(f"  Total tracks: {stats['total_tracks']}")
    logger.info(f"  PTZ movements: {stats['ptz_movements']}")
    logger.info(f"  Events recorded: {len(tracking_engine.events)}")
    
    if stats['frames_processed'] > 0:
        logger.info(f"  Avg detections/frame: {stats['total_detections'] / stats['frames_processed']:.2f}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Security Camera AI Tracking System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default config
  python src/main.py
  
  # Run with custom config directory
  python src/main.py --config-dir config/
  
  # Display video window
  python src/main.py --display
  
  # Run for 60 seconds
  python src/main.py --duration 60
  
  # Debug mode with verbose logging
  python src/main.py --log-level DEBUG --display
        """
    )
    
    parser.add_argument(
        '--config-dir',
        type=str,
        default='config',
        help='Configuration directory (default: config)'
    )
    
    parser.add_argument(
        '--display',
        action='store_true',
        help='Display video window with tracking visualization'
    )
    
    parser.add_argument(
        '--duration',
        type=int,
        default=None,
        help='Run duration in seconds (default: run indefinitely)'
    )
    
    parser.add_argument(
        '--log-level',
        type=str,
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--log-file',
        type=str,
        default='logs/tracking.log',
        help='Log file path (default: logs/tracking.log)'
    )
    
    parser.add_argument(
        '--no-ptz',
        action='store_true',
        help='Disable PTZ camera control (detection only)'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging(args.log_level, args.log_file)
    
    logger.info("=" * 60)
    logger.info("SECURITY CAMERA AI TRACKING SYSTEM")
    logger.info("=" * 60)
    logger.info(f"Configuration directory: {args.config_dir}")
    logger.info(f"Display video: {args.display}")
    logger.info(f"Log level: {args.log_level}")
    
    try:
        # Load configuration
        logger.info("\nLoading configuration...")
        config_loader = ConfigLoader(args.config_dir)
        
        # Validate configuration
        if not config_loader.validate_config():
            logger.error("Configuration validation failed")
            sys.exit(1)
        
        # Initialize components
        components = initialize_components(config_loader, logger)
        
        # Disable PTZ if requested
        if args.no_ptz:
            logger.info("PTZ control disabled by user")
            components['tracking_engine'].config.mode = TrackingMode.MANUAL
        
        # Run tracking system
        run_tracking_system(
            components=components,
            logger=logger,
            display_video=args.display,
            duration=args.duration
        )
        
        sys.exit(0)
        
    except FileNotFoundError as e:
        logger.error(f"Configuration file not found: {e}")
        logger.error("Make sure configuration files exist in the config/ directory")
        sys.exit(1)
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
        
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
