import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from agent.checkpointer import (
    CheckpointerService,
    CheckpointNotFound,
    CheckpointRecord,
    DuplicateStepError,
    get_checkpointer_service,
)


class TestCheckpointRecord:
    """Test the CheckpointRecord Pydantic model."""

    def test_checkpoint_record_creation(self):
        """Test creating a CheckpointRecord with all fields."""
        record = CheckpointRecord(
            run_id="test-run-123",
            step=1,
            state={"tool_calls": [{"name": "test", "args": {"key": "value"}}]},
        )

        assert record.run_id == "test-run-123"
        assert record.step == 1
        assert record.state["tool_calls"][0]["name"] == "test"
        assert isinstance(record.created_at, datetime)

    def test_checkpoint_record_defaults(self):
        """Test CheckpointRecord with default created_at."""
        record = CheckpointRecord(
            run_id="test-run-456",
            step=2,
            state={"test": "data"},
        )

        assert record.run_id == "test-run-456"
        assert record.step == 2
        assert record.state == {"test": "data"}
        assert isinstance(record.created_at, datetime)

    def test_checkpoint_record_custom_timestamp(self):
        """Test CheckpointRecord with custom created_at."""
        custom_time = datetime(2024, 1, 1, 12, 0, 0)
        record = CheckpointRecord(
            run_id="test-run-789",
            step=3,
            state={"custom": "timestamp"},
            created_at=custom_time,
        )

        assert record.created_at == custom_time


