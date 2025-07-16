import tempfile

import pytest

from agent.checkpointer import IkomaCheckpointer


class TestIkomaCheckpointer:
    """Test suite for IkomaCheckpointer SQLite conversation state persistence."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path for testing."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
            return tmp.name

    @pytest.fixture
    def checkpointer(self, temp_db_path):
        """Create a checkpointer instance with temporary database."""
        return IkomaCheckpointer(temp_db_path)

    def test_initialization(self, temp_db_path):
        """Test checkpointer initialization with WAL mode."""
        cp = IkomaCheckpointer(temp_db_path)

        # Verify WAL mode is enabled
        cursor = cp._conn.cursor()
        cursor.execute("PRAGMA journal_mode;")
        journal_mode = cursor.fetchone()[0]
        assert journal_mode == "wal"

        # Verify user version is set
        cursor.execute("PRAGMA user_version;")
        user_version = cursor.fetchone()[0]
        assert user_version == 1

    def test_put_and_get(self, checkpointer):
        """Test basic put and get operations."""
        run_id = "test-run-123"
        step = 1
        tool_calls = {"tool_calls": [{"name": "noop", "args": {"test": "data"}}]}

        # Store data
        checkpointer.put_step(run_id, step, tool_calls)

        # Retrieve data
        result = checkpointer.get_step(run_id, step)
        assert result is not None
        assert result["tool_calls"][0]["name"] == "noop"
        assert result["tool_calls"][0]["args"]["test"] == "data"

    def test_list_steps(self, checkpointer):
        """Test listing all steps for a run_id."""
        run_id = "test-run-456"

        # Add multiple steps
        for step in [1, 3, 5]:
            tool_calls = {"tool_calls": [{"name": f"step_{step}"}]}
            checkpointer.put_step(run_id, step, tool_calls)

        # List steps
        steps = checkpointer.list_steps(run_id)
        assert set(steps) == {1, 3, 5}

    def test_delete_step(self, checkpointer):
        """Test deleting a specific step."""
        run_id = "test-run-789"
        step = 1
        tool_calls = {"tool_calls": [{"name": "to_delete"}]}

        # Store and verify
        checkpointer.put_step(run_id, step, tool_calls)
        assert checkpointer.get_step(run_id, step) is not None

        # Delete and verify
        checkpointer.delete_step(run_id, step)
        assert checkpointer.get_step(run_id, step) is None

    def test_clear_run(self, checkpointer):
        """Test clearing all steps for a run_id."""
        run_id = "test-run-clear"

        # Add multiple steps
        for step in [1, 2, 3]:
            tool_calls = {"tool_calls": [{"name": f"step_{step}"}]}
            checkpointer.put_step(run_id, step, tool_calls)

        # Verify steps exist
        assert len(checkpointer.list_steps(run_id)) == 3

        # Clear and verify
        checkpointer.clear_run(run_id)
        assert len(checkpointer.list_steps(run_id)) == 0

    def test_nonexistent_get(self, checkpointer):
        """Test getting non-existent data returns None."""
        result = checkpointer.get_step("nonexistent", 999)
        assert result is None

    def test_complex_tool_calls(self, checkpointer):
        """Test storing complex tool call structures."""
        run_id = "complex-test"
        step = 1
        tool_calls = {
            "tool_calls": [
                {
                    "name": "web_search",
                    "args": {"query": "test query", "limit": 5},
                    "metadata": {"source": "serpapi"},
                },
                {
                    "name": "file_read",
                    "args": {"path": "/tmp/test.txt"},
                    "metadata": {"sandbox": True},
                },
            ],
            "metadata": {"timestamp": "2024-01-01T00:00:00Z"},
        }

        checkpointer.put_step(run_id, step, tool_calls)
        result = checkpointer.get_step(run_id, step)

        assert result["tool_calls"][0]["name"] == "web_search"
        assert result["tool_calls"][0]["args"]["query"] == "test query"
        assert result["tool_calls"][1]["name"] == "file_read"
        assert result["metadata"]["timestamp"] == "2024-01-01T00:00:00Z"

    def test_multiple_runs(self, checkpointer):
        """Test isolation between different run_ids."""
        run1 = "run-1"
        run2 = "run-2"

        # Add data to both runs
        checkpointer.put_step(run1, 1, {"tool_calls": [{"name": "run1_step1"}]})
        checkpointer.put_step(run1, 2, {"tool_calls": [{"name": "run1_step2"}]})
        checkpointer.put_step(run2, 1, {"tool_calls": [{"name": "run2_step1"}]})

        # Verify isolation
        run1_steps = checkpointer.list_steps(run1)
        run2_steps = checkpointer.list_steps(run2)

        assert set(run1_steps) == {1, 2}
        assert set(run2_steps) == {1}

        # Verify data isolation
        run1_data = checkpointer.get_step(run1, 1)
        run2_data = checkpointer.get_step(run2, 1)
        assert run1_data is not None
        assert run2_data is not None
        assert run1_data["tool_calls"][0]["name"] == "run1_step1"
        assert run2_data["tool_calls"][0]["name"] == "run2_step1"

    def test_concurrent_access(self, temp_db_path):
        """Test that multiple checkpointer instances can access the same DB."""
        cp1 = IkomaCheckpointer(temp_db_path)
        cp2 = IkomaCheckpointer(temp_db_path)

        run_id = "concurrent-test"

        # Write from first instance
        cp1.put_step(run_id, 1, {"tool_calls": [{"name": "from_cp1"}]})

        # Read from second instance
        result = cp2.get_step(run_id, 1)
        assert result is not None
        assert result["tool_calls"][0]["name"] == "from_cp1"

        # Write from second instance
        cp2.put_step(run_id, 2, {"tool_calls": [{"name": "from_cp2"}]})

        # Read from first instance
        result = cp1.get_step(run_id, 2)
        assert result is not None
        assert result["tool_calls"][0]["name"] == "from_cp2"

    def test_large_payload(self, checkpointer):
        """Test handling of large tool call payloads."""
        run_id = "large-payload-test"
        step = 1

        # Create a large payload
        large_content = "x" * 10000  # 10KB of data
        tool_calls = {
            "tool_calls": [
                {
                    "name": "large_operation",
                    "args": {"content": large_content},
                    "metadata": {"size": len(large_content)},
                }
            ]
        }

        # Store and retrieve
        checkpointer.put_step(run_id, step, tool_calls)
        result = checkpointer.get_step(run_id, step)

        assert result["tool_calls"][0]["name"] == "large_operation"
        assert result["tool_calls"][0]["args"]["content"] == large_content
        assert result["tool_calls"][0]["metadata"]["size"] == 10000

    def test_json_serialization(self, checkpointer):
        """Test that all stored data is JSON serializable."""
        run_id = "json-test"
        step = 1

        # Test various data types that should be JSON serializable
        tool_calls = {
            "tool_calls": [
                {
                    "name": "test_operation",
                    "args": {
                        "string": "test",
                        "number": 42,
                        "float": 3.14,
                        "boolean": True,
                        "null": None,
                        "list": [1, 2, 3],
                        "dict": {"nested": "value"},
                    },
                }
            ]
        }

        checkpointer.put_step(run_id, step, tool_calls)
        result = checkpointer.get_step(run_id, step)

        # Verify all data types are preserved
        assert result["tool_calls"][0]["args"]["string"] == "test"
        assert result["tool_calls"][0]["args"]["number"] == 42
        assert result["tool_calls"][0]["args"]["float"] == 3.14
        assert result["tool_calls"][0]["args"]["boolean"] is True
        assert result["tool_calls"][0]["args"]["null"] is None
        assert result["tool_calls"][0]["args"]["list"] == [1, 2, 3]
        assert result["tool_calls"][0]["args"]["dict"]["nested"] == "value"


class TestCheckpointerIntegration:
    """Integration tests for checkpointer with agent workflow."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path for testing."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
            return tmp.name

    def test_agent_with_checkpointer(self, temp_db_path, monkeypatch):
        """Test that agent can be created with checkpointer enabled."""
        # Mock environment to enable checkpointer
        monkeypatch.setenv("IKOMA_DISABLE_CHECKPOINTER", "false")
        monkeypatch.setenv("CONVERSATION_DB_PATH", temp_db_path)

        # Import here to avoid circular imports
        from agent.agent import create_agent

        # Should not raise an exception
        agent = create_agent(disable_checkpoint=False)
        assert agent is not None

    def test_agent_without_checkpointer(self, monkeypatch):
        """Test that agent can be created with checkpointer disabled."""
        # Mock environment to disable checkpointer
        monkeypatch.setenv("IKOMA_DISABLE_CHECKPOINTER", "true")

        # Import here to avoid circular imports
        from agent.agent import create_agent

        # Should not raise an exception
        agent = create_agent(disable_checkpoint=True)
        assert agent is not None

    def test_checkpointer_persistence(self, temp_db_path, monkeypatch):
        """Test that conversation state persists across agent restarts."""
        # Mock environment
        monkeypatch.setenv("IKOMA_DISABLE_CHECKPOINTER", "false")
        monkeypatch.setenv("CONVERSATION_DB_PATH", temp_db_path)

        # Import here to avoid circular imports
        from agent.agent import create_agent

        # Create first agent and run some steps
        agent1 = create_agent(disable_checkpoint=False)

        # Simulate a conversation run
        run_id = "persistence-test"
        # Note: initial_state and config would be used in a full agent integration test
        # For this test, we focus on the checkpointer functionality directly

        # Run a few steps (this would normally invoke the agent)
        # For this test, we'll just verify the checkpointer is working
        checkpointer = agent1.checkpointer if hasattr(agent1, "checkpointer") else None

        if checkpointer:
            # Simulate storing some steps
            checkpointer.put_step(run_id, 1, {"tool_calls": [{"name": "step1"}]})
            checkpointer.put_step(run_id, 2, {"tool_calls": [{"name": "step2"}]})
            checkpointer.put_step(run_id, 3, {"tool_calls": [{"name": "step3"}]})

            # Verify steps were stored
            steps = checkpointer.list_steps(run_id)
            assert len(steps) == 3
            assert set(steps) == {1, 2, 3}

            # Create a new agent instance (simulating restart)
            agent2 = create_agent(disable_checkpoint=False)
            checkpointer2 = (
                agent2.checkpointer if hasattr(agent2, "checkpointer") else None
            )

            if checkpointer2:
                # Verify persistence
                steps2 = checkpointer2.list_steps(run_id)
                assert len(steps2) == 3
                assert set(steps2) == {1, 2, 3}

                # Verify data integrity
                step1_data = checkpointer2.get_step(run_id, 1)
                assert step1_data["tool_calls"][0]["name"] == "step1"
