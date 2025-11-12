# Automatically Create Pull Requests using GitHub CLI
# Requires: gh CLI installed and authenticated

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "AUTO CREATE PULL REQUESTS" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check if gh is authenticated
Write-Host "Checking GitHub CLI authentication..." -ForegroundColor Yellow
gh auth status
if ($LASTEXITCODE -ne 0) {
    Write-Host "`nGitHub CLI not authenticated. Run: gh auth login" -ForegroundColor Red
    exit 1
}
Write-Host "✓ GitHub CLI authenticated`n" -ForegroundColor Green

# PR 1: feature/config-system → main
Write-Host "Creating PR #1: feature/config-system → main..." -ForegroundColor Yellow

$pr1_title = "feat: Configuration system and tracking engine"
$pr1_body = @"
## Summary
Implements configuration system with YAML files and the core tracking engine that coordinates all components.

## Changes
### Configuration System (Task 10)
- ✅ Created ``config/camera_config.yaml`` - Camera settings, RTSP URLs, PTZ presets
- ✅ Created ``config/tracking_rules.yaml`` - Tracking zones, direction triggers, filters
- ✅ Created ``config/ai_config.yaml`` - AI model settings, device configuration
- ✅ Implemented ``ConfigLoader`` class with validation

### Tracking Engine (Task 9)
- ✅ Created ``src/automation/tracking_engine.py`` (580+ lines)
- ✅ ``TrackingEngine`` orchestrates detection → tracking → PTZ control
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

gh pr create `
    --base main `
    --head feature/config-system `
    --title "$pr1_title" `
    --body "$pr1_body" `
    --fill-first

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ PR #1 created successfully`n" -ForegroundColor Green
} else {
    Write-Host "⚠ PR #1 creation failed or already exists`n" -ForegroundColor Red
}

Start-Sleep -Seconds 2

# PR 2: feature/main-application → main
Write-Host "Creating PR #2: feature/main-application → main..." -ForegroundColor Yellow

$pr2_title = "feat: Main application with CLI, runtime fixes, and CI/CD"
$pr2_body = @"
## Summary
Complete main application entry point with CLI interface, interactive launcher, comprehensive documentation, and GitHub Actions CI/CD workflow. Includes extensive runtime debugging and fixes.

## Changes
### Main Application (Task 11)
- ✅ Created ``src/main.py`` (487 lines) - Full application with CLI
- ✅ Created ``run.py`` (96 lines) - Interactive launcher
- ✅ Created ``docs/RUNNING.md`` (231 lines) - Complete usage guide
- ✅ Command-line options: ``--display``, ``--duration``, ``--log-level``, ``--no-ptz``
- ✅ Keyboard controls: q (quit), p (pause/resume), s (stats)
- ✅ Component initialization and graceful shutdown
- ✅ Statistics logging and monitoring

### Runtime Debugging & Fixes
- ✅ Discovered correct RTSP URL via ONVIF (``/11`` not ``/live``)
- ✅ Fixed camera credentials (Windows98 password)
- ✅ Removed Unicode characters for Windows console compatibility
- ✅ Fixed TrackingZone parameter names (``preset_token``)
- ✅ Fixed TrackingConfig initialization (removed invalid ``mode``)
- ✅ Added missing ``stream_handler`` parameter to TrackingEngine
- ✅ Fixed statistics dictionary key mismatches
- ✅ Refactored tracking loop (engine manages own thread)

### New Tools
- ✅ ``scripts/get_stream_uri.py`` - ONVIF stream URI discovery (125 lines)
- ✅ ``scripts/test_stream_urls.py`` - Stream URL testing utility (141 lines)
- ✅ ``scripts/create_prs.ps1`` - PowerShell PR creation helper
- ✅ ``scripts/merge_and_cleanup.ps1`` - Branch cleanup automation

### CI/CD
- ✅ GitHub Actions workflow for PR checks
- ✅ Flake8 linting (syntax errors and code quality)
- ✅ Pytest test runner
- ✅ Import validation for core modules
- ✅ Project structure verification

### Documentation
- ✅ Updated ``README.md`` with running instructions
- ✅ Updated ``.github/copilot-instructions.md`` with venv guidelines
- ✅ Updated ``docs/TODO.md`` - marked Tasks 9-11 complete
- ✅ Created ``docs/PR_WORKFLOW.md`` - PR workflow guide

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

gh pr create `
    --base main `
    --head feature/main-application `
    --title "$pr2_title" `
    --body "$pr2_body" `
    --fill-first

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ PR #2 created successfully`n" -ForegroundColor Green
} else {
    Write-Host "⚠ PR #2 creation failed or already exists`n" -ForegroundColor Red
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "PR CREATION COMPLETE" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "View your pull requests:" -ForegroundColor White
Write-Host "  https://github.com/odanree/security-video-automation/pulls`n" -ForegroundColor Cyan

Write-Host "Or use CLI to view:" -ForegroundColor White
Write-Host "  gh pr list`n" -ForegroundColor Cyan

Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Review PRs on GitHub" -ForegroundColor White
Write-Host "2. Wait for CI/CD checks to complete" -ForegroundColor White
Write-Host "3. Merge with 'Squash and merge'" -ForegroundColor White
Write-Host "4. Run: .\scripts\merge_and_cleanup.ps1`n" -ForegroundColor White
