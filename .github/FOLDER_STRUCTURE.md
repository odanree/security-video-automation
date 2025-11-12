# Folder Structure Guide

## Core Principle: Keep Root Clean! 🧹

**The root directory should only contain:**
- Configuration files
- Documentation files  
- Deployment files
- Dependency management files

**NO source code, logs, videos, or temporary files in root!**

---

## Directory Structure

```
security-video-automation/
│
├── 📂 src/                         ← ALL APPLICATION CODE GOES HERE
│   ├── __init__.py
│   ├── main.py                     ← Entry point
│   │
│   ├── 📂 video/                   ← Video processing module
│   │   ├── __init__.py
│   │   ├── stream_handler.py
│   │   └── frame_processor.py
│   │
│   ├── 📂 ai/                      ← AI/ML module
│   │   ├── __init__.py
│   │   ├── object_detector.py
│   │   ├── motion_tracker.py
│   │   └── 📂 models/              ← AI model files (gitignored)
│   │       └── .gitkeep
│   │
│   ├── 📂 camera/                  ← PTZ camera control module
│   │   ├── __init__.py
│   │   ├── ptz_controller.py
│   │   ├── onvif_client.py
│   │   └── preset_manager.py
│   │
│   ├── 📂 automation/              ← Tracking automation module
│   │   ├── __init__.py
│   │   ├── tracking_engine.py
│   │   └── rules_engine.py
│   │
│   └── 📂 web/                     ← Web dashboard
│       ├── __init__.py
│       ├── app.py
│       ├── 📂 static/              ← Frontend assets
│       │   ├── 📂 css/
│       │   ├── 📂 js/
│       │   └── 📂 demo/            ← Demo videos/images
│       └── 📂 templates/           ← HTML templates
│           ├── index.html
│           └── demo.html
│
├── 📂 config/                      ← CONFIGURATION FILES ONLY
│   ├── camera_config.yaml
│   ├── ai_config.yaml
│   └── tracking_rules.yaml
│
├── 📂 tests/                       ← ALL TEST FILES
│   ├── __init__.py
│   ├── conftest.py                 ← Pytest fixtures
│   ├── 📂 unit/
│   │   ├── test_ptz_controller.py
│   │   ├── test_object_detector.py
│   │   └── test_motion_tracker.py
│   └── 📂 integration/
│       ├── test_tracking_engine.py
│       └── test_camera_integration.py
│
├── 📂 scripts/                     ← UTILITY SCRIPTS
│   ├── discover_camera.py          ← One-off scripts
│   ├── test_ptz.py
│   └── calibrate_presets.py
│
├── 📂 docs/                        ← EXTENDED DOCUMENTATION
│   ├── API.md
│   ├── CAMERA_SETUP.md
│   ├── TROUBLESHOOTING.md
│   └── 📂 screenshots/
│       ├── dashboard.png
│       └── tracking.gif
│
├── 📂 logs/                        ← RUNTIME LOGS (gitignored)
│   └── .gitkeep
│
├── 📂 recordings/                  ← VIDEO RECORDINGS (gitignored)
│   └── .gitkeep
│
├── 📂 .github/                     ← GITHUB-SPECIFIC FILES
│   ├── copilot-instructions.md
│   ├── WORKFLOW.md
│   ├── FOLDER_STRUCTURE.md
│   └── 📂 workflows/               ← CI/CD pipelines
│       └── tests.yml
│
├── 📄 .env.example                 ← ROOT: Config template
├── 📄 .gitignore                   ← ROOT: Git ignore rules
├── 📄 requirements.txt             ← ROOT: Dependencies
├── 📄 requirements-dev.txt         ← ROOT: Dev dependencies
├── 📄 pytest.ini                   ← ROOT: Pytest config
├── 📄 Dockerfile                   ← ROOT: Docker build
├── 📄 docker-compose.yml           ← ROOT: Docker services
├── 📄 render.yaml                  ← ROOT: Render.com config
├── 📄 README.md                    ← ROOT: Main docs (ONLY .md file in root!)
└── 📄 LICENSE                      ← ROOT: License
```

---

## Where Does Each File Type Go?

### Application Code → `src/`

```python
# ✅ Correct
src/camera/ptz_controller.py
src/ai/object_detector.py
src/automation/tracking_engine.py
src/web/app.py
src/main.py

# ❌ Wrong - Don't put in root!
ptz_controller.py
object_detector.py
tracking_engine.py
app.py
main.py
```

### Tests → `tests/`

```python
# ✅ Correct
tests/unit/test_ptz_controller.py
tests/integration/test_tracking_engine.py
tests/conftest.py

# ❌ Wrong
test_ptz.py                        # In root
src/camera/test_ptz.py            # Mixed with source
```

