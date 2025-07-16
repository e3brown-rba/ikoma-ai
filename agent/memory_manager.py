from collections.abc import Iterator
from typing import Any, cast

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)
from langgraph.checkpoint.memory import MemorySaver

from .checkpointer import CheckpointerService, CheckpointRecord


class IkomaMemoryManager(BaseCheckpointSaver[Any]):
    """LangGraph memory manager that delegates to our checkpointer service."""

    def __init__(self, service: CheckpointerService) -> None:
        self.service = service
        # Fallback to memory saver for operations not supported by our service
        self._memory_saver = MemorySaver()

    def get(self, config: RunnableConfig) -> Checkpoint | None:
        """Get checkpoint by config."""
        if not config or "configurable" not in config:
            return None

        configurable = config["configurable"]
        if not isinstance(configurable, dict) or "thread_id" not in configurable:
            return None

        thread_id = configurable["thread_id"]
        records = self.service.get_steps(thread_id)
        if records:
            # Return the latest step's state as a Checkpoint
            latest_record = records[-1]
            # Convert our state dict to LangGraph Checkpoint format
            checkpoint: Checkpoint = {
                "id": str(latest_record.step),
                "v": 1,
                "ts": latest_record.created_at.isoformat(),
                "channel_values": latest_record.state,
                "channel_versions": {},
                "versions_seen": {},
            }
            return checkpoint
        return None

    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        """Get checkpoint tuple by config."""
        if not config or "configurable" not in config:
            return None

        configurable = config["configurable"]
        if not isinstance(configurable, dict) or "thread_id" not in configurable:
            return None

        thread_id = configurable["thread_id"]
        records = self.service.get_steps(thread_id)
        if records:
            # Return the latest step
            latest_record = records[-1]
            metadata: CheckpointMetadata = {"step": latest_record.step}
            # Convert our state dict to LangGraph Checkpoint format
            checkpoint: Checkpoint = {
                "id": str(latest_record.step),
                "v": 1,
                "ts": latest_record.created_at.isoformat(),
                "channel_values": latest_record.state,
                "channel_versions": {},
                "versions_seen": {},
            }
            return cast(CheckpointTuple, (config, checkpoint, metadata))
        return None

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: dict[str, str | int | float],
    ) -> RunnableConfig:
        """Store checkpoint with metadata."""
        if not config or "configurable" not in config:
            return config

        configurable = config["configurable"]
        if not isinstance(configurable, dict) or "thread_id" not in configurable:
            return config

        thread_id = configurable["thread_id"]
        step = metadata.get("step", 0)

        # Extract state from LangGraph Checkpoint format
        state = checkpoint.get("channel_values", {})

        record = CheckpointRecord(run_id=thread_id, step=step, state=state)

        self.service.save_step(record)
        return config

    def list(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> Iterator[CheckpointTuple]:
        """List checkpoints for a config."""
        if not config or "configurable" not in config:
            return

        configurable = config["configurable"]
        if not isinstance(configurable, dict) or "thread_id" not in configurable:
            return

        thread_id = configurable["thread_id"]
        records = self.service.get_steps(thread_id)

        for record in records:
            metadata: CheckpointMetadata = {"step": record.step}
            # Convert our state dict to LangGraph Checkpoint format
            checkpoint: Checkpoint = {
                "id": str(record.step),
                "v": 1,
                "ts": record.created_at.isoformat(),
                "channel_values": record.state,
                "channel_versions": {},
                "versions_seen": {},
            }
            yield cast(CheckpointTuple, (config, checkpoint, metadata))

    def delete(self, config: RunnableConfig) -> None:
        """Delete checkpoint by config."""
        if not config or "configurable" not in config:
            return

        configurable = config["configurable"]
        if not isinstance(configurable, dict) or "thread_id" not in configurable:
            return

        thread_id = configurable["thread_id"]
        self.service.delete_run(thread_id)
