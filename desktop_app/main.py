"""Main PyQt5 desktop application window"""

import sys
import time
import cv2
import numpy as np
from datetime import datetime
from threading import Thread, Lock
from queue import Queue
from typing import Optional

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QSlider, QComboBox, QGridLayout,
                             QScrollArea, QFrame, QSizePolicy, QApplication)
from PyQt5.QtGui import QImage, QPixmap, QFont
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread, QSettings
import requests
import websockets
import asyncio
import json


class StreamWorker(QThread):
    """Background thread for video stream capture"""
    frame_ready = pyqtSignal(np.ndarray)
    
    def __init__(self, rtsp_url: str):
        super().__init__()
        self.rtsp_url = rtsp_url
        self.running = False
        
    def run(self):
        """Capture frames from RTSP stream"""
        self.running = True
        cap = cv2.VideoCapture(self.rtsp_url)
        
        if not cap.isOpened():
            print(f"Failed to open stream: {self.rtsp_url}")
            return
        
        # Set buffer size to 1 for minimal latency
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        # Wait for RTSP stream to connect (camera may need time after reboot)
        time.sleep(2)
        
        frame_times = []
        frame_count = 0
        
        while self.running:
            ret, frame = cap.read()
            
            if not ret:
                print("Stream ended or error")
                time.sleep(0.5)  # Wait before retrying
                continue
            
            frame_count += 1
            
            # Emit every frame from camera (15 FPS) to get smooth display
            # Camera already has 15 FPS limit, so no need to skip
            
            # Calculate FPS
            current_time = time.time()
            frame_times.append(current_time)
            if len(frame_times) > 30:
                frame_times.pop(0)
            
            # Emit frame to GUI
            self.frame_ready.emit(frame)
            
            # OPTIMIZATION: Small sleep to prevent thread from hogging CPU
            time.sleep(0.01)  # 10ms sleep
        
        cap.release()
    
    def stop(self):
        """Stop the stream capture"""
        self.running = False


class StatsWorker(QThread):
    """Background thread for fetching statistics from backend"""
    stats_ready = pyqtSignal(dict)
    
    def __init__(self, backend_url: str):
        super().__init__()
        self.backend_url = backend_url
        self.running = False
    
    def run(self):
        """Fetch statistics periodically"""
        self.running = True
        backend_offline_shown = False
        
        while self.running:
            try:
                response = requests.get(f"{self.backend_url}/api/statistics", timeout=1)
                if response.status_code == 200:
                    stats = response.json()
                    self.stats_ready.emit(stats)
                    backend_offline_shown = False  # Reset error flag
                else:
                    if not backend_offline_shown:
                        print(f"Backend returned status {response.status_code}")
                        backend_offline_shown = True
            except requests.exceptions.ConnectionError:
                if not backend_offline_shown:
                    print(f"⚠️  Backend not running at {self.backend_url}")
                    print("   Stats and controls disabled. Start backend with: python start_dashboard.py")
                    backend_offline_shown = True
                # Emit empty stats to show N/A
                self.stats_ready.emit({"detections": "N/A", "tracks": "N/A", "events": "N/A", "backend_offline": True})
            except Exception as e:
                if not backend_offline_shown:
                    print(f"Stats fetch error: {e}")
                    backend_offline_shown = True
            
            time.sleep(2.0)  # Optimization: Update every 2s instead of 500ms (reduce API calls)
    
    def stop(self):
        """Stop fetching statistics"""
        self.running = False