### Configuration → `config/`

```yaml
# ✅ Correct
config/camera_config.yaml
config/ai_config.yaml
config/tracking_rules.yaml

# ❌ Wrong
camera_config.yaml                 # In root
src/config/camera_config.yaml     # In source code
```

### Utility Scripts → `scripts/`

```python
# ✅ Correct
scripts/discover_camera.py
scripts/test_ptz.py
scripts/setup_dev_env.py

# ❌ Wrong
discover_camera.py                 # In root
src/scripts/discover.py           # In source (not utilities)
```

### Documentation → `docs/` or `root`

```markdown
# ✅ Root (important docs only)
README.md          ← ONLY markdown file in root!
LICENSE

# ✅ docs/ (extended documentation)
docs/DEPLOYMENT.md
docs/PROJECT_SUMMARY.md
docs/CHANGELOG.md
docs/API.md
docs/CAMERA_SETUP.md
docs/TROUBLESHOOTING.md
docs/CONTRIBUTING.md
docs/screenshots/dashboard.png

# ❌ Wrong
src/README.md                      # Should be in root
DEPLOYMENT.md                      # Should be in docs/
camera_setup.md                    # Should be in docs/
CHANGELOG.md                       # Should be in docs/
```

### Web Assets → `src/web/static/` or `src/web/templates/`

```
# ✅ Correct
src/web/static/css/style.css
src/web/static/js/dashboard.js
src/web/static/demo/sample.mp4
src/web/templates/index.html

# ❌ Wrong
static/css/style.css               # In root
css/style.css                      # In root
templates/index.html               # In root
```

---

## Decision Tree: Where Should This File Go?

```
Is this a new file?
│
├─ Is it Python application code?
│  └─ YES → src/<module>/filename.py
│
├─ Is it a test file?
│  └─ YES → tests/unit/ or tests/integration/
│
├─ Is it a configuration file (YAML/JSON)?
│  └─ YES → config/filename.yaml
│
├─ Is it a standalone script (not part of app)?
│  └─ YES → scripts/filename.py
│
├─ Is it documentation?
│  ├─ Main README?
│  │  └─ YES → README.md (in root - ONLY .md file allowed in root!)
│  ├─ License?
│  │  └─ YES → LICENSE (in root)
│  └─ Other docs (deployment, guides, changelog)?
│     └─ YES → docs/FILENAME.md
│
├─ Is it a web asset (CSS/JS/HTML)?
│  └─ YES → src/web/static/ or src/web/templates/
│
├─ Is it a dependency/config file (requirements, Docker)?
│  └─ YES → filename.txt/yml (in root)
│
└─ Is it a runtime artifact (logs, videos)?
   └─ YES → logs/ or recordings/ (gitignored)
```

---

## Common Mistakes to Avoid

### ❌ Mistake #1: Source Code in Root

```python
# WRONG!
ptz_controller.py                  # Should be src/camera/ptz_controller.py
object_detector.py                 # Should be src/ai/object_detector.py
main.py                            # Should be src/main.py
```

### ❌ Mistake #2: Tests in Source Code

```python
# WRONG!
src/camera/test_ptz_controller.py # Should be tests/unit/test_ptz_controller.py
src/ai/test_detector.py            # Should be tests/unit/test_object_detector.py
```

### ❌ Mistake #3: Config Files Everywhere

```yaml
# WRONG!
camera_config.yaml                 # In root - should be config/
src/camera/config.yaml             # In source - should be config/
```

### ❌ Mistake #4: Scattered Documentation

```markdown
# WRONG!
DEPLOYMENT.md                      # In root - should be docs/DEPLOYMENT.md
camera_setup.md                    # In root - should be docs/CAMERA_SETUP.md
CHANGELOG.md                       # In root - should be docs/CHANGELOG.md
src/docs/api.md                    # In source - should be docs/API.md

# RIGHT!
README.md                          # In root - ONLY .md file in root
LICENSE                            # In root - license file
docs/DEPLOYMENT.md                 # Extended docs in docs/
docs/CAMERA_SETUP.md               # Extended docs in docs/
docs/CHANGELOG.md                  # Extended docs in docs/
```

### ❌ Mistake #5: Web Assets in Root

```
# WRONG!
static/                            # Should be src/web/static/
templates/                         # Should be src/web/templates/
css/                               # Should be src/web/static/css/
```

---

## Folder Creation Rules

### Rule 1: Create Subfolders When Needed

If a module grows beyond 3-4 files, create subfolders:

```python
# Before (small module)
src/camera/
├── ptz_controller.py
└── preset_manager.py

# After (growing module)
src/camera/
├── __init__.py
├── ptz/
│   ├── __init__.py
│   ├── controller.py
│   └── preset_manager.py
└── discovery/
    ├── __init__.py
    └── onvif_client.py
```

