import collections
import json
import sqlite3
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, cast

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import Checkpoint, CheckpointMetadata
from langgraph.checkpoint.sqlite import SqliteSaver
from pydantic import BaseModel, Field


class CheckpointRecord(BaseModel):
    """Pydantic model for checkpoint records with full type safety."""

    run_id: str = Field(..., description="Unique identifier for the conversation run")
    step: int = Field(..., description="Sequential step number within the conversation")
    state: dict[str, Any] = Field(..., description="Serialized agent state")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when checkpoint was created",
    )


class CheckpointNotFound(Exception):
    """Raised when a checkpoint record is not found."""

    pass


class DuplicateStepError(Exception):
    """Raised when attempting to save a duplicate step for the same run_id."""

    pass


class SQLiteCRUDMixin:
    """Mixin providing SQLite CRUD operations with proper parameterization."""

    def __init__(self, db_path: str | Path):
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        # Ensure the table exists
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_steps (
                run_id TEXT NOT NULL,
                step INTEGER NOT NULL,
                tool_calls TEXT NOT NULL,
                ts TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (run_id, step)
            )
            """
        )
        # Enable WAL mode for safe concurrent reads
        self._conn.execute("PRAGMA journal_mode=WAL;")
        # Set user version for schema migration tracking
        self._conn.execute("PRAGMA user_version=1;")
        # Create indices for performance
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_conversation_steps_run_step "
            "ON conversation_steps (run_id, step)"
        )

    def _insert_checkpoint(self, record: CheckpointRecord) -> None:
        """Insert a checkpoint record with proper parameterization."""
        cursor = self._conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO conversation_steps (run_id, step, tool_calls, ts) VALUES (?, ?, ?, ?)",
                (
                    record.run_id,
                    record.step,
                    json.dumps(record.state),
                    record.created_at.isoformat(),
                ),
            )
            self._conn.commit()
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                raise DuplicateStepError(
                    f"Step {record.step} already exists for run {record.run_id}"
                ) from e
            raise

    def _select_checkpoints(self, run_id: str) -> list[CheckpointRecord]:
        """Select all checkpoint records for a run_id."""
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT run_id, step, tool_calls, ts FROM conversation_steps WHERE run_id = ? ORDER BY step",
            (run_id,),
        )
        records = []
        for row in cursor.fetchall():
            run_id, step, tool_calls, ts = row
            # Parse the timestamp
            created_at = datetime.fromisoformat(ts) if ts else datetime.utcnow()
            state = json.loads(tool_calls) if tool_calls else {}
            records.append(
                CheckpointRecord(
                    run_id=run_id,
                    step=step,
                    state=state,  # tool_calls is actually the state dict
                    created_at=created_at,
                )
            )
        return records

    def _update_checkpoint(self, run_id: str, step: int, state: dict[str, Any]) -> None:
        """Update a checkpoint record."""
        cursor = self._conn.cursor()
        cursor.execute(
            "UPDATE conversation_steps SET tool_calls = ? WHERE run_id = ? AND step = ?",
            (json.dumps(state), run_id, step),
        )
        if cursor.rowcount == 0:
            raise CheckpointNotFound(
                f"No checkpoint found for run {run_id}, step {step}"
            )
        self._conn.commit()

    def _delete_checkpoints(self, run_id: str) -> None:
        """Delete all checkpoint records for a run_id."""
        cursor = self._conn.cursor()
        cursor.execute("DELETE FROM conversation_steps WHERE run_id = ?", (run_id,))
        self._conn.commit()

    def _delete_checkpoint(self, run_id: str, step: int) -> None:
        """Delete a specific checkpoint record."""
        cursor = self._conn.cursor()
        cursor.execute(
            "DELETE FROM conversation_steps WHERE run_id = ? AND step = ?",
            (run_id, step),
        )
        if cursor.rowcount == 0:
            raise CheckpointNotFound(
                f"No checkpoint found for run {run_id}, step {step}"
            )
        self._conn.commit()


class CheckpointerService:
    """Service layer for checkpoint CRUD operations with thread-safe singleton pattern."""

    def __init__(self, db_path: str | Path):
        self._crud = SQLiteCRUDMixin(db_path)

    def save_step(self, record: CheckpointRecord) -> None:
        """Save a checkpoint step."""
        self._crud._insert_checkpoint(record)

    def get_steps(self, run_id: str) -> list[CheckpointRecord]:
        """Get all steps for a run_id, sorted by step number."""
        return self._crud._select_checkpoints(run_id)

    def update_step(self, run_id: str, step: int, state: dict[str, Any]) -> None:
        """Update a specific step's state."""
        self._crud._update_checkpoint(run_id, step, state)

    def delete_run(self, run_id: str) -> None:
        """Delete all steps for a run_id."""
        self._crud._delete_checkpoints(run_id)

    def delete_step(self, run_id: str, step: int) -> None:
        """Delete a specific step."""
        self._crud._delete_checkpoint(run_id, step)


@lru_cache(maxsize=1)
def get_checkpointer_service(db_path: str | Path) -> CheckpointerService:
    """Get a singleton instance of the checkpointer service."""
    return CheckpointerService(db_path)


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
        now = datetime.now(UTC).isoformat()
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
