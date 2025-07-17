#!/usr/bin/env python3
"""Demo script to launch the agent with the --demo flag for the EV tax credits scenario."""

import os
import subprocess
import sys


def main():
    os.environ["LMSTUDIO_MODEL"] = "meta-llama-3-8b-instruct"
    cmd = [sys.executable, "-m", "agent.agent", "--demo"]
    print("🎬 Launching Ikoma Demo Mode")
    print("=" * 60)
    print("This demo will:")
    print("• Pre-load the EV tax credits tracking task")
    print("• Enable TUI for real-time monitoring")
    print("• Run in continuous mode with auto-continue")
    print("• Show plan generation, execution, and reflection")
    print("=" * 60)
    print("Press Ctrl+C to stop the demo.")
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n\nDemo stopped by user.")


if __name__ == "__main__":
    main()
