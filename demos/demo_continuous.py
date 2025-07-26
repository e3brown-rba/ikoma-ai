#!/usr/bin/env python3
"""Demo script for continuous batch processing scenario."""

import os
import subprocess
import sys


def main():
    os.environ["LMSTUDIO_MODEL"] = "meta-llama-3-8b-instruct"
    cmd = [sys.executable, "-m", "agent.agent", "--demo", "continuous"]
    print("🎬 Launching Memory Operations & Retrieval Demo")
    print("=" * 60)
    print("This demo will:")
    print("• Create memory entries about Python best practices")
    print("• Create memory entries about web development tips")
    print("• Retrieve and summarize both memory entries")
    print("• Demonstrate memory operations and retrieval")
    print("• Work entirely offline")
    print("=" * 60)
    print("Press Ctrl+C to stop the demo.")
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n\nDemo stopped by user.")


if __name__ == "__main__":
    main()
