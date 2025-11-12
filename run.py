"""
Quick start script for Security Camera AI Tracking System
Provides a simple interface to run the tracking system
"""

import sys
import subprocess
from pathlib import Path

def main():
    """Run the tracking system with helpful prompts"""
    
    print("=" * 60)
    print("SECURITY CAMERA AI TRACKING SYSTEM")
    print("=" * 60)
    print()
    
    # Check if config files exist
    config_dir = Path("config")
    required_configs = [
        "camera_config.yaml",
        "tracking_rules.yaml",
        "ai_config.yaml"
    ]
    
    missing_configs = []
    for config_file in required_configs:
        if not (config_dir / config_file).exists():
            missing_configs.append(config_file)
    
    if missing_configs:
        print("❌ Missing configuration files:")
        for config in missing_configs:
            print(f"   - config/{config}")
        print()
        print("Please create the required configuration files before running.")
        sys.exit(1)
    
    print("✓ Configuration files found")
    print()
    
    # Ask user for options
    print("Run options:")
    print("  1. Run with video display (recommended for testing)")
    print("  2. Run headless (no video display)")
    print("  3. Run with video display for 60 seconds")
    print("  4. Run in debug mode (verbose logging + video)")
    print("  5. Run detection only (no PTZ control)")
    print()
    
    choice = input("Select option (1-5) [1]: ").strip() or "1"
    
    # Build command
    cmd = [sys.executable, "src/main.py"]
    
    if choice == "1":
        cmd.append("--display")
        print("\n▶ Running with video display...")
        print("Press 'q' to quit, 'p' to pause/resume, 's' for stats")
        
    elif choice == "2":
        print("\n▶ Running headless mode...")
        print("Press Ctrl+C to stop")
        
    elif choice == "3":
        cmd.extend(["--display", "--duration", "60"])
        print("\n▶ Running for 60 seconds with video display...")
        
    elif choice == "4":
        cmd.extend(["--display", "--log-level", "DEBUG"])
        print("\n▶ Running in debug mode...")
        
    elif choice == "5":
        cmd.extend(["--display", "--no-ptz"])
        print("\n▶ Running detection only (PTZ disabled)...")
        
    else:
        print(f"Invalid option: {choice}")
        sys.exit(1)
    
    print()
    print("Command:", " ".join(cmd))
    print()
    
    # Run the system
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n\nShutdown requested by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
