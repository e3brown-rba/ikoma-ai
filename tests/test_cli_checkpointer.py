import tempfile
from unittest.mock import patch

import pytest

from agent.cli.checkpoint_cli import (
    clear_all_runs,
    create_checkpoint_parser,
    get_db_path,
    list_runs,
    main,
    remove_run,
    show_run,
)


class TestCheckpointCLI:
    """Test the checkpoint CLI functionality."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path for testing."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
            return tmp.name

    def test_create_checkpoint_parser(self):
        """Test that the parser is created with all expected subcommands."""
        parser = create_checkpoint_parser()

        # Check that subcommands exist
        subcommands = [
            action.dest for action in parser._actions if hasattr(action, "dest")
        ]
        assert "command" in subcommands

        # Check that help text is set
        assert parser.description == "Manage conversation checkpoints"

    def test_get_db_path_default(self):
        """Test get_db_path returns default when env var not set."""
        with patch.dict("os.environ", {}, clear=True):
            path = get_db_path()
            assert path == "agent/memory/conversations.sqlite"

    def test_get_db_path_custom(self):
        """Test get_db_path returns custom path when env var is set."""
        custom_path = "/custom/path/conversations.sqlite"
        with patch.dict("os.environ", {"CONVERSATION_DB_PATH": custom_path}):
            path = get_db_path()
            assert path == custom_path

    def test_list_runs_no_database(self, capsys):
        """Test list_runs when database doesn't exist."""
        with patch("pathlib.Path.exists", return_value=False):
            list_runs()
            captured = capsys.readouterr()
            assert "No checkpoint database found" in captured.out

    def test_show_run_no_database(self, capsys):
        """Test show_run when database doesn't exist."""
        with patch("pathlib.Path.exists", return_value=False):
            show_run("test-run-id")
            captured = capsys.readouterr()
            assert "No checkpoint database found" in captured.out

    def test_remove_run_no_database(self, capsys):
        """Test remove_run when database doesn't exist."""
        with patch("pathlib.Path.exists", return_value=False):
            remove_run("test-run-id")
            captured = capsys.readouterr()
            assert "No checkpoint database found" in captured.out

    def test_clear_all_runs_no_database(self, capsys):
        """Test clear_all_runs when database doesn't exist."""
        with patch("pathlib.Path.exists", return_value=False):
            clear_all_runs()
            captured = capsys.readouterr()
            assert "No checkpoint database found" in captured.out

    def test_main_no_command(self, capsys):
        """Test main function with no command specified."""
        with patch("sys.argv", ["ikoma", "checkpoint"]):
            with patch("sys.exit") as mock_exit:
                main()
                mock_exit.assert_called_with(1)

    def test_main_list_command(self):
        """Test main function with list command."""
        with patch("sys.argv", ["ikoma", "list"]):
            with patch("agent.cli.checkpoint_cli.list_runs") as mock_list:
                with patch("sys.exit") as mock_exit:
                    main()
                    mock_list.assert_called_once()
                    mock_exit.assert_not_called()

    def test_main_show_command(self):
        """Test main function with show command."""
        with patch("sys.argv", ["ikoma", "show", "test-run-id"]):
            with patch("agent.cli.checkpoint_cli.show_run") as mock_show:
                with patch("sys.exit") as mock_exit:
                    main()
                    mock_show.assert_called_once_with("test-run-id", False)
                    mock_exit.assert_not_called()

    def test_main_show_command_with_steps(self):
        """Test main function with show command and --steps flag."""
        with patch("sys.argv", ["ikoma", "show", "test-run-id", "--steps"]):
            with patch("agent.cli.checkpoint_cli.show_run") as mock_show:
                with patch("sys.exit") as mock_exit:
                    main()
                    mock_show.assert_called_once_with("test-run-id", True)
                    mock_exit.assert_not_called()

    def test_main_rm_command(self):
        """Test main function with rm command."""
        with patch("sys.argv", ["ikoma", "rm", "test-run-id"]):
            with patch("agent.cli.checkpoint_cli.remove_run") as mock_rm:
                with patch("sys.exit") as mock_exit:
                    main()
                    mock_rm.assert_called_once_with("test-run-id", False)
                    mock_exit.assert_not_called()

    def test_main_rm_command_with_force(self):
        """Test main function with rm command and --force flag."""
        with patch("sys.argv", ["ikoma", "rm", "test-run-id", "--force"]):
            with patch("agent.cli.checkpoint_cli.remove_run") as mock_rm:
                with patch("sys.exit") as mock_exit:
                    main()
                    mock_rm.assert_called_once_with("test-run-id", True)
                    mock_exit.assert_not_called()

    def test_main_clear_all_command(self):
        """Test main function with clear-all command."""
        with patch("sys.argv", ["ikoma", "clear-all"]):
            with patch("agent.cli.checkpoint_cli.clear_all_runs") as mock_clear:
                with patch("sys.exit") as mock_exit:
                    main()
                    mock_clear.assert_called_once_with(False)
                    mock_exit.assert_not_called()

    def test_main_clear_all_command_with_force(self):
        """Test main function with clear-all command and --force flag."""
        with patch("sys.argv", ["ikoma", "clear-all", "--force"]):
            with patch("agent.cli.checkpoint_cli.clear_all_runs") as mock_clear:
                with patch("sys.exit") as mock_exit:
                    main()
                    mock_clear.assert_called_once_with(True)
                    mock_exit.assert_not_called()


