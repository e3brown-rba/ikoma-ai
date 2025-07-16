import tempfile
from typing import Any

import pytest

from agent.checkpointer import get_checkpointer_service
from agent.memory_manager import IkomaMemoryManager


class TestMemoryManagerIntegration:
    """Test the MemoryManager integration with LangGraph."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path for testing."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
            return tmp.name

    @pytest.fixture
    def memory_manager(self, temp_db_path):
        """Create a memory manager instance with temporary database."""
        return IkomaMemoryManager(temp_db_path)

    def test_memory_manager_initialization(self, temp_db_path):
        """Test that MemoryManager initializes correctly."""
        manager = IkomaMemoryManager(temp_db_path)
        assert manager is not None

        # Verify the service is accessible
        service = get_checkpointer_service(temp_db_path)
        assert service is not None

    def test_put_and_get_tuple(self, memory_manager):
        """Test basic put and get_tuple operations."""
        from langchain_core.runnables import RunnableConfig

        # Create test data
        config: RunnableConfig = {
            "configurable": {
                "thread_id": "test-thread-123",
                "checkpoint_id": "1",
                "checkpoint_ns": "",
            }
        }

        checkpoint = {
            "id": "1",
            "v": 1,
            "ts": "2024-01-01T00:00:00Z",
            "channel_values": {
                "tool_calls": {
                    "tool_calls": [{"name": "test_tool", "args": {"param": "value"}}]
                }
            },
            "channel_versions": {},
            "versions_seen": {},
        }

        metadata = {"step": 1}
        new_versions: dict[str, Any] = {}

        # Put the checkpoint
        memory_manager.put(config, checkpoint, metadata, new_versions)

        # Get the checkpoint back
        result = memory_manager.get_tuple(config)

        assert result is not None
        retrieved_checkpoint, retrieved_metadata = result

        # Verify the data matches
        assert retrieved_checkpoint["id"] == "1"
        assert (
            retrieved_checkpoint["channel_values"]["tool_calls"]["tool_calls"][0][
                "name"
            ]
            == "test_tool"
        )
        assert retrieved_metadata["step"] == 1

    def test_list_checkpoints(self, memory_manager):
        """Test listing all checkpoints for a thread."""
        from langchain_core.runnables import RunnableConfig

        # Create multiple checkpoints
        for i in range(1, 4):
            config: RunnableConfig = {
                "configurable": {
                    "thread_id": "test-thread-list",
                    "checkpoint_id": str(i),
                    "checkpoint_ns": "",
                }
            }

            checkpoint = {
                "id": str(i),
                "v": 1,
                "ts": "2024-01-01T00:00:00Z",
                "channel_values": {
                    "tool_calls": {
                        "tool_calls": [{"name": f"tool_{i}", "args": {"step": i}}]
                    }
                },
                "channel_versions": {},
                "versions_seen": {},
            }

            metadata = {"step": i}
            new_versions = {}

            memory_manager.put(config, checkpoint, metadata, new_versions)

        # List all checkpoints
        list_config: RunnableConfig = {
            "configurable": {
                "thread_id": "test-thread-list",
                "checkpoint_ns": "",
            }
        }

        results = memory_manager.list(list_config)

        assert len(results) == 3

        # Verify all checkpoints are present
        checkpoint_ids = [result[1]["id"] for result in results]
        assert set(checkpoint_ids) == {"1", "2", "3"}

    def test_delete_thread(self, memory_manager):
        """Test deleting all checkpoints for a thread."""
        from langchain_core.runnables import RunnableConfig

        # Create checkpoints for multiple threads
        for thread_id in ["thread-1", "thread-2"]:
            for step in range(1, 3):
                config: RunnableConfig = {
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_id": str(step),
                        "checkpoint_ns": "",
                    }
                }

                checkpoint = {
                    "id": str(step),
                    "v": 1,
                    "ts": "2024-01-01T00:00:00Z",
                    "channel_values": {
                        "tool_calls": {
                            "tool_calls": [
                                {"name": f"tool_{step}", "args": {"thread": thread_id}}
                            ]
                        }
                    },
                    "channel_versions": {},
                    "versions_seen": {},
                }

                metadata = {"step": step}
                new_versions = {}

                memory_manager.put(config, checkpoint, metadata, new_versions)

        # Verify both threads have checkpoints
        list_config_1: RunnableConfig = {
            "configurable": {"thread_id": "thread-1", "checkpoint_ns": ""}
        }
        list_config_2: RunnableConfig = {
            "configurable": {"thread_id": "thread-2", "checkpoint_ns": ""}
        }

        assert len(memory_manager.list(list_config_1)) == 2
        assert len(memory_manager.list(list_config_2)) == 2

        # Delete thread-1
        memory_manager.delete_thread("thread-1")

        # Verify thread-1 is gone but thread-2 remains
        assert len(memory_manager.list(list_config_1)) == 0
        assert len(memory_manager.list(list_config_2)) == 2

    def test_remove_method(self, memory_manager):
        """Test the remove method (alias for delete_thread)."""
        from langchain_core.runnables import RunnableConfig

        # Create a checkpoint
        config: RunnableConfig = {
            "configurable": {
                "thread_id": "test-thread-remove",
                "checkpoint_id": "1",
                "checkpoint_ns": "",
            }
        }

        checkpoint = {
            "id": "1",
            "v": 1,
            "ts": "2024-01-01T00:00:00Z",
            "channel_values": {
                "tool_calls": {
                    "tool_calls": [{"name": "test_tool", "args": {"test": "data"}}]
                }
            },
            "channel_versions": {},
            "versions_seen": {},
        }

        metadata = {"step": 1}
        new_versions = {}

        memory_manager.put(config, checkpoint, metadata, new_versions)

        # Verify checkpoint exists
        list_config: RunnableConfig = {
            "configurable": {"thread_id": "test-thread-remove", "checkpoint_ns": ""}
        }
        assert len(memory_manager.list(list_config)) == 1

        # Remove using remove method
        memory_manager.remove("test-thread-remove")

        # Verify checkpoint is gone
        assert len(memory_manager.list(list_config)) == 0

    def test_get_nonexistent_checkpoint(self, memory_manager):
        """Test getting a non-existent checkpoint returns None."""
        from langchain_core.runnables import RunnableConfig

        config: RunnableConfig = {
            "configurable": {
                "thread_id": "nonexistent",
                "checkpoint_id": "999",
                "checkpoint_ns": "",
            }
        }

        result = memory_manager.get_tuple(config)
        assert result is None

    def test_list_empty_thread(self, memory_manager):
        """Test listing checkpoints for a non-existent thread returns empty list."""
        from langchain_core.runnables import RunnableConfig

        config: RunnableConfig = {
            "configurable": {
                "thread_id": "empty-thread",
                "checkpoint_ns": "",
            }
        }

        results = memory_manager.list(config)
        assert results == []

    def test_missing_config_values(self, memory_manager):
        """Test handling of missing config values."""
        from langchain_core.runnables import RunnableConfig

        # Test with missing thread_id
        config: RunnableConfig = {
            "configurable": {
                "checkpoint_id": "1",
                "checkpoint_ns": "",
            }
        }

        checkpoint = {
            "id": "1",
            "v": 1,
            "ts": "2024-01-01T00:00:00Z",
            "channel_values": {"tool_calls": {"test": "data"}},
            "channel_versions": {},
            "versions_seen": {},
        }

        metadata = {"step": 1}
        new_versions = {}

        # Should raise ValueError for missing thread_id
        with pytest.raises(ValueError) as exc_info:
            memory_manager.put(config, checkpoint, metadata, new_versions)

        assert "Missing thread_id" in str(exc_info.value)

    def test_complex_state_round_trip(self, memory_manager):
        """Test round-trip of complex state structures."""
        from langchain_core.runnables import RunnableConfig

        # Create complex state
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

        config: RunnableConfig = {
            "configurable": {
                "thread_id": "test-complex",
                "checkpoint_id": "1",
                "checkpoint_ns": "",
            }
        }

        checkpoint = {
            "id": "1",
            "v": 1,
            "ts": "2024-01-01T00:00:00Z",
            "channel_values": {"tool_calls": complex_state},
            "channel_versions": {},
            "versions_seen": {},
        }

        metadata = {"step": 1}
        new_versions = {}

        # Put the checkpoint
        memory_manager.put(config, checkpoint, metadata, new_versions)

        # Get it back
        result = memory_manager.get_tuple(config)

        assert result is not None
        retrieved_checkpoint, _ = result

        # Verify complex structure is preserved
        retrieved_state = retrieved_checkpoint["channel_values"]["tool_calls"]

        assert retrieved_state["messages"][0]["content"] == "Hello"
        assert retrieved_state["messages"][1]["content"] == "Hi there!"
        assert retrieved_state["tool_calls"][0]["name"] == "web_search"
        assert (
            retrieved_state["metadata"]["nested"]["level1"]["level2"]["level3"]
            == "deep_value"
        )

    def test_error_handling_in_get_tuple(self, memory_manager):
        """Test that get_tuple handles errors gracefully."""
        from langchain_core.runnables import RunnableConfig

        # Create a valid checkpoint first
        config: RunnableConfig = {
            "configurable": {
                "thread_id": "test-error-handling",
                "checkpoint_id": "1",
                "checkpoint_ns": "",
            }
        }

        checkpoint = {
            "id": "1",
            "v": 1,
            "ts": "2024-01-01T00:00:00Z",
            "channel_values": {"tool_calls": {"test": "data"}},
            "channel_versions": {},
            "versions_seen": {},
        }

        metadata = {"step": 1}
        new_versions = {}

        memory_manager.put(config, checkpoint, metadata, new_versions)

        # Test with invalid checkpoint_id (non-numeric)
        invalid_config: RunnableConfig = {
            "configurable": {
                "thread_id": "test-error-handling",
                "checkpoint_id": "invalid",
                "checkpoint_ns": "",
            }
        }

        # Should return None for invalid checkpoint_id
        result = memory_manager.get_tuple(invalid_config)
        assert result is None

    def test_error_handling_in_list(self, memory_manager):
        """Test that list handles errors gracefully."""
        from langchain_core.runnables import RunnableConfig

        # Test with missing thread_id
        config: RunnableConfig = {
            "configurable": {
                "checkpoint_ns": "",
            }
        }

        # Should return empty list for missing thread_id
        results = memory_manager.list(config)
        assert results == []

    def test_singleton_service_sharing(self, temp_db_path):
        """Test that MemoryManager shares the same service instance."""
        manager1 = IkomaMemoryManager(temp_db_path)
        manager2 = IkomaMemoryManager(temp_db_path)

        # They should use the same underlying service
        service1 = manager1._service
        service2 = manager2._service

        # Should be the same instance due to singleton pattern
        assert service1 is service2

        # Test that they share data
        from langchain_core.runnables import RunnableConfig

        config: RunnableConfig = {
            "configurable": {
                "thread_id": "test-sharing",
                "checkpoint_id": "1",
                "checkpoint_ns": "",
            }
        }

        checkpoint = {
            "id": "1",
            "v": 1,
            "ts": "2024-01-01T00:00:00Z",
            "channel_values": {"tool_calls": {"test": "shared"}},
            "channel_versions": {},
            "versions_seen": {},
        }

        metadata = {"step": 1}
        new_versions = {}

        # Save with first manager
        manager1.put(config, checkpoint, metadata, new_versions)

        # Retrieve with second manager
        result = manager2.get_tuple(config)

        assert result is not None
        retrieved_checkpoint, _ = result
        assert retrieved_checkpoint["channel_values"]["tool_calls"]["test"] == "shared"
