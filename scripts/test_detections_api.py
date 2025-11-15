#!/usr/bin/env python3
"""Test the detections API endpoint"""

import requests
import json
import time

BACKEND_URL = "http://localhost:8000"

def test_detections_endpoint():
    """Test the /api/detections/current endpoint"""
    
    print("=" * 60)
    print("Testing Detection API Endpoint")
    print("=" * 60)
    
    for i in range(5):
        try:
            print(f"\n[Request {i+1}] Fetching detections...")
            response = requests.get(f"{BACKEND_URL}/api/detections/current", timeout=2)
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Detections Returned: {len(data)}")
                
                if data:
                    print("\nDetection Data:")
                    for det in data:
                        print(f"  - Class: {det.get('class')}")
                        print(f"    BBox: {det.get('bbox')}")
                        print(f"    Confidence: {det.get('confidence'):.2f}")
                else:
                    print("  (No detections returned)")
            else:
                print(f"Error: {response.text}")
                
        except Exception as e:
            print(f"Error: {e}")
        
        time.sleep(1)

if __name__ == "__main__":
    test_detections_endpoint()
