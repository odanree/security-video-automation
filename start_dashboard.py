#!/usr/bin/env python3
"""
Start Web Dashboard Server
Quick startup script for the security camera AI tracking dashboard
"""

import os
import sys
from pathlib import Path

# Add src directory to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

def main():
    """Start the web dashboard server"""
    try:
        import uvicorn
    except ImportError:
        print("❌ Error: uvicorn not installed")
        print("Install dependencies: pip install fastapi uvicorn jinja2 websockets")
        sys.exit(1)
    
    print("🚀 Starting Security Camera AI Dashboard...")
    print("📹 Camera controls and live monitoring")
    print("🌐 Access at: http://localhost:8000")
    print("Press Ctrl+C to stop\n")
    
    # Start server
    uvicorn.run(
        "web.app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disabled for stability
        log_level="info"
    )

if __name__ == "__main__":
    main()
