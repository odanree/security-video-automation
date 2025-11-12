# Security Video Automation - Task List

## Development Progress

### Phase 1: Infrastructure Setup

- [-] **Task 1: Set up project structure and folders**
  - Create src/, config/, tests/, scripts/, docs/ folders with __init__.py files
  - Status: IN PROGRESS

- [ ] **Task 2: Create camera discovery script**
  - Build scripts/discover_camera.py to find camera IP and check ONVIF/PTZ capabilities
  - Status: Not Started

- [ ] **Task 3: Implement PTZ controller**
  - Create src/camera/ptz_controller.py with ONVIF integration for preset control
  - Status: Not Started

- [ ] **Task 4: Set up camera presets manually**
  - Use camera web interface to configure 3-5 presets (zone_left, zone_center, zone_right, etc.)
  - Status: Not Started
  - Note: Requires physical camera access

- [ ] **Task 5: Create PTZ test script**
  - Build scripts/test_ptz.py to test moving between camera presets
  - Status: Not Started

### Phase 2: Core AI Implementation

- [ ] **Task 6: Implement object detector**
  - Create src/ai/object_detector.py using YOLOv8 for person/vehicle detection
  - Status: Not Started

- [ ] **Task 7: Implement motion tracker**
  - Create src/ai/motion_tracker.py to track subject positions and determine movement direction
  - Status: Not Started

- [ ] **Task 8: Create video stream handler**
  - Build src/video/stream_handler.py for RTSP stream capture with threading
  - Status: Not Started

- [ ] **Task 9: Implement tracking engine**
  - Create src/automation/tracking_engine.py to coordinate detection, tracking, and PTZ control
  - Status: Not Started

### Phase 3: Configuration & Main Application

- [ ] **Task 10: Create configuration files**
  - Build config/camera_config.yaml and config/tracking_rules.yaml for system settings
  - Status: Not Started

- [ ] **Task 11: Build main application**
  - Create src/main.py as entry point to run the tracking system
  - Status: Not Started

### Phase 4: Testing & Web Dashboard

- [ ] **Task 12: Write unit tests**
  - Create tests in tests/unit/ for PTZ controller, object detector, motion tracker
  - Status: Not Started

- [ ] **Task 13: Build FastAPI web dashboard**
  - Create src/web/app.py with endpoints for camera status, presets, and video streaming
  - Status: Not Started

- [ ] **Task 14: Create dashboard frontend**
  - Build src/web/templates/index.html and src/web/static/ assets for live dashboard
  - Status: Not Started

### Phase 5: Portfolio & Demo Deployment

- [ ] **Task 15: Record demo footage**
  - Capture sample video showing tracking in action for portfolio demo
  - Status: Not Started

- [ ] **Task 16: Create demo mode**
  - Build demo version using pre-recorded video instead of live camera
  - Status: Not Started

- [ ] **Task 17: Deploy demo to Vercel**
  - Deploy static demo version to Vercel for public portfolio showcase
  - Status: Not Started

- [ ] **Task 18: Create YouTube demo video**
  - Record 3-5 minute video demonstration of system working
  - Status: Not Started

- [ ] **Task 19: Add to portfolio website**
  - Create project showcase page with demo link, screenshots, and description
  - Status: Not Started

- [ ] **Task 20: Update LinkedIn and resume**
  - Add project to LinkedIn projects section and update resume with demo link
  - Status: Not Started

---

## Progress Summary

- **Total Tasks:** 20
- **Completed:** 0
- **In Progress:** 1
- **Not Started:** 19
- **Completion:** 0%

## Next Steps

1. Complete folder structure setup (Task 1)
2. Create camera discovery script (Task 2)
3. Implement PTZ controller (Task 3)

## Notes

- Follow conventional commit format for all git commits
- Keep root directory clean - only README.md as .md file
- Use feature branches - never commit directly to main
- Update this file as tasks are completed
