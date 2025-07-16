import collections
import datetime
import sqlite3
from pathlib import Path
from typing import Any, cast

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import Checkpoint, CheckpointMetadata
from langgraph.checkpoint.sqlite import SqliteSaver


class IkomaCheckpointer(SqliteSaver):
    """
    SQLite saver using the fixed Ikoma schema for conversation state persistence.
    Inherits from langgraph.checkpoint.sqlite.SqliteSaver for (run_id, step, tool_calls) CRUD.
    Adds convenience methods for (run_id, step) access.
    """

    def __init__(self, db_path: str | Path):
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        super().__init__(self._conn)
        # Enable WAL mode for safe concurrent reads
        self._conn.execute("PRAGMA journal_mode=WAL;")
        # Set user version for schema migration tracking
        self._conn.execute("PRAGMA user_version=1;")

    def put_step(self, run_id: str, step: int, tool_calls: dict[str, Any]) -> None:
        """
        Store a conversation step with tool calls.
        This stores a checkpoint with a composite key (run_id, step).
        """
        checkpoint_id = f"{step}"
        config = cast(
            RunnableConfig,
            {
                "configurable": {
                    "thread_id": run_id,
                    "checkpoint_id": checkpoint_id,
                    "checkpoint_ns": "",
                }
            },
        )
        now = datetime.datetime.now(datetime.UTC).isoformat()
        checkpoint: Checkpoint = {
            "id": checkpoint_id,
            "v": 1,
            "ts": now,
            "channel_values": {"tool_calls": tool_calls},
            "channel_versions": collections.defaultdict(int),
            "versions_seen": collections.defaultdict(
                lambda: collections.defaultdict(int)
            ),
        }
        metadata: CheckpointMetadata = {"step": step}
        new_versions: dict[str, Any] = {}
        self.put(config, checkpoint, metadata, new_versions)

    def get_step(self, run_id: str, step: int) -> dict[str, Any] | None:
        """
        Retrieve a conversation step by run_id and step.
        Returns tool_calls dict or None if not found.
        """
        checkpoint_id = f"{step}"
        config = cast(
            RunnableConfig,
            {
                "configurable": {
                    "thread_id": run_id,
                    "checkpoint_id": checkpoint_id,
                    "checkpoint_ns": "",
                }
            },
        )
        tup = self.get_tuple(config)
        if tup is not None:
            checkpoint = tup.checkpoint
            channel_values = checkpoint.get("channel_values", {})
            tool_calls = channel_values.get("tool_calls")
            if isinstance(tool_calls, dict):
                return tool_calls
        return None

    def list_steps(self, run_id: str) -> list[int]:
        """
        List all steps for a given run_id.
        Returns a list of step numbers (as int).
        """
        config = cast(
            RunnableConfig, {"configurable": {"thread_id": run_id, "checkpoint_ns": ""}}
        )
        steps = []
        for tup in self.list(config):
            configurable = tup.config.get("configurable", {})
            cid = configurable.get("checkpoint_id")
            if cid is not None and cid.isdigit():
                steps.append(int(cid))
        return sorted(steps)

    def delete_step(self, run_id: str, step: int) -> None:
        """
        Delete a specific conversation step.
        """
        checkpoint_id = f"{step}"
        self._conn.execute(
            "DELETE FROM checkpoints WHERE thread_id = ? AND checkpoint_id = ? AND checkpoint_ns = ?",
            (run_id, checkpoint_id, ""),
        )
        self._conn.commit()

    def clear_run(self, run_id: str) -> None:
        """
        Clear all steps for a given run_id.
        """
        self.delete_thread(run_id)
