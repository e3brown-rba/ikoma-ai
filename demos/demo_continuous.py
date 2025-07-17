#!/usr/bin/env python3
"""Demo script for continuous batch processing scenario."""

import os
import subprocess
import sys


def main():
    os.environ["LMSTUDIO_MODEL"] = "meta-llama-3-8b-instruct"
    cmd = [sys.executable, "-m", "agent.agent", "--demo", "continuous"]
    print("🎬 Launching Continuous Batch Processing Demo")
    print("=" * 60)
    print("This demo will:")
    print("• Count word frequencies across .md files")
    print("• Write word_freq.csv")
    print("• Run for multiple iterations")
    print("• Demonstrate checkpoint recovery")
    print("• Work entirely offline")
    print("=" * 60)
    print("Press Ctrl+C to stop the demo.")
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n\nDemo stopped by user.")


if __name__ == "__main__":
    main()