class CameraTrackerApp(QMainWindow):
    """Main application window"""
    
    def __init__(self, camera_rtsp: str, backend_url: str = "http://localhost:8000"):
        super().__init__()
        
        self.camera_rtsp = camera_rtsp
        self.backend_url = backend_url
        
        # Initialize settings for persistent window geometry
        self.settings = QSettings("SecurityCameraTracker", "DesktopApp")
        
        # Debug: Print settings file location
        print(f"📁 Settings file: {self.settings.fileName()}")
        
        # Set window properties FIRST (before UI and geometry restore)
        self.setWindowTitle("Security Camera Tracker - Desktop")
        self.setWindowFlags(Qt.Window)
        self.setMinimumSize(1000, 700)
        
        # Initialize UI
        self.init_ui()
        self.setup_workers()
        
        # Restore window geometry LAST (after everything is set up)
        self.restore_window_geometry()
        
        # Setup auto-save timer for geometry (save every 2 seconds if changed)
        self.geometry_save_timer = QTimer()
        self.geometry_save_timer.timeout.connect(self.save_window_geometry)
        self.geometry_save_timer.start(2000)  # Save every 2 seconds
        
    def restore_window_geometry(self):
        """Restore window position and size from settings"""
        # Try to restore geometry from settings
        geometry = self.settings.value("window/geometry")
        
        if geometry:
            success = self.restoreGeometry(geometry)
            if success:
                print(f"✓ Restored window position and size from last session")
                print(f"  Position: {self.x()},{self.y()} | Size: {self.width()}×{self.height()}")
            else:
                print("✗ Failed to restore geometry, using defaults")
                self.resize(1600, 1000)
        else:
            # First time - use default size
            self.resize(1600, 1000)
            print("✓ Using default window size (first launch)")
    
    def save_window_geometry(self):
        """Save window position and size to settings"""
        geometry = self.saveGeometry()
        self.settings.setValue("window/geometry", geometry)
        self.settings.sync()  # Force write to disk immediately
        # Only print on manual close, not during auto-save
        # print(f"✓ Saved window position and size ({self.width()}×{self.height()} at {self.x()},{self.y()})")
        
    def init_ui(self):
        """Initialize UI components"""
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        layout = QHBoxLayout()
        
        # Left: Video display (full height, responsive)
        left_layout = QVBoxLayout()
        self.video_label = QLabel()
        self.video_label.setStyleSheet("background-color: black; border: 2px solid #555;")
        self.video_label.setMinimumSize(800, 600)  # Reasonable minimum
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # Expand both directions
        self.video_label.setScaledContents(False)  # Don't stretch - we'll scale manually with aspect ratio
        self.video_label.setAlignment(Qt.AlignCenter)  # Center the image
        left_layout.addWidget(self.video_label, 1)  # Stretch factor = 1
        
        # FPS and info label
        self.info_label = QLabel("FPS: -- | Resolution: -- | Status: Starting...")
        self.info_label.setStyleSheet("color: white; background-color: #333; padding: 5px;")
        self.info_label.setFont(QFont("Courier", 9))
        left_layout.addWidget(self.info_label)
        
        layout.addLayout(left_layout, 3)
        
        # Right: Controls panel with scroll area
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        right_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        right_scroll.setMinimumWidth(350)  # Ensure controls panel has minimum width
        right_scroll.setMaximumWidth(450)  # Limit maximum width for better layout
        
        # Enable mouse events for scroll area
        right_scroll.setFocusPolicy(Qt.StrongFocus)
        
        right_widget = QWidget()
        right_widget.setMinimumWidth(330)  # Ensure content fits
        right_layout = QVBoxLayout()
        right_widget.setLayout(right_layout)
        right_scroll.setWidget(right_widget)
        
        # Stats section
        stats_frame = QFrame()
        stats_frame.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 5px;")
        stats_layout = QVBoxLayout()
        
        stats_title = QLabel("📊 Statistics")
        stats_title.setFont(QFont("Arial", 12, QFont.Bold))
        stats_layout.addWidget(stats_title)
        
        self.stat_detections = QLabel("Detections: 0")
        self.stat_tracks = QLabel("Active Tracks: 0")
        self.stat_events = QLabel("Events: 0")
        self.stat_fps_display = QLabel("Stream FPS: --")  # Local FPS counter
        self.stat_fps_backend = QLabel("Backend FPS: --")
        
        stats_layout.addWidget(self.stat_detections)
        stats_layout.addWidget(self.stat_tracks)
        stats_layout.addWidget(self.stat_events)
        stats_layout.addWidget(self.stat_fps_display)
        stats_layout.addWidget(self.stat_fps_backend)
        
        stats_frame.setLayout(stats_layout)
        right_layout.addWidget(stats_frame)
        
        # Tracking control section
        tracking_frame = QFrame()
        tracking_frame.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 5px;")
        tracking_layout = QVBoxLayout()
        
        tracking_title = QLabel("🎯 Tracking Control")
        tracking_title.setFont(QFont("Arial", 12, QFont.Bold))
        tracking_layout.addWidget(tracking_title)
        
        # Style for buttons with hover effects
        button_style = """
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
                transform: scale(1.05);
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """
        
        stop_button_style = """
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #da190b;
                transform: scale(1.05);
            }
            QPushButton:pressed {
                background-color: #c41408;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """
        
        self.btn_start_tracking = QPushButton("▶️ Start Tracking")
        self.btn_start_tracking.setStyleSheet(button_style)
        self.btn_start_tracking.setMinimumHeight(40)
        self.btn_start_tracking.clicked.connect(self.start_tracking)
        tracking_layout.addWidget(self.btn_start_tracking)
        
        self.btn_stop_tracking = QPushButton("⏸️ Stop Tracking")
        self.btn_stop_tracking.setStyleSheet(stop_button_style)
        self.btn_stop_tracking.setMinimumHeight(40)
        self.btn_stop_tracking.clicked.connect(self.stop_tracking)
        self.btn_stop_tracking.setEnabled(False)
        tracking_layout.addWidget(self.btn_stop_tracking)
        
        self.tracking_status = QLabel("Status: Inactive")
        self.tracking_status.setFont(QFont("Courier", 10))
        tracking_layout.addWidget(self.tracking_status)
        
        # Overlay toggle button
        toggle_button_style = """
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: none;
                padding: 8px;
                font-size: 12px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
            QPushButton:pressed {
                background-color: #6A1B9A;
            }
        """
        
        self.btn_toggle_overlay = QPushButton("🔳 Toggle Detection Overlay")
        self.btn_toggle_overlay.setStyleSheet(toggle_button_style)
        self.btn_toggle_overlay.setMinimumHeight(35)
        self.btn_toggle_overlay.clicked.connect(self.toggle_overlay)
        tracking_layout.addWidget(self.btn_toggle_overlay)
        
        self.overlay_enabled = False
        self.overlay_status = QLabel("Overlay: OFF")
        self.overlay_status.setFont(QFont("Courier", 9))
        self.overlay_status.setStyleSheet("color: #666;")
        tracking_layout.addWidget(self.overlay_status)
        
        tracking_frame.setLayout(tracking_layout)
        right_layout.addWidget(tracking_frame)
        
        # PTZ Control section
        ptz_frame = QFrame()
        ptz_frame.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 5px;")
        ptz_layout = QVBoxLayout()
        
        ptz_title = QLabel("🎬 PTZ Control")
        ptz_title.setFont(QFont("Arial", 12, QFont.Bold))
        ptz_layout.addWidget(ptz_title)
        
        # Preset selector
        preset_label = QLabel("Camera Presets:")
        ptz_layout.addWidget(preset_label)
        
        self.preset_combo = QComboBox()
        self.preset_combo.addItem("Loading presets...")
        self.preset_combo.setStyleSheet("""
            QComboBox {
                padding: 5px;
                border: 1px solid #ccc;
                border-radius: 3px;
                background: white;
            }
        """)
        ptz_layout.addWidget(self.preset_combo)
        
        preset_button_style = """
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
            QPushButton:pressed {
                background-color: #0960a8;
            }
        """
        
        self.btn_goto_preset = QPushButton("Go to Preset")
        self.btn_goto_preset.setStyleSheet(preset_button_style)
        self.btn_goto_preset.setMinimumHeight(40)
        self.btn_goto_preset.clicked.connect(self.goto_preset)
        ptz_layout.addWidget(self.btn_goto_preset)
        
        # Speed control
        speed_label = QLabel("Movement Speed:")
        ptz_layout.addWidget(speed_label)
        
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(1)
        self.speed_slider.setMaximum(10)
        self.speed_slider.setValue(5)
        ptz_layout.addWidget(self.speed_slider)
        
        # Manual PTZ Controls
        ptz_manual_label = QLabel("Manual Control:")
        ptz_manual_label.setFont(QFont("Arial", 10, QFont.Bold))
        ptz_layout.addWidget(ptz_manual_label)
        
        # Pan/Tilt buttons in grid layout
        ptz_grid = QGridLayout()
        
        ptz_button_style = """
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 15px;
                font-size: 16px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """
        
        # Pan/Tilt directional buttons
        self.btn_up = QPushButton("▲")
        self.btn_up.setStyleSheet(ptz_button_style)
        self.btn_up.pressed.connect(lambda: self.manual_ptz_start('up'))
        self.btn_up.released.connect(self.manual_ptz_stop)
        ptz_grid.addWidget(self.btn_up, 0, 1)
        
        self.btn_left = QPushButton("◄")
        self.btn_left.setStyleSheet(ptz_button_style)
        self.btn_left.pressed.connect(lambda: self.manual_ptz_start('left'))
        self.btn_left.released.connect(self.manual_ptz_stop)
        ptz_grid.addWidget(self.btn_left, 1, 0)
        
        self.btn_home = QPushButton("⌂")
        self.btn_home.setStyleSheet(ptz_button_style.replace('#4CAF50', '#FF9800').replace('#45a049', '#e68900').replace('#3d8b40', '#cc7a00'))
        self.btn_home.clicked.connect(lambda: self.manual_ptz('home'))
        ptz_grid.addWidget(self.btn_home, 1, 1)
        
        self.btn_right = QPushButton("►")
        self.btn_right.setStyleSheet(ptz_button_style)
        self.btn_right.pressed.connect(lambda: self.manual_ptz_start('right'))
        self.btn_right.released.connect(self.manual_ptz_stop)
        ptz_grid.addWidget(self.btn_right, 1, 2)
        
        self.btn_down = QPushButton("▼")
        self.btn_down.setStyleSheet(ptz_button_style)
        self.btn_down.pressed.connect(lambda: self.manual_ptz_start('down'))
        self.btn_down.released.connect(self.manual_ptz_stop)
        ptz_grid.addWidget(self.btn_down, 2, 1)
        
        ptz_layout.addLayout(ptz_grid)
        
        # Zoom buttons
        zoom_layout = QHBoxLayout()
        
        self.btn_zoom_in = QPushButton("🔍 Zoom In")
        self.btn_zoom_in.setStyleSheet(ptz_button_style)
        self.btn_zoom_in.pressed.connect(lambda: self.manual_ptz_start('zoom_in'))
        self.btn_zoom_in.released.connect(self.manual_ptz_stop)
        zoom_layout.addWidget(self.btn_zoom_in)
        
        self.btn_zoom_out = QPushButton("🔍 Zoom Out")
        self.btn_zoom_out.setStyleSheet(ptz_button_style)
        self.btn_zoom_out.pressed.connect(lambda: self.manual_ptz_start('zoom_out'))
        self.btn_zoom_out.released.connect(self.manual_ptz_stop)
        zoom_layout.addWidget(self.btn_zoom_out)
        
        ptz_layout.addLayout(zoom_layout)
        
        ptz_frame.setLayout(ptz_layout)
        right_layout.addWidget(ptz_frame)
        
        # Spacer at bottom
        right_layout.addStretch()
        
        # Add scroll area to main layout instead of VBoxLayout
        layout.addWidget(right_scroll, 1)
        main_widget.setLayout(layout)
        
    def setup_workers(self):
        """Set up background threads"""
        # Video stream worker
        self.stream_worker = StreamWorker(self.camera_rtsp)
        self.stream_worker.frame_ready.connect(self.on_frame_received)
        self.stream_worker.start()
        
        # Stats worker
        self.stats_worker = StatsWorker(self.backend_url)
        self.stats_worker.stats_ready.connect(self.on_stats_received)
        self.stats_worker.start()
        
        # FPS timer
        self.fps_timer = QTimer()
        self.fps_timer.timeout.connect(self.update_fps_display)
        self.fps_timer.start(1000)  # Update every 1s (was 500ms) to reduce CPU
        
        # PTZ hold support - track which direction is currently held
        self.ptz_hold_direction = None
        self.ptz_hold_timer = QTimer()
        self.ptz_hold_timer.timeout.connect(self.ptz_hold_update)
        
        # Load presets
        self.load_presets()
        
        # Frame timing - use pre-allocated array for ring buffer (no append/pop overhead)
        self.frame_times = [0.0] * 60  # Ring buffer for 60 frames
        self.last_frame_time = time.time()
        
        # Detection overlay cache
        self.cached_detections = []
        self.last_detection_fetch = 0
        self.detection_fetch_interval = 1.0  # Fetch detections every 1 second (reduced from 0.5s for CPU)
        
        # Optimization: Frame skip counter and display resolution tracking
        self.frame_skip_counter = 0
        self.last_frame_h = 0
        self.last_frame_w = 0
    
    def on_frame_received(self, frame: np.ndarray):
        """Handle frame from video stream"""
        # Display all frames with minimal skipping for maximum smoothness
        # No frame skipping - render every frame that arrives
        self.frame_skip_counter += 1
        
        # Display all frames for maximum FPS (no frame skipping)
        # This renders every frame the camera sends
        skip_rate = 1
        if self.frame_skip_counter % skip_rate != 0:
            return  # Skip this frame
        
        # OPTIMIZATION: No color conversion when overlay disabled
        # PyQt5 can display BGR directly (will have slightly different colors but saves CPU)
        if self.overlay_enabled:
            # Copy frame for overlay modification
            display_frame = self.draw_detections_overlay(frame.copy())
            # Convert BGR to RGB only when drawing overlay
            display_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        else:
            # SKIP COLOR CONVERSION - PyQt5 displays BGR as RGB (saves 5-10% CPU)
            # This means colors will be slightly off but it's worth the CPU savings
            display_frame = frame
        
        # Track frame timing for FPS (optimize: ring buffer instead of append/pop)
        current_time = time.time()
        idx = self.frame_skip_counter % 60
        self.frame_times[idx] = current_time
        
        # OPTIMIZATION: Reuse QImage if size hasn't changed (avoid memory allocation)
        h, w = display_frame.shape[:2]
        
        if h != self.last_frame_h or w != self.last_frame_w:
            # Size changed - create new QImage
            bytes_per_line = w * 3 if len(display_frame.shape) == 3 else w
            qt_image = QImage(display_frame.data, w, h, bytes_per_line, 
                            QImage.Format_BGR888 if not self.overlay_enabled else QImage.Format_RGB888)
            self.last_frame_h = h
            self.last_frame_w = w
        else:
            # Size same - just create image from buffer
            bytes_per_line = w * 3 if len(display_frame.shape) == 3 else w
            qt_image = QImage(display_frame.data, w, h, bytes_per_line,
                            QImage.Format_BGR888 if not self.overlay_enabled else QImage.Format_RGB888)
        
        pixmap = QPixmap.fromImage(qt_image)
        
        # IMPORTANT: Draw overlay AFTER scaling for correct coordinate mapping
        # We need to know the final display scale before drawing boxes
        label_width = self.video_label.width()
        label_height = self.video_label.height()
        
        if label_width > 0 and label_height > 0:
            # Calculate scale factor from original to display size
            pixmap_width = pixmap.width()
            pixmap_height = pixmap.height()
            
            # Determine final scale (same logic as below)
            if pixmap_width > label_width or pixmap_height > label_height:
                # Need to scale down
                if pixmap_width / label_width > pixmap_height / label_height:
                    # Scale by width
                    final_scale = label_width / pixmap_width
                else:
                    # Scale by height
                    final_scale = label_height / pixmap_height
            else:
                final_scale = 1.0
            
            # Scale pixmap to fit within label while keeping aspect ratio
            scaled_pixmap = pixmap.scaledToWidth(label_width, Qt.SmoothTransformation) if pixmap.width() > 0 else pixmap
            
            # If scaled height exceeds label height, scale to height instead
            if scaled_pixmap.height() > label_height:
                scaled_pixmap = pixmap.scaledToHeight(label_height, Qt.SmoothTransformation)
            
            self.video_label.setPixmap(scaled_pixmap)
        else:
            # Label not ready yet, just set pixmap (will scale on resize)
            self.video_label.setPixmap(pixmap)
    
    def draw_detections_overlay(self, frame: np.ndarray) -> np.ndarray:
        """Draw detection boxes on frame (uses cached detections to avoid HTTP overhead).
        
        Important: Detections are drawn on the ORIGINAL frame (2560×1920) in the EXACT
        coordinates where they will appear. The frame is then displayed with aspect-ratio
        preservation, so boxes are always correctly positioned.
        """
        current_time = time.time()
        
        # Optimization: Only fetch detections every 1 second instead of 500ms
        if current_time - self.last_detection_fetch > self.detection_fetch_interval:
            try:
                # Non-blocking request with very short timeout
                response = requests.get(f"{self.backend_url}/api/detections/current", timeout=0.05)
                if response.status_code == 200:
                    data = response.json()
                    self.cached_detections = data if isinstance(data, list) else []
                    # Debug: Log detection fetch
                    if self.cached_detections:
                        print(f"[DETECTIONS] Fetched {len(self.cached_detections)} detections for overlay")
                self.last_detection_fetch = current_time
            except Exception as e:
                print(f"[ERROR] Detection fetch failed: {e}")
                pass  # Keep using old cached detections
        
        # Get current frame dimensions
        frame_height, frame_width = frame.shape[:2]
        
        # Desktop shows /11 (2560×1920), backend detects on /12 (800×600)
        # Scale coordinates UP from backend to display frame
        BACKEND_WIDTH, BACKEND_HEIGHT = 800, 600
        scale_x = frame_width / BACKEND_WIDTH   # 2560/800 = 3.2
        scale_y = frame_height / BACKEND_HEIGHT  # 1920/600 = 3.2
        
        # Color mapping for different classes
        colors = {
            'person': (0, 255, 0),      # Green
            'bicycle': (255, 165, 0),   # Orange
            'car': (0, 165, 255),       # Blue (BGR: Red=0, Green=165, Blue=255)
            'motorcycle': (255, 0, 255), # Magenta
            'truck': (255, 255, 0)      # Cyan
        }
        
        # Draw cached detections with proper scaling
        detections_drawn = 0
        if self.cached_detections:
            print(f"[DRAW] Drawing {len(self.cached_detections)} detection(s) on overlay")
        
        for det in self.cached_detections:
            try:
                x1, y1, x2, y2 = det['bbox']
                class_name = det['class']
                confidence = det['confidence']
                
                # Scale UP from backend (800×600) to display frame (2560×1920)
                x1 = int(x1 * scale_x)
                x2 = int(x2 * scale_x)
                y1 = int(y1 * scale_y)
                y2 = int(y2 * scale_y)
                
                # Ensure coordinates are in bounds
                x1 = max(0, min(x1, frame_width - 1))
                x2 = max(x1 + 1, min(x2, frame_width))
                y1 = max(0, min(y1, frame_height - 1))
                y2 = max(y1 + 1, min(y2, frame_height))
                
                if x2 <= x1 or y2 <= y1:
                    print(f"[SKIP] Invalid box: ({x1},{y1}) to ({x2},{y2})")
                    continue
                
                # Get color for this class
                color = colors.get(class_name, (0, 255, 0))  # Default to green
                
                # Draw bounding box rectangle with thickness 2
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                
                # Draw label text with semi-transparent background
                text = f"{class_name} {confidence:.2f}"
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.5
                font_thickness = 2
                
                # Get text size for background
                (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, font_thickness)
                
                # Place label above box
                label_x = x1
                label_y = max(25, y1 - 5)  # At least 25px from top
                
                # Draw semi-transparent background for label
                overlay = frame.copy()
                cv2.rectangle(overlay,
                            (label_x, label_y - text_height - 10),
                            (label_x + text_width + 5, label_y),
                            color, -1)
                cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
                
                # Draw white text on top
                cv2.putText(frame, text,
                          (label_x + 2, label_y - 5),
                          font, font_scale, (255, 255, 255), font_thickness)
                
                detections_drawn += 1
                
            except (KeyError, TypeError, ValueError, IndexError) as e:
                print(f"[ERROR] Could not draw detection {det}: {e}")
                continue
        
        if detections_drawn > 0:
            print(f"[SUCCESS] Drew {detections_drawn} detection box(es)")
        
        return frame
    
    def on_stats_received(self, stats: dict):
        """Handle statistics from backend"""
        # Check if backend is offline
        if stats.get('backend_offline'):
            self.stat_detections.setText("Detections: N/A (backend offline)")
            self.stat_tracks.setText("Active Tracks: N/A")
            self.stat_events.setText("Events: N/A")
            self.tracking_status.setText("Status: Backend Offline")
            self.tracking_status.setStyleSheet("color: red;")
            return
        
        # Try to load presets if combo still shows "Loading..."
        if self.preset_combo.count() == 1 and "Loading" in self.preset_combo.itemText(0):
            self.load_presets()
        
        # Normal stats display
        self.stat_detections.setText(f"Detections: {stats.get('detections', 0)}")
        self.stat_tracks.setText(f"Active Tracks: {stats.get('tracks', 0)}")
        self.stat_events.setText(f"Events: {stats.get('events', 0)}")
        self.tracking_status.setStyleSheet("color: black;")
        
        # Update tracking status
        if stats.get('tracking_active'):
            self.tracking_status.setText(f"Status: Active | Uptime: {stats.get('tracking_uptime', '00:00:00')}")
        else:
            self.tracking_status.setText("Status: Inactive")
    
    def update_fps_display(self):
        """Update FPS display - calculate from ring buffer"""
        # Find valid entries in ring buffer (those with non-zero timestamps)
        valid_times = [t for t in self.frame_times if t > 0]
        
        if len(valid_times) > 5:
            # Calculate FPS from oldest to newest timestamp in buffer
            time_span = valid_times[-1] - valid_times[0]
            if time_span > 0:
                fps = len(valid_times) / time_span
                # Account for frame skipping - multiply by skip rate for actual FPS
                skip_rate = 3 if self.overlay_enabled else 2
                actual_fps = fps * skip_rate
                
                self.info_label.setText(f"FPS: {actual_fps:.1f} | Frames: {self.frame_skip_counter} | Status: Running")
                # Also update in stats panel
                self.stat_fps_display.setText(f"Stream FPS: {actual_fps:.1f}")
        else:
            self.stat_fps_display.setText("Stream FPS: --")
    
    def toggle_overlay(self):
        """Toggle detection overlay on/off"""
        self.overlay_enabled = not self.overlay_enabled
        if self.overlay_enabled:
            self.overlay_status.setText("Overlay: ON")
            self.overlay_status.setStyleSheet("color: #4CAF50; font-weight: bold;")
            print("✓ Detection overlay enabled")
        else:
            self.overlay_status.setText("Overlay: OFF")
            self.overlay_status.setStyleSheet("color: #666;")
            print("✓ Detection overlay disabled")
    
    def start_tracking(self):
        """Start tracking"""
        try:
            print(f"Sending POST to {self.backend_url}/api/tracking/start")
            response = requests.post(f"{self.backend_url}/api/tracking/start", timeout=2)
            print(f"Response: {response.status_code} - {response.text}")
            if response.status_code == 200:
                self.btn_start_tracking.setEnabled(False)
                self.btn_stop_tracking.setEnabled(True)
                self.tracking_status.setText("Status: Starting...")
                print("✓ Tracking started successfully")
            else:
                self.tracking_status.setText(f"Error: {response.status_code}")
                print(f"✗ Failed to start tracking: {response.status_code}")
        except Exception as e:
            self.tracking_status.setText(f"Error: {e}")
            print(f"✗ Exception starting tracking: {e}")
    
    def stop_tracking(self):
        """Stop tracking"""
        try:
            response = requests.post(f"{self.backend_url}/api/tracking/stop", timeout=2)
            if response.status_code == 200:
                self.btn_start_tracking.setEnabled(True)
                self.btn_stop_tracking.setEnabled(False)
                self.tracking_status.setText("Status: Inactive")
        except Exception as e:
            self.tracking_status.setText(f"Error: {e}")
    
    def load_presets(self):
        """Load camera presets from backend"""
        try:
            response = requests.get(f"{self.backend_url}/api/camera/presets", timeout=2)
            if response.status_code == 200:
                presets = response.json()  # Returns list directly
                self.preset_combo.clear()
                if not presets:
                    self.preset_combo.addItem("No presets available")
                else:
                    for preset in presets[:20]:  # Show first 20
                        self.preset_combo.addItem(preset['name'], preset['token'])
                print(f"✓ Loaded {len(presets[:20])} presets")
        except Exception as e:
            print(f"Failed to load presets: {e}")
            # Keep "Loading presets..." text and retry later
    
    def manual_ptz_start(self, direction: str):
        """Start continuous PTZ movement (button pressed)"""
        self.ptz_hold_direction = direction
        self.ptz_hold_timer.start(100)  # Send continuous move commands every 100ms
        print(f"🔘 PTZ hold: {direction} started")
    
    def manual_ptz_stop(self):
        """Stop continuous PTZ movement (button released)"""
        if self.ptz_hold_direction:
            print(f"🔘 PTZ hold: {self.ptz_hold_direction} stopped")
            self.ptz_hold_direction = None
        self.ptz_hold_timer.stop()
        
        # Send stop command to camera
        try:
            requests.post(f"{self.backend_url}/api/camera/stop", timeout=1)
        except:
            pass  # Ignore errors
    
    def ptz_hold_update(self):
        """Send continuous movement commands while button is held"""
        if not self.ptz_hold_direction:
            self.ptz_hold_timer.stop()
            return
        
        # Send very short movement command (100ms each)
        self.manual_ptz(self.ptz_hold_direction, duration_override=0.1)
    
    def manual_ptz(self, direction: str, duration_override: Optional[float] = None):
        """Manual PTZ control - pan, tilt, zoom"""
        try:
            # Use much slower speed for manual controls (30% of slider value)
            # This makes the controls more precise and less aggressive
            base_speed = self.speed_slider.value() / 10.0  # 0.1-1.0 range
            manual_speed = base_speed * 0.3  # Reduce to 30% for manual control
            
            # Map direction to pan/tilt/zoom values
            ptz_commands = {
                'up': {'pan': 0, 'tilt': manual_speed, 'zoom': 0, 'duration': 0.2},
                'down': {'pan': 0, 'tilt': -manual_speed, 'zoom': 0, 'duration': 0.2},
                'left': {'pan': -manual_speed, 'tilt': 0, 'zoom': 0, 'duration': 0.2},
                'right': {'pan': manual_speed, 'tilt': 0, 'zoom': 0, 'duration': 0.2},
                'zoom_in': {'pan': 0, 'tilt': 0, 'zoom': manual_speed * 0.5, 'duration': 0.15},
                'zoom_out': {'pan': 0, 'tilt': 0, 'zoom': -manual_speed * 0.5, 'duration': 0.15},
                'home': {'pan': 0, 'tilt': 0, 'zoom': 0, 'duration': 0.1}
            }
            
            if direction not in ptz_commands:
                print(f"✗ Unknown PTZ direction: {direction}")
                return
            
            cmd = ptz_commands[direction]
            
            # Override duration if provided (for continuous hold)
            if duration_override is not None:
                cmd['duration'] = duration_override
            
            # Send continuous move command to backend in a separate thread
            # This prevents UI blocking while waiting for response
            def send_ptz_command():
                try:
                    response = requests.post(
                        f"{self.backend_url}/api/camera/move",
                        json={
                            'pan': cmd['pan'],
                            'tilt': cmd['tilt'],
                            'zoom': cmd['zoom'],
                            'duration': cmd['duration']
                        },
                        timeout=1  # Shorter timeout for faster response
                    )
                    
                    if response.status_code == 200:
                        zoom_speed = cmd['zoom']
                        display_speed = abs(zoom_speed) if zoom_speed != 0 else manual_speed
                        print(f"✓ PTZ {direction} command sent (speed: {display_speed:.2f}, duration: {cmd['duration']}s)")
                    else:
                        print(f"✗ PTZ command failed: {response.status_code}")
                except Exception as e:
                    print(f"✗ Error sending PTZ command: {e}")
            
            # Execute in background thread for instant button response
            Thread(target=send_ptz_command, daemon=True).start()
                
        except Exception as e:
            print(f"✗ Error sending PTZ command: {e}")
    
    def goto_preset(self):
        """Move camera to selected preset"""
        preset_text = self.preset_combo.currentText()
        if preset_text == "Loading presets..." or preset_text == "No presets available":
            print("✗ Presets not loaded yet")
            return
        
        # Get preset token from combo box data (safer than parsing text)
        try:
            current_index = self.preset_combo.currentIndex()
            preset_token = self.preset_combo.itemData(current_index)
            
            if preset_token is None:
                print("✗ No preset token found")
                return
            
            # Use maximum speed (1.0) for preset movement - always fast
            speed = 1.0
            
            response = requests.post(
                f"{self.backend_url}/api/camera/preset/{preset_token}",
                params={"speed": speed},
                timeout=5
            )
            
            if response.status_code == 200:
                print(f"✓ Camera moving to preset {preset_text} (token: {preset_token}) at speed {speed}")
            else:
                print(f"✗ Failed to move to preset: {response.status_code}")
        except Exception as e:
            print(f"✗ Error moving to preset: {e}")
            import traceback
            traceback.print_exc()
    
    def showEvent(self, event):
        """Called when window is shown - center on current screen if first launch"""
        super().showEvent(event)
        
        # Only center if this is first launch (no saved geometry)
        if not self.settings.value("window/geometry"):
            # Get the screen where mouse cursor is (for multi-monitor support)
            cursor_pos = QApplication.desktop().cursor().pos()
            screen = QApplication.screenAt(cursor_pos)
            
            if screen is None:
                screen = QApplication.primaryScreen()
            
            if screen:
                screen_geometry = screen.availableGeometry()
                window_geometry = self.frameGeometry()
                
                # Center window on the screen where cursor is
                center_point = screen_geometry.center()
                window_geometry.moveCenter(center_point)
                self.move(window_geometry.topLeft())
                
                print(f"✓ Window positioned on screen: {screen.name() if hasattr(screen, 'name') else 'primary'}")
                print(f"  Screen geometry: {screen_geometry.width()}×{screen_geometry.height()}")
        
        # Force update of all widgets to ensure they're responsive
        self.update()
        self.repaint()
    
    def resizeEvent(self, event):
        """Called when window is resized - save geometry"""
        super().resizeEvent(event)
        # Save will happen via timer (to avoid excessive saves during dragging)
    
    def moveEvent(self, event):
        """Called when window is moved - save geometry"""
        super().moveEvent(event)
        # Save will happen via timer (to avoid excessive saves during dragging)
    
    def closeEvent(self, event):
        """Clean up on exit"""
        # Stop the geometry save timer
        if hasattr(self, 'geometry_save_timer'):
            self.geometry_save_timer.stop()
        
        # Save window geometry one final time before closing
        self.save_window_geometry()
        print(f"✓ Final save: window position and size ({self.width()}×{self.height()} at {self.x()},{self.y()})")
        
        self.stream_worker.stop()
        self.stream_worker.wait()
        
        self.stats_worker.stop()
        self.stats_worker.wait()
        
        event.accept()


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    
    qapp = QApplication(sys.argv)
    
    # Configure camera RTSP URL
    # Backend uses /12 (800×600), desktop uses /11 (higher res) to avoid connection conflict
    # Camera only allows one connection per stream path
    camera_rtsp = "rtsp://admin:Windows98@192.168.1.107:554/11"  # 2560×1920
    backend_url = "http://localhost:8000"
    
    window = CameraTrackerApp(camera_rtsp, backend_url)
    window.show()
    
    sys.exit(qapp.exec_())
