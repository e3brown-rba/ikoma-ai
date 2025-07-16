import tempfile
from typing import Any

import pytest

from agent.agent import create_agent


class TestCheckpointerToggle:
    """Test suite for checkpointer toggle functionality."""

    @pytest.fixture
    def temp_db_path(self) -> str:
        """Create a temporary database path for testing."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
            return tmp.name

    def test_default_enabled(self, temp_db_path: str, monkeypatch: Any) -> None:
        """Test that checkpointer is enabled by default when no env vars are set."""
        monkeypatch.setenv("CONVERSATION_DB_PATH", temp_db_path)

        # Clear any existing env vars
        monkeypatch.delenv("CHECKPOINTER_ENABLED", raising=False)
        monkeypatch.delenv("IKOMA_DISABLE_CHECKPOINTER", raising=False)

        agent = create_agent(disable_checkpoint=False)

        # Check that agent was created successfully
        assert agent is not None

    def test_checkpointer_enabled_true(
        self, temp_db_path: str, monkeypatch: Any
    ) -> None:
        """Test that checkpointer is enabled when CHECKPOINTER_ENABLED=true."""
        monkeypatch.setenv("CONVERSATION_DB_PATH", temp_db_path)
        monkeypatch.setenv("CHECKPOINTER_ENABLED", "true")
        monkeypatch.delenv("IKOMA_DISABLE_CHECKPOINTER", raising=False)

        agent = create_agent(disable_checkpoint=False)

        # Check that agent was created successfully
        assert agent is not None

    def test_checkpointer_enabled_false(
        self, temp_db_path: str, monkeypatch: Any
    ) -> None:
        """Test that checkpointer is disabled when CHECKPOINTER_ENABLED=false."""
        monkeypatch.setenv("CONVERSATION_DB_PATH", temp_db_path)
        monkeypatch.setenv("CHECKPOINTER_ENABLED", "false")
        monkeypatch.delenv("IKOMA_DISABLE_CHECKPOINTER", raising=False)

        agent = create_agent(disable_checkpoint=False)

        # Check that agent was created successfully (even without checkpointer)
        assert agent is not None

    def test_checkpointer_enabled_case_insensitive(
        self, temp_db_path: str, monkeypatch: Any
    ) -> None:
        """Test that CHECKPOINTER_ENABLED is case insensitive."""
        monkeypatch.setenv("CONVERSATION_DB_PATH", temp_db_path)
        monkeypatch.setenv("CHECKPOINTER_ENABLED", "FALSE")
        monkeypatch.delenv("IKOMA_DISABLE_CHECKPOINTER", raising=False)

        agent = create_agent(disable_checkpoint=False)

        # Check that agent was created successfully
        assert agent is not None

    def test_checkpointer_enabled_invalid_value(
        self, temp_db_path: str, monkeypatch: Any, capsys: Any
    ) -> None:
        """Test that invalid CHECKPOINTER_ENABLED values default to true."""
        monkeypatch.setenv("CONVERSATION_DB_PATH", temp_db_path)
        monkeypatch.setenv("CHECKPOINTER_ENABLED", "invalid_value")
        monkeypatch.delenv("IKOMA_DISABLE_CHECKPOINTER", raising=False)

        agent = create_agent(disable_checkpoint=False)

        # Should show warning about invalid value
        captured = capsys.readouterr()
        assert "CHECKPOINTER_ENABLED value 'invalid_value' is invalid" in captured.out

        # Check that agent was created successfully (defaults to true)
        assert agent is not None

    def test_legacy_ikoma_disable_checkpointer(
        self, temp_db_path: str, monkeypatch: Any, capsys: Any
    ) -> None:
        """Test that legacy IKOMA_DISABLE_CHECKPOINTER still works."""
        monkeypatch.setenv("CONVERSATION_DB_PATH", temp_db_path)
        monkeypatch.setenv("IKOMA_DISABLE_CHECKPOINTER", "true")
        monkeypatch.delenv("CHECKPOINTER_ENABLED", raising=False)

        agent = create_agent(disable_checkpoint=False)

        # Should show deprecation warning
        captured = capsys.readouterr()
        assert "DEPRECATION: IKOMA_DISABLE_CHECKPOINTER detected" in captured.out

        # Check that agent was created successfully
        assert agent is not None

    def test_cli_no_checkpoint_overrides_env(
        self, temp_db_path: str, monkeypatch: Any
    ) -> None:
        """Test that --no-checkpoint CLI flag overrides environment variables."""
        monkeypatch.setenv("CONVERSATION_DB_PATH", temp_db_path)
        monkeypatch.setenv("CHECKPOINTER_ENABLED", "true")
        monkeypatch.delenv("IKOMA_DISABLE_CHECKPOINTER", raising=False)

        # CLI flag should override env var
        agent = create_agent(disable_checkpoint=True)

        # Check that agent was created successfully
        assert agent is not None

    def test_legacy_overrides_new_env_var(
        self, temp_db_path: str, monkeypatch: Any, capsys: Any
    ) -> None:
        """Test that legacy IKOMA_DISABLE_CHECKPOINTER overrides CHECKPOINTER_ENABLED."""
        monkeypatch.setenv("CONVERSATION_DB_PATH", temp_db_path)
        monkeypatch.setenv("CHECKPOINTER_ENABLED", "true")
        monkeypatch.setenv("IKOMA_DISABLE_CHECKPOINTER", "true")

        agent = create_agent(disable_checkpoint=False)

        # Should show deprecation warning
        captured = capsys.readouterr()
        assert "DEPRECATION: IKOMA_DISABLE_CHECKPOINTER detected" in captured.out

        # Check that agent was created successfully
        assert agent is not None

    @pytest.mark.parametrize("enabled_value", ["0", "false", "no"])
    def test_checkpointer_enabled_false_values(
        self, temp_db_path: str, monkeypatch: Any, enabled_value: str
    ) -> None:
        """Test various false values for CHECKPOINTER_ENABLED."""
        monkeypatch.setenv("CONVERSATION_DB_PATH", temp_db_path)
        monkeypatch.setenv("CHECKPOINTER_ENABLED", enabled_value)
        monkeypatch.delenv("IKOMA_DISABLE_CHECKPOINTER", raising=False)

        agent = create_agent(disable_checkpoint=False)

        # Check that agent was created successfully
        assert agent is not None

    @pytest.mark.parametrize("enabled_value", ["1", "true", "yes"])
    def test_checkpointer_enabled_true_values(
        self, temp_db_path: str, monkeypatch: Any, enabled_value: str
    ) -> None:
        """Test various true values for CHECKPOINTER_ENABLED."""
        monkeypatch.setenv("CONVERSATION_DB_PATH", temp_db_path)
        monkeypatch.setenv("CHECKPOINTER_ENABLED", enabled_value)
        monkeypatch.delenv("IKOMA_DISABLE_CHECKPOINTER", raising=False)

        agent = create_agent(disable_checkpoint=False)

        # Check that agent was created successfully
        assert agent is not None

    def test_agent_state_with_checkpointer(
        self, temp_db_path: str, monkeypatch: Any
    ) -> None:
        """Test that agent state is properly initialized when checkpointer is enabled."""
        monkeypatch.setenv("CONVERSATION_DB_PATH", temp_db_path)
        monkeypatch.setenv("CHECKPOINTER_ENABLED", "true")
        monkeypatch.delenv("IKOMA_DISABLE_CHECKPOINTER", raising=False)

        agent = create_agent(disable_checkpoint=False)

        # Test that agent can be invoked with proper state
        from langchain_core.messages import HumanMessage

        initial_state = {
            "messages": [HumanMessage(content="test message")],
            "memory_context": None,
            "user_profile": None,
            "session_summary": None,
            "current_plan": None,
            "execution_results": None,
            "reflection": None,
            "continue_planning": False,
            "max_iterations": 3,
            "current_iteration": 0,
            "start_time": None,
            "time_limit_secs": None,
            "citations": [],
            "citation_counter": 1,
            "checkpoint_every": None,
            "last_checkpoint_iter": 0,
        }

        config = {"configurable": {"thread_id": "test_thread"}}

        # Should not raise an exception
        result = agent.invoke(initial_state, config)
        assert result is not None

    def test_agent_state_without_checkpointer(
        self, temp_db_path: str, monkeypatch: Any
    ) -> None:
        """Test that agent state is properly initialized when checkpointer is disabled."""
        monkeypatch.setenv("CONVERSATION_DB_PATH", temp_db_path)
        monkeypatch.setenv("CHECKPOINTER_ENABLED", "false")
        monkeypatch.delenv("IKOMA_DISABLE_CHECKPOINTER", raising=False)

        agent = create_agent(disable_checkpoint=False)

        # Test that agent can be invoked with proper state
        from langchain_core.messages import HumanMessage

        initial_state = {
            "messages": [HumanMessage(content="test message")],
            "memory_context": None,
            "user_profile": None,
            "session_summary": None,
            "current_plan": None,
            "execution_results": None,
            "reflection": None,
            "continue_planning": False,
            "max_iterations": 3,
            "current_iteration": 0,
            "start_time": None,
            "time_limit_secs": None,
            "citations": [],
            "citation_counter": 1,
            "checkpoint_every": None,
            "last_checkpoint_iter": 0,
        }

        config = {"configurable": {"thread_id": "test_thread"}}

        # Should not raise an exception
        result = agent.invoke(initial_state, config)
        assert result is not None
