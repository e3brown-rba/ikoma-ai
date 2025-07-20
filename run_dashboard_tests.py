#!/usr/bin/env python3
"""
Script to run dashboard tests locally.
These tests require a running dashboard server.
"""

import subprocess
import sys


def main():
    """Run dashboard tests with server setup instructions."""
    print("🧪 Dashboard Test Runner")
    print("=" * 50)

    print("\n📋 Prerequisites:")
    print("   1. Start the dashboard server:")
    print("      uvicorn dashboard.app:app --reload --port 8000")
    print("   2. Ensure the server is running on http://localhost:8000")
    print("   3. The server should be accessible and responding")

    print("\n🔍 Checking if dashboard server is running...")

    try:
        import requests

        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Dashboard server is running!")
        else:
            print("❌ Dashboard server responded with status:", response.status_code)
            print("\n   Please start the dashboard server first:")
            print("   uvicorn dashboard.app:app --reload --port 8000")
            print("\n   Then run this script again.")
            return 1
    except Exception as e:
        print("❌ Could not connect to dashboard server:", e)
        print("\n   Please start the dashboard server first:")
        print("   uvicorn dashboard.app:app --reload --port 8000")
        print("\n   Then run this script again.")
        return 1

    print("\n🧪 Running dashboard tests...")
    print("=" * 50)

    # Run the dashboard tests
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-m", "dashboard", "-v"]
    )

    print("\n" + "=" * 50)
    if result.returncode == 0:
        print("✅ Dashboard tests passed!")
    else:
        print("❌ Dashboard tests failed!")

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
