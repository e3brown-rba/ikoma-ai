"""UI utilities for human interaction in continuous mode."""

import sys
from typing import Any

from rich.console import Console
from rich.panel import Panel


def prompt_user_confirm(state: Any) -> bool:
    """Prompt the user for confirmation to continue in continuous mode.

    Args:
        state: The current agent state containing reflection and iteration info

    Returns:
        True if user wants to continue, False if user wants to stop
    """
    # Check if we're in an interactive terminal
    if not sys.stdin.isatty():
        # Non-interactive environment (CI, etc.) - auto-continue
        print("⚠️  Non-interactive environment detected - auto-continuing...")
        return True

    console = Console()

    # Extract relevant information from state
    current_iteration = state.get("current_iteration", 0)
    reflection = state.get("reflection", "No reflection available")
    goal = ""
    if state.get("messages"):
        # Get the original goal from the first message
        for msg in state["messages"]:
            if hasattr(msg, "content") and msg.content:
                goal = msg.content
                break

    # Create a summary panel
    summary_text = f"""Iteration: {current_iteration}

Goal: {goal}

Latest Reflection:
{reflection}

Do you want to continue with the next iteration?"""

    panel = Panel(
        summary_text, title="🤖 iKOMA Checkpoint", border_style="yellow", padding=(1, 2)
    )

    console.print(panel)

    # Get user input with default to continue
    while True:
        try:
            response = input("Continue? [Y/n]: ").strip().lower()
            if response in ["", "y", "yes"]:
                return True
            elif response in ["n", "no"]:
                return False
            else:
                console.print(
                    "[red]Please enter 'y' or 'n' (or press Enter for yes)[/red]"
                )
        except (EOFError, KeyboardInterrupt):
            # Handle Ctrl+C or Ctrl+D gracefully
            console.print("\n[yellow]Received interrupt - stopping execution[/yellow]")
            return False
