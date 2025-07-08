#!/usr/bin/env python3
"""
iKOMA Agent Runner
Ensures proper environment setup and runs the agent
"""

import os
import sys
import subprocess
from pathlib import Path


def main():
    # Get the project root directory
    project_root = Path(__file__).parent
    venv_path = project_root / "venv"
    agent_path = project_root / "agent" / "agent.py"

    # Check if virtual environment exists
    if not venv_path.exists():
        print("❌ Virtual environment not found at:", venv_path)
        print("Please run: ./setup.sh to create the virtual environment")
        return 1

    # Check if agent file exists
    if not agent_path.exists():
        print("❌ Agent file not found at:", agent_path)
        return 1

    # Determine the correct Python executable
    if os.name == "nt":  # Windows
        python_exe = venv_path / "Scripts" / "python.exe"
    else:  # Unix-like
        python_exe = venv_path / "bin" / "python"

    if not python_exe.exists():
        print("❌ Python executable not found at:", python_exe)
        return 1

    print("🚀 Starting iKOMA Agent...")
    print(f"Using Python: {python_exe}")
    print(f"Running: {agent_path}")
    print("-" * 50)

    # Set up environment variables for the subprocess
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root)

    # Run the agent
    try:
        subprocess.run([str(python_exe), str(agent_path)], check=True, env=env)
    except subprocess.CalledProcessError as e:
        print(f"❌ Agent failed with exit code: {e.returncode}")
        return e.returncode
    except KeyboardInterrupt:
        print("\n👋 Agent stopped by user")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
