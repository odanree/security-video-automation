# Create Pull Requests for Feature Branches
# This script opens GitHub PR creation pages in browser

$repo = "odanree/security-video-automation"

# PR 1: feature/config-system → main
$pr1_title = "feat: Configuration system and tracking engine"
$pr1_body = @"
## Summary
Implements configuration system with YAML files and the core tracking engine that coordinates all components.

## Changes
### Configuration System (Task 10)
- ✅ Created \`config/camera_config.yaml\` - Camera settings, RTSP URLs, PTZ presets
- ✅ Created \`config/tracking_rules.yaml\` - Tracking zones, direction triggers, filters
- ✅ Created \`config/ai_config.yaml\` - AI model settings, device configuration
- ✅ Implemented \`ConfigLoader\` class with validation

### Tracking Engine (Task 9)
- ✅ Created \`src/automation/tracking_engine.py\` (580+ lines)
- ✅ \`TrackingEngine\` orchestrates detection → tracking → PTZ control
- ✅ Zone-based tracking with 5 configurable zones
- ✅ Direction-based PTZ triggers (LEFT_TO_RIGHT, RIGHT_TO_LEFT)
- ✅ Event recording and statistics tracking
- ✅ Background thread for automated processing

## Testing
- ✅ All configurations load successfully
- ✅ Engine tested with simulated video
- ✅ Zone detection working
- ✅ Direction triggers validated

## Related Tasks
- Closes Task 9: Implement tracking engine
- Closes Task 10: Create configuration files

## Project Progress
- Tasks completed: 10/20 (50%)
"@

# PR 2: feature/main-application → main
$pr2_title = "feat: Main application with CLI, runtime fixes, and CI/CD"
$pr2_body = @"
## Summary
Complete main application entry point with CLI interface, interactive launcher, comprehensive documentation, and GitHub Actions CI/CD workflow. Includes extensive runtime debugging and fixes.

## Changes
### Main Application (Task 11)
- ✅ Created \`src/main.py\` (487 lines) - Full application with CLI
- ✅ Created \`run.py\` (96 lines) - Interactive launcher
- ✅ Created \`docs/RUNNING.md\` (231 lines) - Complete usage guide
- ✅ Command-line options: \`--display\`, \`--duration\`, \`--log-level\`, \`--no-ptz\`
- ✅ Keyboard controls: q (quit), p (pause/resume), s (stats)
- ✅ Component initialization and graceful shutdown
- ✅ Statistics logging and monitoring

### Runtime Debugging & Fixes
- ✅ Discovered correct RTSP URL via ONVIF (\`/11\` not \`/live\`)
- ✅ Fixed camera credentials (Windows98 password)
- ✅ Removed Unicode characters for Windows console compatibility
- ✅ Fixed TrackingZone parameter names (\`preset_token\`)
- ✅ Fixed TrackingConfig initialization (removed invalid \`mode\`)
- ✅ Added missing \`stream_handler\` parameter to TrackingEngine
- ✅ Fixed statistics dictionary key mismatches
- ✅ Refactored tracking loop (engine manages own thread)

### New Tools
- ✅ \`scripts/get_stream_uri.py\` - ONVIF stream URI discovery (125 lines)
- ✅ \`scripts/test_stream_urls.py\` - Stream URL testing utility (141 lines)

### CI/CD
- ✅ GitHub Actions workflow for PR checks
- ✅ Flake8 linting (syntax errors and code quality)
- ✅ Pytest test runner
- ✅ Import validation for core modules
- ✅ Project structure verification

### Documentation
- ✅ Updated \`README.md\` with running instructions
- ✅ Updated \`.github/copilot-instructions.md\` with venv guidelines
- ✅ Updated \`docs/TODO.md\` - marked Tasks 9-11 complete

## Testing
- ✅ 60-second live camera test successful
- ✅ 658 frames processed @ 11 FPS
- ✅ 79 objects detected (AI working)
- ✅ 79 tracks created (motion tracking working)
- ✅ All components initialized correctly
- ✅ No runtime errors
- ✅ Clean shutdown

## Camera Validation
- **Camera:** 192.168.1.107:8080
- **Credentials:** admin/Windows98
- **Stream:** rtsp://192.168.1.107:554/11 (2560x1920 @ 15 FPS)
- **Status:** ✅ Connected and streaming

## Related Tasks
- Closes Task 11: Build main application

## Project Progress
- Tasks completed: 11/20 (55%)
- Phase 1: 80% (4/5 tasks)
- Phase 2: 100% (3/3 tasks)
- Phase 3: 100% (3/3 tasks)

## Breaking Changes
None - first complete release

## Notes
PTZ movement testing requires manual preset configuration (Task 4). Detection and tracking are fully operational.
"@

# Encode for URL
Add-Type -AssemblyName System.Web
$pr1_body_encoded = [System.Web.HttpUtility]::UrlEncode($pr1_body)
$pr2_body_encoded = [System.Web.HttpUtility]::UrlEncode($pr2_body)

# Generate PR URLs
$pr1_url = "https://github.com/$repo/compare/main...feature/config-system?expand=1&title=$([System.Web.HttpUtility]::UrlEncode($pr1_title))&body=$pr1_body_encoded"
$pr2_url = "https://github.com/$repo/compare/main...feature/main-application?expand=1&title=$([System.Web.HttpUtility]::UrlEncode($pr2_title))&body=$pr2_body_encoded"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "PULL REQUEST CREATION" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Opening PR creation pages in browser...`n" -ForegroundColor Green

Write-Host "PR #1: feature/config-system → main" -ForegroundColor Yellow
Write-Host "  Title: $pr1_title"
Write-Host "  Opening: $pr1_url`n"
Start-Process $pr1_url

Start-Sleep -Seconds 2

Write-Host "PR #2: feature/main-application → main" -ForegroundColor Yellow
Write-Host "  Title: $pr2_title"
Write-Host "  Opening: $pr2_url`n"
Start-Process $pr2_url

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "NEXT STEPS" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "1. Review PR descriptions in browser" -ForegroundColor White
Write-Host "2. Click 'Create Pull Request' for each PR" -ForegroundColor White
Write-Host "3. Wait for CI/CD checks to complete" -ForegroundColor White
Write-Host "4. Merge PRs with 'Squash and merge'" -ForegroundColor White
Write-Host "5. Delete feature branches after merge`n" -ForegroundColor White

Write-Host "To merge and cleanup after PRs are created, run:" -ForegroundColor Green
Write-Host "  .\scripts\merge_and_cleanup.ps1`n" -ForegroundColor Cyan
