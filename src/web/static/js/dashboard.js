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
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;
            this.updateConnectionStatus(true);
        };
        
        this.ws.onmessage = (event) => {
            console.log('WebSocket message received:', event.data);
            try {
                const message = JSON.parse(event.data);
                console.log('Parsed message:', message);
                
                // Handle different message types
                if (message.type === 'statistics') {
                    console.log('Statistics message:', message.data);
                    this.updateStatistics(message.data);
                } else if (message.type === 'event') {
                    console.log('Event message:', message.data);
                    this.addEventLog(message.data);
                }
            } catch (e) {
                console.error('Error parsing WebSocket message:', e);
            }
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
        
        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.updateConnectionStatus(false);
            this.attemptReconnect();
        };
    }
    
    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Reconnecting... (Attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
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
    // Video Stream
    // ========================================================================
    
    initializeVideoStream() {
        const videoElement = document.getElementById('video-stream');
        const videoOverlay = document.getElementById('video-overlay');
        
        // Set the stream URL
        videoElement.src = this.streamUrl;
        
        // For MJPEG streams in <img> tags, use onload instead of oncanplay
        videoElement.onload = () => {
            console.log('Video stream loaded successfully');
            videoOverlay.classList.add('hidden');
        };
        
        videoElement.onerror = () => {
            console.error('Video stream error');
            videoOverlay.classList.add('hidden');
            document.getElementById('video-status').textContent = 'Stream unavailable';
        };
        
        // Hide spinner after a short delay as fallback (MJPEG streams may not fire onload)
        setTimeout(() => {
            if (!videoOverlay.classList.contains('hidden')) {
                console.log('Hiding spinner via timeout fallback');
                videoOverlay.classList.add('hidden');
            }
        }, 2000);
    }
    
    toggleFullscreen() {
        const videoContainer = document.querySelector('.video-container');
        
        if (!document.fullscreenElement) {
            videoContainer.requestFullscreen().catch(err => {
                console.error('Fullscreen error:', err);
            });
        } else {
            document.exitFullscreen();
        }
    }
    
    // ========================================================================
    // Statistics Updates
    // ========================================================================
    
    updateStatistics(data) {
        console.log('Updating statistics:', data);
        
        // DEBUG: Update page title to confirm function is called
        document.title = `Stats: ${data.detections || 0} detections | Tracker`;
        
        // Update stat cards - map backend keys to DOM elements with null checks
        const detectionsEl = document.getElementById('stat-detections');
        if (detectionsEl) {
            detectionsEl.textContent = data.detections || 0;
            console.log('Updated detections element:', detectionsEl.textContent);
        } else {
            console.warn('stat-detections element not found!');
        }
        
        const tracksEl = document.getElementById('stat-tracks');
        if (tracksEl) {
            tracksEl.textContent = data.tracks || 0;
            console.log('Updated tracks element:', tracksEl.textContent);
        } else {
            console.warn('stat-tracks element not found!');
        }
        
        const eventsEl = document.getElementById('stat-events');
        if (eventsEl) {
            eventsEl.textContent = data.completed_events || 0;
            console.log('Updated events element:', eventsEl.textContent);
        } else {
            console.warn('stat-events element not found!');
        }
        
        // Display additional stats if available
        const fpsElement = document.getElementById('stat-fps');
        if (fpsElement) {
            // Only update FPS if stream is connected or value is meaningful
            const fps = data.fps || data.processing_fps || 0;
            const streamConnected = data.stream_connected !== false;  // Default to true for compatibility
            
            if (streamConnected || fps > 0) {
                fpsElement.textContent = fps.toFixed(1);
                fpsElement.style.color = fps > 10 ? '#00FF00' : fps > 5 ? '#FFD700' : '#FF4444';
            } else {
                // Show loading state if stream not connected
                fpsElement.textContent = '--';
                fpsElement.style.color = '#999999';
            }
            console.log('Updated FPS element:', fpsElement.textContent, 'connected:', streamConnected);
        } else {
            console.warn('stat-fps element not found!');
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
            console.error('Failed to load system status:', error);
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
            console.error('Failed to start tracking:', error);
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
            console.error('Failed to stop tracking:', error);
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
                console.warn('preset-select element not found');
                return;
            }
            
            select.innerHTML = '<option value="">Select Preset...</option>';
            
            if (!Array.isArray(data.presets)) {
                console.warn('No presets returned from API');
                return;
            }
            
            data.presets.forEach(preset => {
                const option = document.createElement('option');
                option.value = preset.token;
                option.textContent = preset.name;
                select.appendChild(option);
            });
            
        } catch (error) {
            console.error('Failed to load presets:', error);
        }
    }
    
    async gotoPreset() {
        const select = document.getElementById('preset-select');
        if (!select) {
            console.warn('preset-select element not found');
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
            console.error('Failed to move camera:', error);
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
            console.error('PTZ move error:', error);
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
            console.error('PTZ move error:', error);
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
            console.error('PTZ stop error:', error);
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
                console.warn('events-container not found');
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
            console.error('Failed to load events:', error);
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
                    console.log('Initial statistics load:', data);
                    this.updateStatistics(data);
                }
            } catch (e) {
                console.error('Error loading initial statistics:', e);
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
                    console.log('Polled statistics:', data);
                    this.updateStatistics(data);
                }
            } catch (e) {
                console.error('Error polling statistics:', e);
            }
        }, 2000);
        
        // Poll tracking status every 3 seconds
        setInterval(async () => {
            try {
                const response = await fetch('/api/tracking/status');
                if (response.ok) {
                    const data = await response.json();
                    console.log('Tracking status:', data);
                    this.isTracking = data.running;
                    this.updateTrackingUI();
                    this.updateTrackingStats(data);
                }
            } catch (e) {
                console.error('Error polling tracking status:', e);
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
            // Switch back to normal stream (30 FPS, no overlays)
            targetUrl = '/api/video/stream';
            this.isDetectionMode = false;
            btn.style.opacity = '0.5';
            btn.title = 'Enable Detection Overlays (15 FPS)';
            console.log('Switching to fast stream: 30 FPS, no detection overlays');
        } else {
            // Switch to detection stream (15 FPS, with overlays)
            targetUrl = '/api/video/stream?detections=true';
            this.isDetectionMode = true;
            btn.style.opacity = '1.0';
            btn.title = 'Disable Detection Overlays (30 FPS)';
            console.log('Switching to detection stream: 15 FPS with detection overlays');
        }
        
        // Force a new stream connection by:
        // 1. Clearing the src (stops current stream)
        // 2. Small delay to ensure disconnect
        // 3. Set new src with cache buster
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
        console.log(`[${type.toUpperCase()}] ${message}`);
        // TODO: Implement toast notification UI
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new Dashboard();
});