class TestCheckpointCLIWithDatabase:
    """Test CLI functionality with actual database operations."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path for testing."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
            return tmp.name

    def test_list_runs_with_data(self, temp_db_path, capsys):
        """Test list_runs with actual database data."""
        # Create some test data in the database
        import sqlite3

        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        # Create the table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_steps (
                run_id TEXT NOT NULL,
                step INTEGER NOT NULL,
                tool_calls TEXT NOT NULL,
                ts TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (run_id, step)
            )
        """)

        # Insert test data
        cursor.execute(
            "INSERT INTO conversation_steps (run_id, step, tool_calls, ts) VALUES (?, ?, ?, ?)",
            ("test-run-1", 1, '{"test": "data1"}', "2024-01-01T10:00:00"),
        )
        cursor.execute(
            "INSERT INTO conversation_steps (run_id, step, tool_calls, ts) VALUES (?, ?, ?, ?)",
            ("test-run-1", 2, '{"test": "data2"}', "2024-01-01T11:00:00"),
        )
        cursor.execute(
            "INSERT INTO conversation_steps (run_id, step, tool_calls, ts) VALUES (?, ?, ?, ?)",
            ("test-run-2", 1, '{"test": "data3"}', "2024-01-01T12:00:00"),
        )
        conn.commit()
        conn.close()

        # Test list_runs
        with patch("agent.cli.checkpoint_cli.get_db_path", return_value=temp_db_path):
            list_runs()
            captured = capsys.readouterr()

            # Should show the runs
            assert "test-run-1" in captured.out
            assert "test-run-2" in captured.out
            assert "2" in captured.out  # test-run-1 has 2 steps
            assert "1" in captured.out  # test-run-2 has 1 step

    def test_show_run_with_data(self, temp_db_path, capsys):
        """Test show_run with actual database data."""
        # Create test data
        import sqlite3

        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_steps (
                run_id TEXT NOT NULL,
                step INTEGER NOT NULL,
                tool_calls TEXT NOT NULL,
                ts TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (run_id, step)
            )
        """)

        cursor.execute(
            "INSERT INTO conversation_steps (run_id, step, tool_calls, ts) VALUES (?, ?, ?, ?)",
            (
                "test-run-show",
                1,
                '{"tool_calls": [{"name": "test_tool"}]}',
                "2024-01-01T10:00:00",
            ),
        )
        conn.commit()
        conn.close()

        # Test show_run
        with patch("agent.cli.checkpoint_cli.get_db_path", return_value=temp_db_path):
            show_run("test-run-show")
            captured = capsys.readouterr()

            assert "test-run-show" in captured.out
            assert "Total Steps: 1" in captured.out

    def test_show_run_nonexistent(self, temp_db_path, capsys):
        """Test show_run with non-existent run."""
        # Create empty database
        import sqlite3

        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_steps (
                run_id TEXT NOT NULL,
                step INTEGER NOT NULL,
                tool_calls TEXT NOT NULL,
                ts TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (run_id, step)
            )
        """)
        conn.commit()
        conn.close()

        # Test show_run with non-existent run
        with patch("agent.cli.checkpoint_cli.get_db_path", return_value=temp_db_path):
            show_run("nonexistent-run")
            captured = capsys.readouterr()

            assert "No checkpoint found for run: nonexistent-run" in captured.out

    def test_remove_run_with_data(self, temp_db_path, capsys):
        """Test remove_run with actual database data."""
        # Create test data
        import sqlite3

        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_steps (
                run_id TEXT NOT NULL,
                step INTEGER NOT NULL,
                tool_calls TEXT NOT NULL,
                ts TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (run_id, step)
            )
        """)

        cursor.execute(
            "INSERT INTO conversation_steps (run_id, step, tool_calls, ts) VALUES (?, ?, ?, ?)",
            ("test-run-remove", 1, '{"test": "data"}', "2024-01-01T10:00:00"),
        )
        conn.commit()
        conn.close()

        # Test remove_run with force
        with patch("agent.cli.checkpoint_cli.get_db_path", return_value=temp_db_path):
            remove_run("test-run-remove", force=True)
            captured = capsys.readouterr()

            assert "Successfully deleted run: test-run-remove" in captured.out

    def test_remove_run_nonexistent(self, temp_db_path, capsys):
        """Test remove_run with non-existent run."""
        # Create empty database
        import sqlite3

        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_steps (
                run_id TEXT NOT NULL,
                step INTEGER NOT NULL,
                tool_calls TEXT NOT NULL,
                ts TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (run_id, step)
            )
        """)
        conn.commit()
        conn.close()

        # Test remove_run with non-existent run
        with patch("agent.cli.checkpoint_cli.get_db_path", return_value=temp_db_path):
            remove_run("nonexistent-run")
            captured = capsys.readouterr()

            assert "No checkpoint found for run: nonexistent-run" in captured.out

    def test_clear_all_runs_with_data(self, temp_db_path, capsys):
        """Test clear_all_runs with actual database data."""
        # Create test data
        import sqlite3

        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_steps (
                run_id TEXT NOT NULL,
                step INTEGER NOT NULL,
                tool_calls TEXT NOT NULL,
                ts TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (run_id, step)
            )
        """)

        cursor.execute(
            "INSERT INTO conversation_steps (run_id, step, tool_calls, ts) VALUES (?, ?, ?, ?)",
            ("test-run-1", 1, '{"test": "data1"}', "2024-01-01T10:00:00"),
        )
        cursor.execute(
            "INSERT INTO conversation_steps (run_id, step, tool_calls, ts) VALUES (?, ?, ?, ?)",
            ("test-run-2", 1, '{"test": "data2"}', "2024-01-01T11:00:00"),
        )
        conn.commit()
        conn.close()

        # Test clear_all_runs with force
        with patch("agent.cli.checkpoint_cli.get_db_path", return_value=temp_db_path):
            clear_all_runs(force=True)
            captured = capsys.readouterr()

            assert "Successfully deleted 2 runs" in captured.out

    def test_clear_all_runs_empty(self, temp_db_path, capsys):
        """Test clear_all_runs with empty database."""
        # Create empty database
        import sqlite3

        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_steps (
                run_id TEXT NOT NULL,
                step INTEGER NOT NULL,
                tool_calls TEXT NOT NULL,
                ts TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (run_id, step)
            )
        """)
        conn.commit()
        conn.close()

        # Test clear_all_runs with empty database
        with patch("agent.cli.checkpoint_cli.get_db_path", return_value=temp_db_path):
            clear_all_runs()
            captured = capsys.readouterr()

            assert "No checkpoint runs found" in captured.out