### Rule 2: Mirror Structure in Tests

```python
# Source structure
src/
├── camera/
│   ├── ptz_controller.py
│   └── preset_manager.py
└── ai/
    └── object_detector.py

# Test structure (mirrored)
tests/
├── unit/
│   ├── test_ptz_controller.py
│   ├── test_preset_manager.py
│   └── test_object_detector.py
```

### Rule 3: Use `__init__.py` for Packages

```python
# src/camera/__init__.py
"""Camera control package."""

from .ptz_controller import PTZController
from .preset_manager import PresetManager

__all__ = ['PTZController', 'PresetManager']
```

### Rule 4: Keep Runtime Artifacts Separate

```python
# These folders are for OUTPUT only
logs/          # Created by application
recordings/    # Created by application

# NOT for:
logs/app.py    # Wrong - source code doesn't go here
```

---

## Import Patterns

### ✅ Good - Absolute Imports

```python
# src/main.py
from src.camera import PTZController
from src.ai import ObjectDetector
from src.automation import TrackingEngine

# src/automation/tracking_engine.py
from src.camera.ptz_controller import PTZController
from src.ai.object_detector import ObjectDetector
```

### ❌ Avoid - Relative Imports Across Modules

```python
# src/automation/tracking_engine.py
from ..camera.ptz_controller import PTZController  # Fragile
from ..ai.object_detector import ObjectDetector    # Hard to refactor
```

### ⚠️ OK - Relative Imports Within Same Module

```python
# src/camera/preset_manager.py
from .ptz_controller import PTZController  # OK - same module
```

---

## Quick Reference Checklist

Before creating a file, verify:

- [ ] Is the root directory clean? (No source code files)
- [ ] Is the file in the correct subfolder?
- [ ] Does the subfolder have `__init__.py`? (for Python packages)
- [ ] Are tests separate from source code?
- [ ] Are configs separate from source code?
- [ ] Are docs in `docs/` (not root, unless README/LICENSE)?
- [ ] Are web assets in `src/web/static/` or `src/web/templates/`?
- [ ] Will runtime files be gitignored?

---

## Examples: Before and After

### Before (Messy Root) ❌

```
security-video-automation/
├── main.py
├── ptz_controller.py
├── object_detector.py
├── tracking_engine.py
├── app.py
├── test_ptz.py
├── camera_config.yaml
├── style.css
├── dashboard.html
├── DEPLOYMENT.md           ← Should be in docs/
├── camera_setup.md         ← Should be in docs/
├── CHANGELOG.md            ← Should be in docs/
├── sample_video.mp4
├── app.log
├── README.md               ← Only .md that belongs in root
└── requirements.txt
```

### After (Clean Organization) ✅

```
security-video-automation/
├── src/
│   ├── main.py
│   ├── camera/
│   │   └── ptz_controller.py
│   ├── ai/
│   │   └── object_detector.py
│   ├── automation/
│   │   └── tracking_engine.py
│   └── web/
│       ├── app.py
│       ├── static/
│       │   ├── css/
│       │   │   └── style.css
│       │   └── demo/
│       │       └── sample_video.mp4
│       └── templates/
│           └── dashboard.html
├── tests/
│   └── unit/
│       └── test_ptz_controller.py
├── config/
│   └── camera_config.yaml
├── docs/
│   ├── DEPLOYMENT.md          ← Extended docs here
│   ├── CAMERA_SETUP.md
│   └── CHANGELOG.md
├── logs/
│   ├── .gitkeep
│   └── app.log (gitignored)
├── README.md                  ← ONLY .md in root
└── requirements.txt
```

---

## Summary

**Golden Rules:**
1. 🧹 **Keep root clean** - Only config/deps/deploy files + README.md
2. 📁 **Organize by purpose** - src, tests, config, scripts, docs
3. � **ONE .md file in root** - README.md only! Rest go in docs/
4. �🐍 **Use `__init__.py`** - Every Python package folder
5. 🔍 **Mirror test structure** - Match src/ in tests/
6. 🚫 **Separate concerns** - Config ≠ Code ≠ Tests ≠ Docs

**Root Directory:**
- ✅ README.md (ONLY markdown file allowed in root!)
- ✅ LICENSE, .gitignore, requirements.txt, Dockerfile, render.yaml
- ❌ DEPLOYMENT.md (→ docs/)
- ❌ CHANGELOG.md (→ docs/)
- ❌ Any .py files (→ src/ or scripts/)
- ❌ Any other .md files (→ docs/)

**When in doubt:** Ask "If someone clones this repo, will they know where everything is?"

---

**Need help?** Check the decision tree or refer to `.github/copilot-instructions.md`
