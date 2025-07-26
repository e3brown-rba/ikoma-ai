#!/usr/bin/env python3
"""Demo script for offline repository intelligence scenario."""

import os
import subprocess
import sys


def main():
    os.environ["LMSTUDIO_MODEL"] = "meta-llama-3-8b-instruct"
    cmd = [sys.executable, "-m", "agent.agent", "--demo", "offline"]
    print("🎬 Launching Simple File Operations Demo")
    print("=" * 60)
    print("This demo will:")
    print("• Create a simple text file")
    print("• Read the file back to verify content")
    print("• Demonstrate basic file operations")
    print("• Work entirely offline")
    print("=" * 60)
    print("Press Ctrl+C to stop the demo.")
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n\nDemo stopped by user.")


if __name__ == "__main__":
    main()
