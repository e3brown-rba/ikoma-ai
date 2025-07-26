import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class AgentStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"
    STOPPED = "stopped"
    DELETED = "deleted"


@dataclass
class AgentState:
    agent_id: str
    name: str
    status: AgentStatus
    demo_type: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    output_lines: list[str] = field(default_factory=list)
    error_message: str | None = None
    progress: int = 0
    current_step: str = "Idle"
    goal: str = ""
    steps_completed: int = 0
    total_steps: int = 0
    execution_time: str = "00:00:00"
    latest_plan: dict[str, Any] | None = None
    plan_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.agent_id,
            "name": self.name,
            "status": self.status.value,
            "demo_type": self.demo_type,
            "progress": self.progress,
            "current_step": self.current_step,
            "is_demo": self.demo_type is not None,
            "execution_time": self.execution_time,
            "goal": self.goal,
            "steps_completed": self.steps_completed,
            "total_steps": self.total_steps,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "output": self.output_lines,
            "error": self.error_message,
        }

    def update_progress(
        self, progress: int, steps_completed: int, total_steps: int
    ) -> None:
        """Update progress information."""
        self.progress = progress
        self.steps_completed = steps_completed
        self.total_steps = total_steps

    def update_execution_time(self) -> None:
        """Calculate and update execution time."""
        if not self.start_time:
            self.execution_time = "00:00:00"
            return

        end = self.end_time or datetime.now()
        delta = end - self.start_time
        self.execution_time = str(delta).split(".")[0]  # Remove microseconds

    def add_output_line(self, line: str) -> None:
        """Add a line to the output."""
        self.output_lines.append(line.strip())

    def set_error(self, error: str) -> None:
        """Set error message and update status."""
        self.error_message = error
        self.status = AgentStatus.ERROR

    def update_plan_data(self, plan_data: str, plan_version: int | None = None) -> None:
        """Update plan information."""
        if plan_version:
            self.plan_version = plan_version

        self.latest_plan = {
            "plan_id": f"plan-{self.agent_id}-v{self.plan_version}",
            "plan_version": self.plan_version,
            "plan_data": plan_data,
            "progress": self.progress,
            "status": self.status.value,
        }


class StateManager:
    def __init__(self) -> None:
        self._agents: dict[str, AgentState] = {}
        self._lock = threading.RLock()

    def create_agent(
        self, agent_id: str, name: str, demo_type: str | None = None
    ) -> AgentState:
        """Create a new agent state."""
        with self._lock:
            agent = AgentState(
                agent_id=agent_id,
                name=name,
                status=AgentStatus.IDLE,
                demo_type=demo_type,
                start_time=datetime.now(),
                goal=self._get_demo_goal(demo_type)
                if demo_type
                else "User-defined goal",
            )
            self._agents[agent_id] = agent
            return agent

    def get_agent(self, agent_id: str) -> AgentState | None:
        """Get agent state by ID."""
        with self._lock:
            return self._agents.get(agent_id)

    def update_agent(self, agent_id: str, **updates: Any) -> None:
        """Update agent state with provided fields."""
        with self._lock:
            if agent_id in self._agents:
                agent = self._agents[agent_id]
                for key, value in updates.items():
                    if hasattr(agent, key):
                        setattr(agent, key, value)

    def update_agent_status(
        self, agent_id: str, status: AgentStatus, **additional_updates: Any
    ) -> None:
        """Update agent status and optionally other fields."""
        with self._lock:
            if agent_id in self._agents:
                agent = self._agents[agent_id]
                agent.status = status

                # Update end time if completed or stopped
                if status in [
                    AgentStatus.COMPLETED,
                    AgentStatus.ERROR,
                    AgentStatus.STOPPED,
                ]:
                    agent.end_time = datetime.now()
                    agent.update_execution_time()

                # Apply additional updates
                for key, value in additional_updates.items():
                    if hasattr(agent, key):
                        setattr(agent, key, value)

    def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent from the state manager."""
        with self._lock:
            if agent_id in self._agents:
                del self._agents[agent_id]
                return True
            return False

    def list_agents(self) -> list[dict[str, Any]]:
        """Get list of all agents as dictionaries."""
        with self._lock:
            return [agent.to_dict() for agent in self._agents.values()]

    def get_running_agents(self) -> list[AgentState]:
        """Get list of currently running agents."""
        with self._lock:
            return [
                agent
                for agent in self._agents.values()
                if agent.status == AgentStatus.RUNNING
            ]

    def get_all_agents(self) -> list[AgentState]:
        """Get list of all agents."""
        with self._lock:
            return list(self._agents.values())

    def get_agent_count_by_status(self, status: AgentStatus) -> int:
        """Get count of agents with specific status."""
        with self._lock:
            return sum(1 for agent in self._agents.values() if agent.status == status)

    def broadcast_progress_update(
        self, agent_id: str, progress_data: dict[str, Any]
    ) -> None:
        """Broadcast progress updates for real-time UI sync."""
        with self._lock:
            if agent_id in self._agents:
                agent = self._agents[agent_id]

                # Update the agent's progress data
                agent.update_progress(
                    progress_data["progress"],
                    progress_data["steps_completed"],
                    progress_data["total_steps"],
                )
                agent.current_step = progress_data.get(
                    "current_step", agent.current_step
                )

                try:
                    from dashboard.sse_manager import sse_manager

                    sse_manager.broadcast_from_thread(
                        agent_id,
                        "progress_update",
                        {"agent": agent.to_dict(), "progress_data": progress_data},
                    )
                except Exception as e:
                    print(f"Failed to broadcast progress update: {e}")

    def broadcast_step_change(self, agent_id: str, step_data: dict[str, Any]) -> None:
        """Broadcast step changes for plan execution tracking."""
        with self._lock:
            if agent_id in self._agents:
                agent = self._agents[agent_id]
                agent.current_step = step_data.get(
                    "step_description", agent.current_step
                )

                try:
                    from dashboard.sse_manager import sse_manager

                    sse_manager.broadcast_from_thread(
                        agent_id,
                        "step_change",
                        {"agent": agent.to_dict(), "step_data": step_data},
                    )
                except Exception as e:
                    print(f"Failed to broadcast step change: {e}")

    def _get_demo_goal(self, demo_type: str) -> str:
        """Get the goal description for demo types."""
        goals = {
            "online": "Search the web and gather information about current events",
            "offline": "Analyze local files and provide insights",
            "continuous": "Run continuously and adapt to changing conditions",
        }
        return goals.get(demo_type, "Execute demo tasks")


# Global state manager instance
state_manager = StateManager()
