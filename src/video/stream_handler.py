"""
Video Stream Handler

Captures video streams from IP cameras (RTSP/HTTP) with threaded buffering.
Handles stream reconnection, frame buffering, and provides clean API for frame retrieval.

Example:
    from src.video.stream_handler import VideoStreamHandler
    
    # Start stream
    stream = VideoStreamHandler(
        rtsp_url="rtsp://admin:password@192.168.1.100:554/stream1"
    ).start()
    
    # Read frames
    while True:
        frame = stream.read()
        if frame is not None:
            # Process frame
            cv2.imshow('Stream', frame)
"""

import cv2
import logging
import time
import threading
from queue import Queue, Empty
from typing import Optional, Tuple
from dataclasses import dataclass
from pathlib import Path


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class StreamStats:
    """
    Statistics for video stream
    
    Attributes:
        frames_received: Total frames received from stream
        frames_dropped: Frames dropped due to full buffer
        fps: Current frames per second
        resolution: (width, height) of stream
        is_connected: Whether stream is currently connected
        reconnect_attempts: Number of reconnection attempts
        last_frame_time: Timestamp of last received frame
    """
    frames_received: int = 0
    frames_dropped: int = 0
    fps: float = 0.0
    resolution: Tuple[int, int] = (0, 0)
    is_connected: bool = False
    reconnect_attempts: int = 0
    last_frame_time: float = 0.0


