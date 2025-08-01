#!/usr/bin/env python3
"""Demo script to launch the agent with TUI enabled for a simple goal."""

import subprocess
import sys


def main():
    cmd = [
        sys.executable,
        "-m",
        "agent.agent",
        "--tui",
        "--continuous",
        "--goal",
        "List the files in the sandbox directory",
        "--max-iterations",
        "3",
        "--auto",
    ]
    print("🧪 Launching Ikoma agent with TUI...")
    print("Command:", " ".join(cmd))
    print("\nPress Ctrl+C to stop the demo.")
    try:
        subprocess.run(cmd, timeout=30)  # Add timeout to prevent hanging
    except (KeyboardInterrupt, subprocess.TimeoutExpired):
        print("\nDemo stopped by user or timeout.")


if __name__ == "__main__":
    main()
