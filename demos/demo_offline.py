#!/usr/bin/env python3
"""Demo script for offline repository intelligence scenario."""

import os
import subprocess
import sys


def main():
    os.environ["LMSTUDIO_MODEL"] = "meta-llama-3-8b-instruct"
    cmd = [sys.executable, "-m", "agent.agent", "--demo", "offline"]
    print("🎬 Launching Offline Repository Intelligence Demo")
    print("=" * 60)
    print("This demo will:")
    print("• Scan repo for TODO & FIXME comments")
    print("• Group comments by file")
    print("• Create docs/todo_report.md")
    print("• Schedule daily reminders")
    print("• Work entirely offline")
    print("=" * 60)
    print("Press Ctrl+C to stop the demo.")
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n\nDemo stopped by user.")


if __name__ == "__main__":
    main()
