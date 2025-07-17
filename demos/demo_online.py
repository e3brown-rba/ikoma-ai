#!/usr/bin/env python3
"""Demo script for online research & monitoring scenario."""

import os
import subprocess
import sys


def main():
    os.environ["LMSTUDIO_MODEL"] = "meta-llama-3-8b-instruct"
    cmd = [sys.executable, "-m", "agent.agent", "--demo", "online"]
    print("🎬 Launching Online Research & Monitoring Demo")
    print("=" * 60)
    print("This demo will:")
    print("• Track EV tax credit policy proposals")
    print("• Use internet search and scraping")
    print("• Show safety filters and rate limiting")
    print("• Demonstrate memory storage and recall")
    print("• Schedule weekly automation")
    print("=" * 60)
    print("Press Ctrl+C to stop the demo.")
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n\nDemo stopped by user.")


if __name__ == "__main__":
    main()
