// ============================================================================
// Security Camera AI Tracker - Dashboard JavaScript
// ============================================================================

class Dashboard {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000;
        this.isTracking = false;
        this.isDetectionMode = false;  // Track current detection mode for FPS display
        this.streamUrl = '/api/video/stream';
        
        this.init();
    }
    
    // Initialize dashboard
    init() {
        this.setupEventListeners();
        this.initializeVideoStream();
        this.connectWebSocket();
        this.loadCameraPresets();
        this.loadSystemStatus();
        this.startPolling();
    }
    
    // ========================================================================
    // WebSocket Connection
    // ========================================================================
    
    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/updates`;
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            this.reconnectAttempts = 0;
            this.updateConnectionStatus(true);
        };
        
        this.ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                
                // Handle different message types
                if (message.type === 'statistics') {
                    this.updateStatistics(message.data);
                } else if (message.type === 'event') {
                    this.addEventLog(message.data);
                }
            } catch (e) {
                // Silent fail
            }
        };
        
        this.ws.onerror = (error) => {
            // Silent fail
        };
        
        this.ws.onclose = () => {
            this.updateConnectionStatus(false);
            this.attemptReconnect();
        };
    }
    
    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            setTimeout(() => this.connectWebSocket(), this.reconnectDelay);
        }
    }
    
    updateConnectionStatus(connected) {
        const statusDot = document.getElementById('connection-status');
        const statusText = document.getElementById('connection-text');
        
        if (statusDot) {
            if (connected) {
                statusDot.classList.remove('offline');
                statusDot.classList.add('online');
            } else {
                statusDot.classList.remove('online');
                statusDot.classList.add('offline');
            }
        }
        
        if (statusText) {
            statusText.textContent = connected ? 'Connected' : 'Disconnected';
        }
    }
    
    // ========================================================================
    // Video Stream - WebSocket Binary (Ultra-Low Latency)
    // ========================================================================
    
    initializeVideoStream() {
        this.setupWebSocketVideoStream();
    }
    
    setupWebSocketVideoStream() {
        const canvas = document.getElementById('video-canvas');
        const overlay = document.getElementById('video-overlay');
        const ctx = canvas.getContext('2d', { willReadFrequently: true });
        
        if (!ctx) {
            console.warn('Canvas context not available');
            return;
        }
        
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsVideoUrl = `${protocol}//${window.location.host}/ws/video`;
        
        const wsVideo = new WebSocket(wsVideoUrl);
        wsVideo.binaryType = 'arraybuffer';
        
        let firstFrame = false;
        let frameBuffer = new ArrayBuffer(0);
        const headerSize = 4; // 4-byte frame size
        
        wsVideo.onopen = () => {
            // Stream connected
        };
        
        wsVideo.onmessage = (event) => {
            try {
                // Append incoming data to buffer
                const newData = new Uint8Array(event.data);
                const oldBuffer = new Uint8Array(frameBuffer);
                frameBuffer = new ArrayBuffer(oldBuffer.length + newData.length);
                const combined = new Uint8Array(frameBuffer);
                combined.set(oldBuffer);
                combined.set(newData, oldBuffer.length);
                
                // Process complete frames
                while (frameBuffer.byteLength >= headerSize) {
                    const view = new DataView(frameBuffer);
                    const frameSize = view.getUint32(0, true); // Little-endian
                    
                    if (frameBuffer.byteLength >= headerSize + frameSize) {
                        // We have a complete frame
                        const frameData = frameBuffer.slice(headerSize, headerSize + frameSize);
                        frameBuffer = frameBuffer.slice(headerSize + frameSize);
                        
                        // Decode JPEG and display
                        this.displayFrameFromJPEG(canvas, ctx, frameData);
                        
                        if (!firstFrame) {
                            overlay.classList.add('hidden');
                            firstFrame = true;
                        }
                    } else {
                        break; // Wait for more data
                    }
                }
            } catch (e) {
                console.error('Frame processing error:', e);
            }
        };
        
        wsVideo.onerror = (error) => {
            console.error('WebSocket video error:', error);
        };
        
        wsVideo.onclose = () => {
            // Attempt reconnect after delay
            setTimeout(() => this.setupWebSocketVideoStream(), 2000);
        };
    }
    
    displayFrameFromJPEG(canvas, ctx, jpegData) {
        // Convert JPEG binary data to blob and decode
        const blob = new Blob([jpegData], { type: 'image/jpeg' });
        const url = URL.createObjectURL(blob);
        
        const img = new Image();
        img.onload = () => {
            // Set canvas size to match image (only on first frame or size change)
            if (canvas.width !== img.width || canvas.height !== img.height) {
                canvas.width = img.width;
                canvas.height = img.height;
            }
            
            // Draw image to canvas
            ctx.drawImage(img, 0, 0);
            
            // Clean up blob URL
            URL.revokeObjectURL(url);
        };
        
        img.onerror = () => {
            URL.revokeObjectURL(url);
            console.warn('Failed to decode frame');
        };
        
        img.src = url;
    }
    
    toggleFullscreen() {
        const videoContainer = document.querySelector('.video-container');
        
        if (!document.fullscreenElement) {
            videoContainer.requestFullscreen().catch(err => {
                // Silent fail
            });
        } else {
            document.exitFullscreen();
        }
    }
    
    // ========================================================================
    // Statistics Updates
    // ========================================================================
    
    updateStatistics(data) {
        // Update stat cards - map backend keys to DOM elements with null checks
        const detectionsEl = document.getElementById('stat-detections');
        if (detectionsEl) {
            detectionsEl.textContent = data.detections || 0;
        }
        
        const tracksEl = document.getElementById('stat-tracks');
        if (tracksEl) {
            tracksEl.textContent = data.tracks || 0;
        }
        
        const eventsEl = document.getElementById('stat-events');
        if (eventsEl) {
            eventsEl.textContent = data.completed_events || 0;
        }
        
        // Display additional stats if available
        const fpsElement = document.getElementById('stat-fps');
        if (fpsElement) {
            // Get FPS value - prioritize fps, then processing_fps
            const fps = parseFloat(data.fps) || parseFloat(data.processing_fps) || 0;
            const streamConnected = data.stream_connected !== false;  // Default to true for compatibility
            
            // Only show '--' if explicitly disconnected AND fps is 0
            if (!streamConnected && fps < 0.1) {
                fpsElement.textContent = '--';
                fpsElement.style.color = '#999999';
            } else if (fps >= 0.5) {
                // Show FPS value if it's meaningful (>= 0.5)
                fpsElement.textContent = fps.toFixed(1);
                fpsElement.style.color = fps > 10 ? '#00FF00' : fps > 5 ? '#FFD700' : '#FF4444';
            } else {
                // FPS very low but stream might be starting - show 0.0 instead of --
                fpsElement.textContent = '0.0';
                fpsElement.style.color = '#FF4444';
            }
        }
        
        // Update frame and processing info
        const framesReceivedEl = document.getElementById('frames-received');
        if (framesReceivedEl) {
            framesReceivedEl.textContent = data.frames_processed || 0;
        }
        
        const activeEventsEl = document.getElementById('stat-active-events');
        if (activeEventsEl) {
            activeEventsEl.textContent = data.active_events || 0;
        }
        
        const modeEl = document.getElementById('stat-mode');
        if (modeEl) {
            modeEl.textContent = data.mode || data.current_mode || 'unknown';
        }
    }
    
    async loadSystemStatus() {
        try {
            // Fetch system status and camera info in parallel
            const [statusResponse, cameraResponse] = await Promise.all([
                fetch('/api/status'),
                fetch('/api/camera/info')
            ]);
            
            const status = await statusResponse.json();
            const camera = cameraResponse.ok ? await cameraResponse.json() : null;
            
            // Update system info with null checks
            const streamStatusEl = document.getElementById('status-stream');
            if (streamStatusEl) {
                streamStatusEl.textContent = status.camera_connected ? '✓ Connected' : '✗ Disconnected';
                streamStatusEl.className = status.camera_connected ? 'badge badge-active' : 'badge badge-inactive';
            }
            
            const detectorStatusEl = document.getElementById('status-detector');
            if (detectorStatusEl) {
                detectorStatusEl.textContent = status.ai_model_loaded ? '✓ Loaded' : '✗ Not Loaded';
                detectorStatusEl.className = status.ai_model_loaded ? 'badge badge-active' : 'badge badge-inactive';
            }
            
            const ptzStatusEl = document.getElementById('status-ptz');
            if (ptzStatusEl) {
                ptzStatusEl.textContent = status.ptz_enabled ? '✓ Enabled' : '✗ Disabled';
                ptzStatusEl.className = status.ptz_enabled ? 'badge badge-active' : 'badge badge-inactive';
            }
            
            // Update camera info section
            if (camera) {
                const cameraNameEl = document.getElementById('camera-name');
                if (cameraNameEl) {
                    cameraNameEl.textContent = camera.name || 'Unknown';
                }
                
                const cameraResolutionEl = document.getElementById('camera-resolution');
                if (cameraResolutionEl) {
                    const res = camera.resolution;
                    cameraResolutionEl.textContent = Array.isArray(res) 
                        ? `${res[0]}x${res[1]}` 
                        : (res || '--');
                }
                
                const streamFpsEl = document.getElementById('stream-fps');
                if (streamFpsEl) {
                    // Show current output FPS (will update on detection toggle)
                    const outputFps = this.isDetectionMode ? camera.output_fps_detection || 15 : (camera.output_fps || 30);
                    streamFpsEl.textContent = `${outputFps} (${this.isDetectionMode ? 'detection' : 'fast'})`;
                }
            }
            
            // Update tracking status
            this.isTracking = status.tracking_active;
            this.updateTrackingUI();
            
        } catch (error) {
            // Silent fail
        }
    }
    
    // ========================================================================
    // Tracking Control
    // ========================================================================
    
    async startTracking() {
        try {
            const response = await fetch('/api/tracking/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            if (response.ok) {
                this.isTracking = true;
                this.updateTrackingUI();
                this.showNotification('Tracking started', 'success');
            }
        } catch (error) {
            this.showNotification('Failed to start tracking', 'error');
        }
    }
    
    async stopTracking() {
        try {
            const response = await fetch('/api/tracking/stop', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            if (response.ok) {
                this.isTracking = false;
                this.updateTrackingUI();
                this.showNotification('Tracking stopped', 'info');
            }
        } catch (error) {
            this.showNotification('Failed to stop tracking', 'error');
        }
    }
    
    updateTrackingUI() {
        const startBtn = document.getElementById('btn-start-tracking');
        const stopBtn = document.getElementById('btn-stop-tracking');
        const statusBadge = document.getElementById('tracking-status');
        
        if (startBtn && stopBtn && statusBadge) {
            if (this.isTracking) {
                startBtn.disabled = true;
                stopBtn.disabled = false;
                statusBadge.className = 'badge badge-active';
                statusBadge.textContent = 'Active';
            } else {
                startBtn.disabled = false;
                stopBtn.disabled = true;
                statusBadge.className = 'badge badge-inactive';
                statusBadge.textContent = 'Inactive';
            }
        }
    }
    
    updateTrackingStats(data) {
        /**Update tracking statistics display*/
        // Update active tracks count if element exists
        const activeTracksEl = document.getElementById('active-tracks');
        if (activeTracksEl) {
            activeTracksEl.textContent = data.active_tracks || 0;
        }
        
        // Update detections count if element exists
        const detectionsEl = document.getElementById('tracking-detections');
        if (detectionsEl) {
            detectionsEl.textContent = data.detections || 0;
        }
        
        // Update PTZ movements count if element exists
        const movementsEl = document.getElementById('ptz-movements');
        if (movementsEl) {
            movementsEl.textContent = data.ptz_movements || 0;
        }
    }
    
    // ========================================================================
    // PTZ Camera Control
    // ========================================================================
    
    async loadCameraPresets() {
        try {
            const response = await fetch('/api/camera/presets');
            const data = await response.json();
            
            const select = document.getElementById('preset-select');
            if (!select) {
                return;
            }
            
            select.innerHTML = '<option value="">Select Preset...</option>';
            
            if (!Array.isArray(data.presets)) {
                return;
            }
            
            data.presets.forEach(preset => {
                const option = document.createElement('option');
                option.value = preset.token;
                option.textContent = preset.name;
                select.appendChild(option);
            });
            
        } catch (error) {
            // Silent fail
        }
    }
    
    async gotoPreset() {
        const select = document.getElementById('preset-select');
        if (!select) {
            return;
        }
        
        const presetToken = select.value;
        if (!presetToken) return;
        
        try {
            const response = await fetch(`/api/camera/preset/${presetToken}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            if (response.ok) {
                this.showNotification(`Moving to ${select.options[select.selectedIndex].text}`, 'success');
            }
        } catch (error) {
            this.showNotification('Failed to move camera', 'error');
        }
    }
    
    async movePTZ(direction) {
        const speedSlider = document.getElementById('ptz-speed');
        const speed = speedSlider ? parseFloat(speedSlider.value) : 0.5;
        
        const velocities = {
            'up': { pan: 0, tilt: speed },
            'down': { pan: 0, tilt: -speed },
            'left': { pan: -speed, tilt: 0 },
            'right': { pan: speed, tilt: 0 }
        };
        
        const velocity = velocities[direction];
        if (!velocity) return;
        
        try {
            const response = await fetch('/api/camera/move', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    pan_velocity: velocity.pan,
                    tilt_velocity: velocity.tilt,
                    duration: 0.5
                })
            });
            
            if (!response.ok) {
                throw new Error('Move failed');
            }
        } catch (error) {
            // Silent fail
        }
    }
    
    async movePTZContinuous(panVelocity, tiltVelocity, duration = 0.3) {
        try {
            const response = await fetch('/api/camera/move', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    pan_velocity: panVelocity,
                    tilt_velocity: tiltVelocity,
                    duration: duration
                })
            });
            
            if (!response.ok) {
                throw new Error('Move failed');
            }
        } catch (error) {
            // Silent fail
        }
    }
    
    async stopPTZ() {
        try {
            const response = await fetch('/api/camera/stop', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            if (!response.ok) {
                throw new Error('Stop failed');
            }
        } catch (error) {
            // Silent fail
        }
    }
    
    async continuousZoom(velocity) {
        // Continuous zoom for hold-down behavior
        try {
            const response = await fetch('/api/camera/move', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    pan_velocity: 0.0,
                    tilt_velocity: 0.0,
                    zoom_velocity: velocity
                })
            });
            if (!response.ok) {
                console.error('Zoom failed:', response.status, response.statusText);
            }
        } catch (error) {
            console.error('Zoom error:', error.message);
        }
    }
    
    async stopZoom() {
        try {
            const response = await fetch('/api/camera/stop', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            if (!response.ok) {
                console.error('Stop failed:', response.status, response.statusText);
            }
        } catch (error) {
            console.error('Stop error:', error.message);
        }
    }
    
    updateSpeedDisplay() {
        const speedSlider = document.getElementById('ptz-speed');
        const speedValue = document.getElementById('speed-value');
        
        if (speedSlider && speedValue) {
            speedValue.textContent = `${(parseFloat(speedSlider.value) * 100).toFixed(0)}%`;
        }
    }
    
    // ========================================================================
    // Events
    // ========================================================================
    
    async loadEvents() {
        try {
            const response = await fetch('/api/events');
            const data = await response.json();
            
            const eventsContainer = document.getElementById('events-container');
            if (!eventsContainer) {
                return;
            }
            
            // Safely extract events array with multiple fallbacks
            let events = [];
            if (data && typeof data === 'object') {
                if (Array.isArray(data.events)) {
                    events = data.events;
                } else if (Array.isArray(data)) {
                    events = data;
                }
            }
            
            if (!Array.isArray(events) || events.length === 0) {
                eventsContainer.innerHTML = '<p class="no-events">No events recorded yet</p>';
                return;
            }
            
            eventsContainer.innerHTML = events.map(event => `
                <div class="event-item">
                    <div class="event-header">
                        <strong>${event.type || 'Unknown'}</strong>
                        <span class="event-time">${this.formatTime(event.timestamp)}</span>
                    </div>
                    <div class="event-details">
                        <div class="event-detail">
                            <span class="event-detail-label">Class:</span>
                            <span>${event.class_name || 'N/A'}</span>
                        </div>
                        <div class="event-detail">
                            <span class="event-detail-label">Confidence:</span>
                            <span>${(event.confidence * 100).toFixed(1) || 'N/A'}%</span>
                        </div>
                        <div class="event-detail">
                            <span class="event-detail-label">Direction:</span>
                            <span>${event.direction || 'N/A'}</span>
                        </div>
                    </div>
                </div>
            `).join('');
            
        } catch (error) {
            // Silent fail
        }
    }
    
    clearEvents() {
        const eventsContainer = document.getElementById('events-container');
        if (eventsContainer) {
            eventsContainer.innerHTML = '<p class="no-events">Events cleared</p>';
        }
    }
    
    // ========================================================================
    // Polling (fallback when WebSocket unavailable)
    // ========================================================================
    
    startPolling() {
        // Load statistics immediately on startup
        (async () => {
            try {
                const response = await fetch('/api/statistics');
                if (response.ok) {
                    const data = await response.json();
                    this.updateStatistics(data);
                }
            } catch (e) {
                // Silent fail
            }
        })();
        
        // Load system status immediately on startup
        this.loadSystemStatus();
        
        // Poll statistics every 2 seconds as fallback
        setInterval(async () => {
            try {
                const response = await fetch('/api/statistics');
                if (response.ok) {
                    const data = await response.json();
                    this.updateStatistics(data);
                }
            } catch (e) {
                // Silent fail
            }
        }, 2000);
        
        // Poll tracking status every 3 seconds
        setInterval(async () => {
            try {
                const response = await fetch('/api/tracking/status');
                if (response.ok) {
                    const data = await response.json();
                    this.isTracking = data.running;
                    this.updateTrackingUI();
                    this.updateTrackingStats(data);
                }
            } catch (e) {
                // Silent fail
            }
        }, 3000);
        
        // Reload events every 5 seconds
        setInterval(() => this.loadEvents(), 5000);
        
        // Reload system status every 10 seconds
        setInterval(() => this.loadSystemStatus(), 10000);
    }
    
    // ========================================================================
    // Event Listeners
    // ========================================================================
    
    setupEventListeners() {
        // Tracking controls - correct IDs
        document.getElementById('btn-start-tracking')?.addEventListener('click', () => this.startTracking());
        document.getElementById('btn-stop-tracking')?.addEventListener('click', () => this.stopTracking());
        
        // Video controls - correct IDs
        document.getElementById('btn-toggle-detections')?.addEventListener('click', () => this.toggleDetections());
        document.getElementById('btn-fullscreen')?.addEventListener('click', () => this.toggleFullscreen());
        
        // PTZ dpad controls - use mousedown for instant response
        document.querySelectorAll('.dpad-btn').forEach(btn => {
            let moveInterval = null;
            
            // Start moving on mousedown
            btn.addEventListener('mousedown', (e) => {
                const pan = parseFloat(e.target.dataset.pan || 0);
                const tilt = parseFloat(e.target.dataset.tilt || 0);
                
                if (pan !== 0 || tilt !== 0) {
                    // Immediate first move
                    this.movePTZContinuous(pan, tilt, 0.2);
                    
                    // Continue moving while held down
                    moveInterval = setInterval(() => {
                        this.movePTZContinuous(pan, tilt, 0.2);
                    }, 200);
                }
            });
            
            // Stop on mouseup or mouseleave
            const stopMove = () => {
                if (moveInterval) {
                    clearInterval(moveInterval);
                    moveInterval = null;
                    this.stopPTZ();
                }
            };
            
            btn.addEventListener('mouseup', stopMove);
            btn.addEventListener('mouseleave', stopMove);
        });
        
        // Preset selection
        document.getElementById('btn-goto-preset')?.addEventListener('click', () => this.gotoPreset());
        
        // Zoom controls - hold-down behavior
        const zoomInBtn = document.getElementById('btn-zoom-in');
        const zoomOutBtn = document.getElementById('btn-zoom-out');
        const self = this;
        
        if (zoomInBtn) {
            let zoomInterval = null;
            let isActive = false;
            
            zoomInBtn.addEventListener('mousedown', (e) => {
                e.preventDefault();
                if (isActive) return;
                isActive = true;
                zoomInBtn.style.opacity = '0.5';
                self.continuousZoom(0.5);
                self.showNotification('Zooming in...', 'info');
                zoomInterval = setInterval(() => {
                    self.continuousZoom(0.5);
                }, 100);
            });
            
            zoomInBtn.addEventListener('mouseup', () => {
                if (!isActive) return;
                isActive = false;
                clearInterval(zoomInterval);
                self.stopZoom();
                zoomInBtn.style.opacity = '1';
                self.showNotification('Zoom stopped', 'info');
            });
        }
        
        if (zoomOutBtn) {
            let zoomInterval = null;
            let isActive = false;
            
            zoomOutBtn.addEventListener('mousedown', (e) => {
                e.preventDefault();
                if (isActive) return;
                isActive = true;
                zoomOutBtn.style.opacity = '0.5';
                self.continuousZoom(-0.5);
                self.showNotification('Zooming out...', 'info');
                zoomInterval = setInterval(() => {
                    self.continuousZoom(-0.5);
                }, 100);
            });
            
            zoomOutBtn.addEventListener('mouseup', () => {
                if (!isActive) return;
                isActive = false;
                clearInterval(zoomInterval);
                self.stopZoom();
                zoomOutBtn.style.opacity = '1';
                self.showNotification('Zoom stopped', 'info');
            });
        }
        
        // Speed slider
        document.getElementById('ptz-speed')?.addEventListener('input', () => this.updateSpeedDisplay());
        
        // Clear events button
        document.getElementById('btn-clear-events')?.addEventListener('click', () => this.clearEvents());
        
        // Initialize speed display
        this.updateSpeedDisplay();
    }
    
    // ========================================================================
    // Video Stream Controls
    // ========================================================================
    
    toggleDetections() {
        const videoImg = document.getElementById('video-stream');
        const btn = document.getElementById('btn-toggle-detections');
        
        if (!videoImg) return;
        
        // Determine target URL based on current state
        let targetUrl;
        if (videoImg.src.includes('detections=true')) {
            // Switch back to normal stream (no overlays, faster)
            targetUrl = '/api/video/stream';
            this.isDetectionMode = false;
            btn.style.opacity = '0.5';
            btn.title = 'Enable Detection Overlays';
        } else {
            // Switch to detection stream (with overlays)
            targetUrl = '/api/video/stream?detections=true';
            this.isDetectionMode = true;
            btn.style.opacity = '1.0';
            btn.title = 'Disable Detection Overlays';
        }
        
        // Force a new stream connection by clearing and resetting src
        videoImg.src = '';
        
        setTimeout(() => {
            const timestamp = Date.now();
            videoImg.src = `${targetUrl}${targetUrl.includes('?') ? '&' : '?'}t=${timestamp}`;
            
            // Refresh camera info to update FPS display
            this.loadSystemStatus();
        }, 100);
    }
    
    // ========================================================================
    // Utilities
    // ========================================================================
    
    formatTime(timestamp) {
        const date = new Date(timestamp * 1000);
        return date.toLocaleTimeString();
    }
    
    showNotification(message, type = 'info') {
        const container = document.getElementById('notifications-container');
        if (!container) return;
        
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.style.cssText = `
            padding: 12px 16px;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 10px;
            animation: slideIn 0.3s ease-out;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            min-width: 200px;
        `;
        
        // Set color based on type
        const colors = {
            'success': { bg: '#10b981', text: '#fff', icon: '✓' },
            'error': { bg: '#ef4444', text: '#fff', icon: '✕' },
            'info': { bg: '#3b82f6', text: '#fff', icon: 'ℹ' },
            'warning': { bg: '#f59e0b', text: '#fff', icon: '⚠' }
        };
        
        const color = colors[type] || colors['info'];
        notification.style.backgroundColor = color.bg;
        notification.style.color = color.text;
        
        notification.innerHTML = `
            <span style="font-size: 16px; font-weight: bold;">${color.icon}</span>
            <span>${message}</span>
        `;
        
        container.appendChild(notification);
        
        // Auto-remove after 3 seconds
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
}

// Add CSS animations for notifications
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new Dashboard();
});
