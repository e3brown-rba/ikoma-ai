from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AgentEvent(BaseModel):
    type: str  # Allow any string for flexibility
    data: dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class EventsResponse(BaseModel):
    events: list[AgentEvent]
    latest_timestamp: datetime
    has_more: bool


class PlanSummary(BaseModel):
    id: str
    goal: str
    steps: list[dict[str, Any]]
    created_at: datetime
    status: str


class ExecutionTrace(BaseModel):
    execution_id: str
    events: list[AgentEvent]
    duration_seconds: float
    status: str
