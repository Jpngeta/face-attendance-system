#!/usr/bin/env python3
"""
Quick test script for the web interface
"""
import requests

BASE_URL = "http://localhost:5000"

def test_endpoints():
    """Test various endpoints"""

    print("Testing Face Attendance System Web Interface")
    print("=" * 50)

    # Test health endpoint
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        print(f"✓ Health Check: {response.status_code}")
        if response.status_code == 200:
            print(f"  Response: {response.json()}")
    except Exception as e:
        print(f"✗ Health Check Failed: {e}")

    # Test home page
    try:
        response = requests.get(BASE_URL, timeout=5)
        print(f"✓ Home Page: {response.status_code}")
    except Exception as e:
        print(f"✗ Home Page Failed: {e}")

    # Test live recognition page
    try:
        response = requests.get(f"{BASE_URL}/live", timeout=5)
        print(f"✓ Live Recognition Page: {response.status_code}")
    except Exception as e:
        print(f"✗ Live Recognition Page Failed: {e}")

    # Test recognition status
    try:
        response = requests.get(f"{BASE_URL}/api/recognition/status", timeout=5)
        print(f"✓ Recognition Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"  Status: {data.get('status')}")
    except Exception as e:
        print(f"✗ Recognition Status Failed: {e}")

    # Test active session
    try:
        response = requests.get(f"{BASE_URL}/api/sessions/active", timeout=5)
        print(f"✓ Active Session Check: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"  Active Session: {data.get('session', {}).get('session_name')}")
        elif response.status_code == 404:
            print("  No active session found (expected if none created)")
    except Exception as e:
        print(f"✗ Active Session Check Failed: {e}")

    print("\n" + "=" * 50)
    print("Testing complete!")
    print(f"\nAccess the web interface at: {BASE_URL}")
    print(f"Live Recognition page: {BASE_URL}/live")

if __name__ == "__main__":
    test_endpoints()