class TestCheckpointerService:
    """Test the CheckpointerService CRUD operations."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path for testing."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
            return tmp.name

    @pytest.fixture
    def service(self, temp_db_path):
        """Create a service instance with temporary database."""
        return CheckpointerService(temp_db_path)

    def test_save_and_get_step(self, service):
        """Test basic save and get operations."""
        record = CheckpointRecord(
            run_id="test-run-123",
            step=1,
            state={"tool_calls": [{"name": "test_tool", "args": {"param": "value"}}]},
        )

        # Save the record
        service.save_step(record)

        # Retrieve all steps for the run
        records = service.get_steps("test-run-123")

        assert len(records) == 1
        retrieved = records[0]
        assert retrieved.run_id == "test-run-123"
        assert retrieved.step == 1
        assert retrieved.state["tool_calls"][0]["name"] == "test_tool"
        assert retrieved.state["tool_calls"][0]["args"]["param"] == "value"

    def test_save_multiple_steps(self, service):
        """Test saving multiple steps for the same run."""
        records = [
            CheckpointRecord(
                run_id="test-run-multi",
                step=i,
                state={"tool_calls": [{"name": f"tool_{i}", "args": {"step": i}}]},
            )
            for i in range(1, 4)
        ]

        # Save all records
        for record in records:
            service.save_step(record)

        # Retrieve all steps
        retrieved = service.get_steps("test-run-multi")

        assert len(retrieved) == 3
        # Should be sorted by step
        assert [r.step for r in retrieved] == [1, 2, 3]
        assert retrieved[0].state["tool_calls"][0]["name"] == "tool_1"
        assert retrieved[2].state["tool_calls"][0]["name"] == "tool_3"

    def test_duplicate_step_error(self, service):
        """Test that saving duplicate steps raises DuplicateStepError."""
        record = CheckpointRecord(
            run_id="test-run-duplicate",
            step=1,
            state={"test": "data"},
        )

        # Save first time
        service.save_step(record)

        # Try to save again with same run_id and step
        with pytest.raises(DuplicateStepError) as exc_info:
            service.save_step(record)

        assert "Step 1 already exists for run test-run-duplicate" in str(exc_info.value)

    def test_update_step(self, service):
        """Test updating an existing step."""
        # Create initial record
        record = CheckpointRecord(
            run_id="test-run-update",
            step=1,
            state={"original": "data"},
        )
        service.save_step(record)

        # Update the step
        new_state = {"updated": "data", "new_key": "new_value"}
        service.update_step("test-run-update", 1, new_state)

        # Verify update
        records = service.get_steps("test-run-update")
        assert len(records) == 1
        assert records[0].state == new_state

    def test_update_nonexistent_step(self, service):
        """Test updating a non-existent step raises CheckpointNotFound."""
        with pytest.raises(CheckpointNotFound) as exc_info:
            service.update_step("nonexistent", 999, {"test": "data"})

        assert "No checkpoint found for run nonexistent, step 999" in str(
            exc_info.value
        )

    def test_delete_step(self, service):
        """Test deleting a specific step."""
        # Create multiple steps
        for i in range(1, 4):
            record = CheckpointRecord(
                run_id="test-run-delete",
                step=i,
                state={"step": i},
            )
            service.save_step(record)

        # Verify all steps exist
        records = service.get_steps("test-run-delete")
        assert len(records) == 3

        # Delete step 2
        service.delete_step("test-run-delete", 2)

        # Verify step 2 is gone
        records = service.get_steps("test-run-delete")
        assert len(records) == 2
        assert [r.step for r in records] == [1, 3]

    def test_delete_nonexistent_step(self, service):
        """Test deleting a non-existent step raises CheckpointNotFound."""
        with pytest.raises(CheckpointNotFound) as exc_info:
            service.delete_step("nonexistent", 999)

        assert "No checkpoint found for run nonexistent, step 999" in str(
            exc_info.value
        )

    def test_delete_run(self, service):
        """Test deleting all steps for a run."""
        # Create steps for multiple runs
        for run_id in ["run-1", "run-2"]:
            for step in range(1, 4):
                record = CheckpointRecord(
                    run_id=run_id,
                    step=step,
                    state={"run": run_id, "step": step},
                )
                service.save_step(record)

        # Verify both runs have steps
        assert len(service.get_steps("run-1")) == 3
        assert len(service.get_steps("run-2")) == 3

        # Delete run-1
        service.delete_run("run-1")

        # Verify run-1 is gone but run-2 remains
        assert len(service.get_steps("run-1")) == 0
        assert len(service.get_steps("run-2")) == 3

    def test_get_steps_empty_run(self, service):
        """Test getting steps for a run that doesn't exist."""
        records = service.get_steps("nonexistent")
        assert records == []

    def test_large_state_payload(self, service):
        """Test handling of large state payloads."""
        large_content = "x" * 10000  # 10KB of data
        record = CheckpointRecord(
            run_id="test-run-large",
            step=1,
            state={
                "tool_calls": [
                    {
                        "name": "large_operation",
                        "args": {"content": large_content},
                        "metadata": {"size": len(large_content)},
                    }
                ]
            },
        )

        # Save and retrieve
        service.save_step(record)
        records = service.get_steps("test-run-large")

        assert len(records) == 1
        retrieved = records[0]
        assert retrieved.state["tool_calls"][0]["name"] == "large_operation"
        assert retrieved.state["tool_calls"][0]["args"]["content"] == large_content
        assert retrieved.state["tool_calls"][0]["metadata"]["size"] == 10000


class TestCheckpointerServiceSingleton:
    """Test the singleton pattern for CheckpointerService."""

    def test_singleton_behavior(self):
        """Test that get_checkpointer_service returns the same instance for the same path."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
            db_path = tmp.name

        try:
            # Get service instances
            service1 = get_checkpointer_service(db_path)
            service2 = get_checkpointer_service(db_path)

            # Should be the same instance
            assert service1 is service2

            # Test that they share the same database
            record = CheckpointRecord(
                run_id="test-singleton",
                step=1,
                state={"test": "data"},
            )

            service1.save_step(record)
            records = service2.get_steps("test-singleton")

            assert len(records) == 1
            assert records[0].run_id == "test-singleton"

        finally:
            # Cleanup
            Path(db_path).unlink(missing_ok=True)

    def test_different_paths_different_instances(self):
        """Test that different paths return different instances."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp1:
            db_path1 = tmp1.name

        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp2:
            db_path2 = tmp2.name

        try:
            service1 = get_checkpointer_service(db_path1)
            service2 = get_checkpointer_service(db_path2)

            # Should be different instances
            assert service1 is not service2

            # Test isolation
            record1 = CheckpointRecord(
                run_id="test-isolation",
                step=1,
                state={"service": "1"},
            )
            record2 = CheckpointRecord(
                run_id="test-isolation",
                step=1,
                state={"service": "2"},
            )

            service1.save_step(record1)
            service2.save_step(record2)

            # Should have different data
            records1 = service1.get_steps("test-isolation")
            records2 = service2.get_steps("test-isolation")

            assert len(records1) == 1
            assert len(records2) == 1
            assert records1[0].state["service"] == "1"
            assert records2[0].state["service"] == "2"

        finally:
            # Cleanup
            Path(db_path1).unlink(missing_ok=True)
            Path(db_path2).unlink(missing_ok=True)


class TestCheckpointerServiceEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path for testing."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
            return tmp.name

    @pytest.fixture
    def service(self, temp_db_path):
        """Create a service instance with temporary database."""
        return CheckpointerService(temp_db_path)

    def test_complex_nested_state(self, service):
        """Test saving and retrieving complex nested state structures."""
        complex_state = {
            "messages": [
                {"type": "human", "content": "Hello"},
                {"type": "ai", "content": "Hi there!"},
            ],
            "tool_calls": [
                {
                    "name": "web_search",
                    "args": {"query": "test query"},
                    "metadata": {"source": "serpapi"},
                }
            ],
            "metadata": {
                "timestamp": "2024-01-01T00:00:00Z",
                "session_id": "session-123",
                "nested": {"level1": {"level2": {"level3": "deep_value"}}},
            },
        }

        record = CheckpointRecord(
            run_id="test-complex",
            step=1,
            state=complex_state,
        )

        service.save_step(record)
        records = service.get_steps("test-complex")

        assert len(records) == 1
        retrieved_state = records[0].state

        # Verify complex structure is preserved
        assert retrieved_state["messages"][0]["content"] == "Hello"
        assert retrieved_state["messages"][1]["content"] == "Hi there!"
        assert retrieved_state["tool_calls"][0]["name"] == "web_search"
        assert (
            retrieved_state["metadata"]["nested"]["level1"]["level2"]["level3"]
            == "deep_value"
        )

    def test_special_characters_in_run_id(self, service):
        """Test handling of special characters in run IDs."""
        special_run_id = "test-run-with-special-chars-!@#$%^&*()_+-=[]{}|;':\",./<>?"

        record = CheckpointRecord(
            run_id=special_run_id,
            step=1,
            state={"test": "data"},
        )

        service.save_step(record)
        records = service.get_steps(special_run_id)

        assert len(records) == 1
        assert records[0].run_id == special_run_id

    def test_zero_step_number(self, service):
        """Test handling of step number 0."""
        record = CheckpointRecord(
            run_id="test-zero-step",
            step=0,
            state={"step": 0},
        )

        service.save_step(record)
        records = service.get_steps("test-zero-step")

        assert len(records) == 1
        assert records[0].step == 0

    def test_negative_step_number(self, service):
        """Test handling of negative step numbers."""
        record = CheckpointRecord(
            run_id="test-negative-step",
            step=-1,
            state={"step": -1},
        )

        service.save_step(record)
        records = service.get_steps("test-negative-step")

        assert len(records) == 1
        assert records[0].step == -1

    def test_empty_state(self, service):
        """Test handling of empty state dictionary."""
        record = CheckpointRecord(
            run_id="test-empty-state",
            step=1,
            state={},
        )

        service.save_step(record)
        records = service.get_steps("test-empty-state")

        assert len(records) == 1
        assert records[0].state == {}

    def test_none_values_in_state(self, service):
        """Test handling of None values in state."""
        record = CheckpointRecord(
            run_id="test-none-values",
            step=1,
            state={
                "null_value": None,
                "tool_calls": None,
                "metadata": {"nested_null": None},
            },
        )

        service.save_step(record)
        records = service.get_steps("test-none-values")

        assert len(records) == 1
        retrieved_state = records[0].state
        assert retrieved_state["null_value"] is None
        assert retrieved_state["tool_calls"] is None
        assert retrieved_state["metadata"]["nested_null"] is None