class TestCheckpointCLIErrorHandling:
    """Test CLI error handling."""

    def test_list_runs_database_error(self, capsys):
        """Test list_runs handles database errors gracefully."""
        with patch(
            "agent.cli.checkpoint_cli.get_db_path",
            return_value="/nonexistent/path/db.sqlite",
        ):
            with patch("pathlib.Path.exists", return_value=True):
                with pytest.raises(SystemExit) as exc_info:
                    list_runs()
                assert exc_info.value.code == 1
                captured = capsys.readouterr()
                assert "Error listing runs" in captured.out

    def test_show_run_database_error(self, capsys):
        """Test show_run handles database errors gracefully."""
        with patch(
            "agent.cli.checkpoint_cli.get_db_path",
            return_value="/nonexistent/path/db.sqlite",
        ):
            with patch("pathlib.Path.exists", return_value=True):
                with pytest.raises(SystemExit) as exc_info:
                    show_run("test-run")
                assert exc_info.value.code == 1
                captured = capsys.readouterr()
                assert "Error showing run" in captured.out

    def test_remove_run_database_error(self, capsys):
        """Test remove_run handles database errors gracefully."""
        with patch(
            "agent.cli.checkpoint_cli.get_db_path",
            return_value="/nonexistent/path/db.sqlite",
        ):
            with patch("pathlib.Path.exists", return_value=True):
                with pytest.raises(SystemExit) as exc_info:
                    remove_run("test-run")
                assert exc_info.value.code == 1
                captured = capsys.readouterr()
                assert "Error removing run" in captured.out

    def test_clear_all_runs_database_error(self, capsys):
        """Test clear_all_runs handles database errors gracefully."""
        with patch(
            "agent.cli.checkpoint_cli.get_db_path",
            return_value="/nonexistent/path/db.sqlite",
        ):
            with patch("pathlib.Path.exists", return_value=True):
                with pytest.raises(SystemExit) as exc_info:
                    clear_all_runs()
                assert exc_info.value.code == 1
                captured = capsys.readouterr()
                assert "Error clearing all runs" in captured.out