class VideoStreamHandler:
    """
    Handle video stream from IP camera with threading
    
    Runs capture in background thread and maintains frame buffer.
    Automatically handles reconnection on stream loss.
    """
    
    def __init__(
        self,
        stream_url: str,
        buffer_size: int = 30,
        reconnect: bool = True,
        reconnect_delay: float = 5.0,
        max_reconnect_attempts: int = -1,
        name: str = "Stream"
    ):
        """
        Initialize video stream handler
        
        Args:
            stream_url: RTSP, HTTP, or file path URL
                       Examples:
                       - rtsp://username:password@192.168.1.100:554/stream1
                       - http://192.168.1.100/video.mjpeg
                       - /path/to/video.mp4
            buffer_size: Maximum frames to buffer (older frames dropped)
            reconnect: Automatically reconnect on stream loss
            reconnect_delay: Seconds to wait between reconnection attempts
            max_reconnect_attempts: Max reconnects (-1 = unlimited)
            name: Name for logging purposes
        """
        self.stream_url = stream_url
        self.buffer_size = buffer_size
        self.reconnect_enabled = reconnect
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_attempts = max_reconnect_attempts
        self.name = name
        
        # Stream capture
        self.capture: Optional[cv2.VideoCapture] = None
        self.frame_queue: Queue = Queue(maxsize=buffer_size)
        
        # Thread control
        self.stopped = False
        self.thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()
        
        # Statistics
        self.stats = StreamStats()
        
        logger.info(f"VideoStreamHandler '{name}' initialized for {stream_url}")
    
    def start(self) -> 'VideoStreamHandler':
        """
        Start video capture in background thread
        
        Returns:
            Self for chaining
            
        Raises:
            RuntimeError: If stream cannot be opened
        """
        logger.info(f"Starting stream '{self.name}'...")
        
        # Open stream
        if not self._connect():
            raise RuntimeError(f"Failed to open stream: {self.stream_url}")
        
        # Start capture thread
        self.stopped = False
        self.thread = threading.Thread(target=self._update, daemon=True)
        self.thread.start()
        
        logger.info(f"✓ Stream '{self.name}' started")
        
        return self
    
    def _connect(self) -> bool:
        """
        Connect to video stream
        
        Returns:
            True if connection successful
        """
        try:
            self.capture = cv2.VideoCapture(self.stream_url)
            
            if not self.capture.isOpened():
                logger.error(f"Failed to open stream: {self.stream_url}")
                return False
            
            # Get stream properties
            width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = self.capture.get(cv2.CAP_PROP_FPS)
            
            with self.lock:
                self.stats.resolution = (width, height)
                self.stats.fps = fps if fps > 0 else 30.0  # Default if unknown
                self.stats.is_connected = True
            
            logger.info(
                f"✓ Connected to stream: {width}x{height} @ {fps:.1f} FPS"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False
    
    def _update(self) -> None:
        """
        Continuously read frames from stream (runs in background thread)
        """
        fps_counter = 0
        fps_start_time = time.time()
        
        while not self.stopped:
            # Check if capture is valid
            if self.capture is None or not self.capture.isOpened():
                logger.warning(f"Stream '{self.name}' disconnected")
                
                with self.lock:
                    self.stats.is_connected = False
                    self.stats.fps = 0.0  # Reset FPS when disconnected
                
                # Try to reconnect
                if self.reconnect_enabled:
                    if self._should_reconnect():
                        logger.info(
                            f"Reconnecting to '{self.name}' "
                            f"(attempt {self.stats.reconnect_attempts + 1})..."
                        )
                        
                        with self.lock:
                            self.stats.reconnect_attempts += 1
                        
                        if self._connect():
                            logger.info(f"✓ Reconnected to '{self.name}'")
                            continue
                        else:
                            time.sleep(self.reconnect_delay)
                            continue
                    else:
                        logger.error(
                            f"Max reconnection attempts reached for '{self.name}'"
                        )
                        break
                else:
                    break
            
            # Read frame
            try:
                ret, frame = self.capture.read()
                
                if not ret:
                    logger.warning(f"Failed to read frame from '{self.name}'")
                    
                    # Release capture to trigger reconnection
                    if self.capture:
                        self.capture.release()
                        self.capture = None
                    
                    continue
                
                # Update statistics
                current_time = time.time()
                
                with self.lock:
                    self.stats.frames_received += 1
                    self.stats.last_frame_time = current_time
                
                # Calculate FPS
                fps_counter += 1
                fps_elapsed = current_time - fps_start_time
                
                if fps_elapsed >= 1.0:
                    with self.lock:
                        self.stats.fps = fps_counter / fps_elapsed
                    
                    fps_counter = 0
                    fps_start_time = current_time
                
                # Add frame to queue
                if not self.frame_queue.full():
                    self.frame_queue.put(frame)
                else:
                    # Drop oldest frame and add new one
                    try:
                        self.frame_queue.get_nowait()
                        
                        with self.lock:
                            self.stats.frames_dropped += 1
                        
                    except Empty:
                        pass
                    
                    self.frame_queue.put(frame)
                
            except Exception as e:
                logger.error(f"Error reading frame from '{self.name}': {e}")
                time.sleep(0.1)
    
    def _should_reconnect(self) -> bool:
        """
        Check if reconnection should be attempted
        
        Returns:
            True if should attempt reconnect
        """
        if self.max_reconnect_attempts < 0:
            return True  # Unlimited reconnects
        
        return self.stats.reconnect_attempts < self.max_reconnect_attempts
    
    def read(self, timeout: float = 1.0) -> Optional[cv2.Mat]:
        """
        Read latest frame from stream
        
        Args:
            timeout: Maximum seconds to wait for frame
            
        Returns:
            OpenCV BGR image or None if no frame available
        """
        try:
            frame = self.frame_queue.get(timeout=timeout)
            return frame
        except Empty:
            return None
    
    def read_latest(self) -> Optional[cv2.Mat]:
        """
        Read latest frame and discard any older buffered frames
        
        Returns:
            Most recent frame or None
        """
        frame = None
        
        # Clear queue and get most recent frame
        while not self.frame_queue.empty():
            try:
                frame = self.frame_queue.get_nowait()
            except Empty:
                break
        
        return frame
    
    def is_opened(self) -> bool:
        """
        Check if stream is currently connected
        
        Returns:
            True if connected and receiving frames
        """
        with self.lock:
            return self.stats.is_connected
    
    def get_stats(self) -> StreamStats:
        """
        Get stream statistics
        
        Returns:
            Copy of current StreamStats
        """
        with self.lock:
            return StreamStats(
                frames_received=self.stats.frames_received,
                frames_dropped=self.stats.frames_dropped,
                fps=self.stats.fps,
                resolution=self.stats.resolution,
                is_connected=self.stats.is_connected,
                reconnect_attempts=self.stats.reconnect_attempts,
                last_frame_time=self.stats.last_frame_time
            )
    
    def get_resolution(self) -> Tuple[int, int]:
        """
        Get stream resolution
        
        Returns:
            (width, height) tuple
        """
        with self.lock:
            return self.stats.resolution
    
    def get_fps(self) -> float:
        """
        Get current frames per second
        
        Returns:
            FPS value
        """
        with self.lock:
            return self.stats.fps
    
    def stop(self) -> None:
        """
        Stop stream capture and release resources
        """
        logger.info(f"Stopping stream '{self.name}'...")
        
        self.stopped = True
        
        # Wait for thread to finish
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        
        # Release capture
        if self.capture:
            self.capture.release()
            self.capture = None
        
        # Clear queue
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except Empty:
                break
        
        with self.lock:
            self.stats.is_connected = False
        
        logger.info(f"✓ Stream '{self.name}' stopped")
    
    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()
    
    def __repr__(self) -> str:
        """String representation"""
        stats = self.get_stats()
        width, height = stats.resolution
        
        return (
            f"VideoStreamHandler('{self.name}', "
            f"{width}x{height}, {stats.fps:.1f} FPS, "
            f"connected={stats.is_connected})"
        )


class MultiStreamHandler:
    """
    Manage multiple video streams simultaneously
    
    Useful for multi-camera setups.
    """
    
    def __init__(self):
        """Initialize multi-stream handler"""
        self.streams: dict[str, VideoStreamHandler] = {}
        logger.info("MultiStreamHandler initialized")
    
    def add_stream(
        self,
        stream_id: str,
        stream_url: str,
        **kwargs
    ) -> VideoStreamHandler:
        """
        Add and start a new stream
        
        Args:
            stream_id: Unique identifier for stream
            stream_url: RTSP/HTTP URL
            **kwargs: Additional arguments for VideoStreamHandler
            
        Returns:
            VideoStreamHandler instance
        """
        if stream_id in self.streams:
            logger.warning(f"Stream '{stream_id}' already exists, stopping old stream")
            self.streams[stream_id].stop()
        
        stream = VideoStreamHandler(stream_url, name=stream_id, **kwargs)
        stream.start()
        
        self.streams[stream_id] = stream
        
        logger.info(f"Added stream '{stream_id}'")
        
        return stream
    
    def get_stream(self, stream_id: str) -> Optional[VideoStreamHandler]:
        """
        Get stream by ID
        
        Args:
            stream_id: Stream identifier
            
        Returns:
            VideoStreamHandler or None if not found
        """
        return self.streams.get(stream_id)
    
    def read_from(self, stream_id: str) -> Optional[cv2.Mat]:
        """
        Read frame from specific stream
        
        Args:
            stream_id: Stream identifier
            
        Returns:
            Frame or None
        """
        stream = self.get_stream(stream_id)
        
        if stream:
            return stream.read()
        
        return None
    
    def read_all(self) -> dict[str, Optional[cv2.Mat]]:
        """
        Read latest frame from all streams
        
        Returns:
            Dictionary mapping stream_id to frame
        """
        frames = {}
        
        for stream_id, stream in self.streams.items():
            frames[stream_id] = stream.read_latest()
        
        return frames
    
    def get_all_stats(self) -> dict[str, StreamStats]:
        """
        Get statistics for all streams
        
        Returns:
            Dictionary mapping stream_id to StreamStats
        """
        stats = {}
        
        for stream_id, stream in self.streams.items():
            stats[stream_id] = stream.get_stats()
        
        return stats
    
    def stop_stream(self, stream_id: str) -> None:
        """
        Stop specific stream
        
        Args:
            stream_id: Stream to stop
        """
        if stream_id in self.streams:
            self.streams[stream_id].stop()
            del self.streams[stream_id]
            logger.info(f"Stopped and removed stream '{stream_id}'")
    
    def stop_all(self) -> None:
        """Stop all streams"""
        logger.info("Stopping all streams...")
        
        for stream in self.streams.values():
            stream.stop()
        
        self.streams.clear()
        
        logger.info("✓ All streams stopped")
    
    def __len__(self) -> int:
        """Get number of active streams"""
        return len(self.streams)
    
    def __repr__(self) -> str:
        """String representation"""
        return f"MultiStreamHandler({len(self.streams)} streams)"
