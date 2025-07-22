"""Dashboard models for agent events and state."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AgentEvent(BaseModel):
    """Standardized agent event model for dashboard and TUI communication."""

    type: str
    data: dict[str, Any]
    timestamp: datetime = datetime.now()

    model_config = ConfigDict(arbitrary_types_allowed=True)


class AgentStatus(BaseModel):
    """Agent status information for dashboard display."""

    agent_id: str
    status: str  # "running", "stopped", "error"
    goal: str | None = None
    current_step: str | None = None
    iteration: int = 0
    max_iterations: int = 0
    start_time: datetime | None = None
    last_update: datetime = datetime.now()

    model_config = ConfigDict(arbitrary_types_allowed=True)


class DemoStatus(BaseModel):
    """Demo status information for dashboard display."""

    demo_id: str
    status: str  # "running", "stopped", "error"
    scenario: str  # "online", "offline", "continuous"
    goal: str
    start_time: datetime | None = None
    last_update: datetime = datetime.now()
    output: str = ""

    model_config = ConfigDict(arbitrary_types_allowed=True)
