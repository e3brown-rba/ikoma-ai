#!/usr/bin/env python3
"""Demo script for online research & monitoring scenario."""

import os
import subprocess
import sys


def main():
    os.environ["LMSTUDIO_MODEL"] = "meta-llama-3-8b-instruct"
    cmd = [sys.executable, "-m", "agent.agent", "--demo", "online"]
    print("🎬 Launching Simple Weather Fetch Demo")
    print("=" * 60)
    print("This demo will:")
    print("• Fetch current weather for New York City")
    print("• Create a simple weather summary")
    print("• Demonstrate basic web fetching")
    print("• Work with online data sources")
    print("=" * 60)
    print("Press Ctrl+C to stop the demo.")
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n\nDemo stopped by user.")


if __name__ == "__main__":
    main()
