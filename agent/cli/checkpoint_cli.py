import argparse
import os
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

from agent.checkpointer import get_checkpointer_service


def create_checkpoint_parser() -> argparse.ArgumentParser:
    """Create the checkpoint subcommand parser."""
    parser = argparse.ArgumentParser(
        prog="ikoma checkpoint",
        description="Manage conversation checkpoints",
        add_help=False,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List command
    list_parser = subparsers.add_parser(
        "list",
        help="List all checkpoint runs",
        add_help=False,
    )
    list_parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of runs to show (default: 50)",
    )

    # Show command
    show_parser = subparsers.add_parser(
        "show",
        help="Show details for a specific run",
        add_help=False,
    )
    show_parser.add_argument(
        "run_id",
        help="Run ID to show details for",
    )
    show_parser.add_argument(
        "--steps",
        action="store_true",
        help="Show individual step details",
    )

    # Remove command
    rm_parser = subparsers.add_parser(
        "rm",
        help="Remove a specific run",
        add_help=False,
    )
    rm_parser.add_argument(
        "run_id",
        help="Run ID to remove",
    )
    rm_parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt",
    )

    # Clear all command
    clear_parser = subparsers.add_parser(
        "clear-all",
        help="Remove all checkpoint runs",
        add_help=False,
    )
    clear_parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt",
    )

    return parser


def get_db_path() -> str:
    """Get the database path from environment or default."""
    return os.getenv("CONVERSATION_DB_PATH", "agent/memory/conversations.sqlite")


def list_runs(limit: int = 50) -> None:
    """List all checkpoint runs with Rich formatting."""
    console = Console()
    db_path = get_db_path()

    if not Path(db_path).exists():
        console.print("[yellow]No checkpoint database found.[/yellow]")
        return

    try:
        # Get all runs by querying the database directly
        import sqlite3

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT DISTINCT run_id, COUNT(*) as step_count, "
            "MIN(ts) as first_step, MAX(ts) as last_step "
            "FROM conversation_steps "
            "GROUP BY run_id "
            "ORDER BY last_step DESC "
            "LIMIT ?",
            (limit,),
        )
        runs = cursor.fetchall()
        conn.close()

        if not runs:
            console.print("[yellow]No checkpoint runs found.[/yellow]")
            return

        # Create table
        table = Table(title="Checkpoint Runs")
        table.add_column("Run ID", style="cyan", no_wrap=True)
        table.add_column("Steps", justify="right", style="green")
        table.add_column("First Step", style="blue")
        table.add_column("Last Step", style="blue")

        for run_id, step_count, first_step, last_step in runs:
            table.add_row(
                run_id, str(step_count), first_step or "N/A", last_step or "N/A"
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error listing runs: {e}[/red]")
        sys.exit(1)


def show_run(run_id: str, show_steps: bool = False) -> None:
    """Show details for a specific run."""
    console = Console()
    db_path = get_db_path()

    if not Path(db_path).exists():
        console.print("[yellow]No checkpoint database found.[/yellow]")
        return

    try:
        service = get_checkpointer_service(db_path)
        records = service.get_steps(run_id)

        if not records:
            console.print(f"[yellow]No checkpoint found for run: {run_id}[/yellow]")
            return

        # Show run summary
        console.print(f"[bold cyan]Run ID:[/bold cyan] {run_id}")
        console.print(f"[bold green]Total Steps:[/bold green] {len(records)}")
        console.print(f"[bold blue]First Step:[/bold blue] {records[0].created_at}")
        console.print(f"[bold blue]Last Step:[/bold blue] {records[-1].created_at}")

        if show_steps:
            console.print("\n[bold]Step Details:[/bold]")
            for record in records:
                console.print(
                    f"\n[cyan]Step {record.step}[/cyan] ({record.created_at})"
                )
                console.print(f"State keys: {list(record.state.keys())}")

                # Show a preview of the state
                if "tool_calls" in record.state:
                    tool_calls = record.state["tool_calls"]
                    if isinstance(tool_calls, list) and tool_calls:
                        console.print(f"Tool calls: {len(tool_calls)}")
                        for i, call in enumerate(tool_calls[:3]):  # Show first 3
                            if isinstance(call, dict):
                                name = call.get("name", "unknown")
                                console.print(f"  {i + 1}. {name}")
                        if len(tool_calls) > 3:
                            console.print(f"  ... and {len(tool_calls) - 3} more")

    except Exception as e:
        console.print(f"[red]Error showing run: {e}[/red]")
        sys.exit(1)


def remove_run(run_id: str, force: bool = False) -> None:
    """Remove a specific run."""
    console = Console()
    db_path = get_db_path()

    if not Path(db_path).exists():
        console.print("[yellow]No checkpoint database found.[/yellow]")
        return

    try:
        service = get_checkpointer_service(db_path)

        # Check if run exists
        records = service.get_steps(run_id)
        if not records:
            console.print(f"[yellow]No checkpoint found for run: {run_id}[/yellow]")
            return

        # Confirm deletion
        if not force:
            console.print(f"[yellow]About to delete run: {run_id}[/yellow]")
            console.print(f"[yellow]This will remove {len(records)} steps.[/yellow]")
            response = input("Continue? (y/N): ").strip().lower()
            if response not in ["y", "yes"]:
                console.print("[yellow]Deletion cancelled.[/yellow]")
                return

        # Delete the run
        service.delete_run(run_id)
        console.print(f"[green]Successfully deleted run: {run_id}[/green]")

    except Exception as e:
        console.print(f"[red]Error removing run: {e}[/red]")
        sys.exit(1)


def clear_all_runs(force: bool = False) -> None:
    """Remove all checkpoint runs."""
    console = Console()
    db_path = get_db_path()

    if not Path(db_path).exists():
        console.print("[yellow]No checkpoint database found.[/yellow]")
        return

    try:
        # Get run count first
        import sqlite3

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(DISTINCT run_id) FROM conversation_steps")
        run_count = cursor.fetchone()[0]
        conn.close()

        if run_count == 0:
            console.print("[yellow]No checkpoint runs found.[/yellow]")
            return

        # Confirm deletion
        if not force:
            console.print(
                f"[yellow]About to delete ALL checkpoint runs ({run_count} runs).[/yellow]"
            )
            console.print("[red]This action cannot be undone![/red]")
            response = input("Type 'DELETE ALL' to confirm: ").strip()
            if response != "DELETE ALL":
                console.print("[yellow]Deletion cancelled.[/yellow]")
                return

        # Delete all runs
        service = get_checkpointer_service(db_path)

        # Get all run IDs
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT run_id FROM conversation_steps")
        run_ids = [row[0] for row in cursor.fetchall()]
        conn.close()

        # Delete each run
        for run_id in run_ids:
            service.delete_run(run_id)

        console.print(f"[green]Successfully deleted {len(run_ids)} runs.[/green]")

    except Exception as e:
        console.print(f"[red]Error clearing all runs: {e}[/red]")
        sys.exit(1)


def main(args: list[str] | None = None) -> None:
    """Main entry point for checkpoint CLI."""
    parser = create_checkpoint_parser()
    parsed_args = parser.parse_args(args)

    if not parsed_args.command:
        parser.print_help()
        sys.exit(1)

    if parsed_args.command == "list":
        list_runs(parsed_args.limit)
    elif parsed_args.command == "show":
        show_run(parsed_args.run_id, parsed_args.steps)
    elif parsed_args.command == "rm":
        remove_run(parsed_args.run_id, parsed_args.force)
    elif parsed_args.command == "clear-all":
        clear_all_runs(parsed_args.force)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
