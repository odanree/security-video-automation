#!/usr/bin/env python3
"""Check GPU availability for YOLO detection"""

import torch
import sys

print("=" * 60)
print("GPU AVAILABILITY CHECK")
print("=" * 60)

# Check PyTorch GPU support
print(f"\nPyTorch Version: {torch.__version__}")
print(f"CUDA Available: {torch.cuda.is_available()}")

if torch.cuda.is_available():
    print(f"CUDA Device: {torch.cuda.get_device_name(0)}")
    print(f"CUDA Capability: {torch.cuda.get_device_capability(0)}")
    print(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
else:
    print("✗ CUDA not available (NVIDIA GPU not detected or driver not installed)")

# Check for DirectML (AMD on Windows)
try:
    import torch_directml
    print(f"\n✓ DirectML available (AMD GPU acceleration)")
    dml_device = torch_directml.device()
    print(f"  DirectML Device: {dml_device}")
except ImportError:
    print(f"\n✗ DirectML not available")

# Check for AMD ROCm
try:
    import torch.utils.hip
    print(f"✓ ROCm/HIP available: {torch.utils.hip.is_available()}")
except:
    print(f"✗ ROCm/HIP not available")

# Check CPU info
print(f"\nCPU Threads: {torch.get_num_threads()}")

# Try YOLO
print("\n" + "=" * 60)
print("Testing YOLO with available device...")
print("=" * 60)

try:
    from ultralytics import YOLO
    
    model = YOLO('yolov8n.pt')
    
    # Determine device
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    try:
        import torch_directml
        device = torch_directml.device()
        print(f"\n✓ YOLO will use DirectML (AMD GPU)")
    except:
        pass
    
    print(f"✓ YOLO loaded successfully")
    print(f"Using device: {device}")
    
    # Quick inference test
    import numpy as np
    test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    results = model(test_frame, verbose=False, device=device)
    print(f"✓ Inference test passed")
    
except Exception as e:
    print(f"✗ YOLO test failed: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
try:
    import torch_directml
    print("Summary: DirectML GPU acceleration ✓ AVAILABLE")
except:
    print("Summary: GPU acceleration", "✓ AVAILABLE" if torch.cuda.is_available() else "✗ NOT AVAILABLE (CPU mode)")
print("=" * 60)
