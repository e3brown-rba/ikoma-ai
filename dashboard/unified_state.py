import re
import threading
from collections.abc import Callable
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


class DemoPhase(Enum):
    INITIALIZING = "initializing"
    PLANNING = "planning"
    EXECUTING = "executing"
    REFLECTING = "reflecting"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class UnifiedAgentState:
    agent_id: str
    name: str
    demo_type: str | None = None

    # Execution state
    status: AgentStatus = AgentStatus.IDLE
    phase: DemoPhase = DemoPhase.INITIALIZING
    current_step: str = "Idle"

    # Progress tracking
    progress: int = 0
    steps_completed: int = 0
    total_steps: int = 0

    # Plan integration
    current_plan: dict[str, Any] | None = None
    plan_version: int = 1

    # Real-time updates
    output_buffer: list[str] = field(default_factory=list)
    last_activity: datetime = field(default_factory=datetime.now)

    # Additional metadata
    start_time: datetime | None = None
    end_time: datetime | None = None
    error_message: str | None = None
    goal: str = ""
    execution_time: str = "00:00:00"

    def to_dict(self) -> dict[str, Any]:
        """Convert state to dictionary for JSON serialization"""
        return {
            "id": self.agent_id,
            "name": self.name,
            "status": self.status.value,
            "demo_type": self.demo_type,
            "phase": self.phase.value,
            "progress": self.progress,
            "current_step": self.current_step,
            "is_demo": self.demo_type is not None,
            "execution_time": self.execution_time,
            "goal": self.goal,
            "steps_completed": self.steps_completed,
            "total_steps": self.total_steps,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "output": self.output_buffer[-50:],  # Last 50 lines
            "error": self.error_message,
            "current_plan": self.current_plan,
            "plan_version": self.plan_version,
            "last_activity": self.last_activity.isoformat(),
        }

    def update_from_output(self, line: str) -> dict[str, Any]:
        """Extract state updates from agent output line"""
        changes: dict[str, Any] = {}
        line_lower = line.lower()

        # Track actual step completion from agent events
        if "broadcasting step_start:" in line_lower:
            # Extract step number from step_start event
            step_match = re.search(r"step_start.*?step_index.*?(\d+)", line_lower)
            if step_match:
                current_step = int(step_match.group(1))
                changes["steps_completed"] = max(
                    0, current_step - 1
                )  # Step started, so previous step completed
                changes["current_step"] = f"Executing step {current_step}"

        elif "broadcasting step_complete:" in line_lower:
            # Extract step number from step_complete event
            step_match = re.search(r"step_complete.*?step_index.*?(\d+)", line_lower)
            if step_match:
                current_step = int(step_match.group(1))
                changes["steps_completed"] = current_step
                changes["current_step"] = f"Completed step {current_step}"

        # Also look for step completion indicators in execution details
        elif "✓ step" in line_lower or ("step" in line_lower and ":" in line_lower):
            # Extract step number from execution details like "✓ Step 1: Create a new text file..."
            step_match = re.search(r"✓ step (\d+):", line_lower)
            if step_match:
                current_step = int(step_match.group(1))
                changes["steps_completed"] = current_step
                changes["current_step"] = f"Completed step {current_step}"

        # Phase detection
        elif "planning your request" in line_lower or "creating plan" in line_lower:
            changes["phase"] = DemoPhase.PLANNING
            changes["current_step"] = "Creating plan"
        elif "executing plan" in line_lower or "step" in line_lower:
            changes["phase"] = DemoPhase.EXECUTING
            if "step" in line_lower and not changes.get("steps_completed"):
                # Extract step info: "Step 1: create_text_file"
                step_match = re.search(r"step (\d+)", line_lower)
                if step_match:
                    changes["steps_completed"] = int(step_match.group(1))
        elif "reflection" in line_lower or "task completed" in line_lower:
            changes["phase"] = DemoPhase.REFLECTING
            changes["current_step"] = "Analyzing results"
        elif "completed" in line_lower or "finished" in line_lower:
            changes["phase"] = DemoPhase.COMPLETED
            changes["current_step"] = "Demo completed"

        # Progress calculation based on phase and steps
        if changes.get("phase"):
            phase_progress = {
                DemoPhase.PLANNING: 10,
                DemoPhase.EXECUTING: 70,
                DemoPhase.REFLECTING: 90,
                DemoPhase.COMPLETED: 100,
            }
            base_progress = phase_progress.get(changes["phase"], 0)

            if changes["phase"] == DemoPhase.EXECUTING and self.total_steps > 0:
                step_progress = (
                    changes.get("steps_completed", 0) / self.total_steps
                ) * 60
                changes["progress"] = min(base_progress + step_progress, 95)
            else:
                changes["progress"] = base_progress

        # If we have step completion but no phase change, update progress based on steps
        elif changes.get("steps_completed") is not None and self.total_steps > 0:
            step_progress = (changes["steps_completed"] / self.total_steps) * 100
            changes["progress"] = min(int(step_progress), 95)

        return changes

    def update_execution_time(self) -> None:
        """Calculate and update execution time."""
        if not self.start_time:
            self.execution_time = "00:00:00"
            return

        end = self.end_time or datetime.now()
        delta = end - self.start_time
        self.execution_time = str(delta).split(".")[0]  # Remove microseconds


class UnifiedStateManager:
    def __init__(self) -> None:
        self._agents: dict[str, UnifiedAgentState] = {}
        self._lock = threading.RLock()
        self._subscribers: list[Callable[[str, dict[str, Any]], None]] = []

    def create_agent(
        self, agent_id: str, name: str, demo_type: str | None = None
    ) -> UnifiedAgentState:
        """Create a new agent state"""
        with self._lock:
            agent_state = UnifiedAgentState(
                agent_id=agent_id,
                name=name,
                demo_type=demo_type,
                status=AgentStatus.RUNNING,
                start_time=datetime.now(),
                total_steps=self._get_demo_total_steps(demo_type),
            )
            self._agents[agent_id] = agent_state
            return agent_state

    def get_agent(self, agent_id: str) -> UnifiedAgentState | None:
        """Get agent state by ID"""
        with self._lock:
            return self._agents.get(agent_id)

    def list_agents(self) -> list[dict[str, Any]]:
        """Get all agents as dictionaries"""
        with self._lock:
            return [agent.to_dict() for agent in self._agents.values()]

    def get_running_agents(self) -> list[UnifiedAgentState]:
        """Get all running agents"""
        with self._lock:
            return [
                agent
                for agent in self._agents.values()
                if agent.status == AgentStatus.RUNNING
            ]

    def subscribe(self, callback: Callable[[str, dict[str, Any]], None]) -> None:
        """Subscribe to state changes"""
        with self._lock:
            self._subscribers.append(callback)

    def _notify_subscribers(self, agent_id: str, changes: dict[str, Any]) -> None:
        """Notify all subscribers of state changes"""
        # Convert enum values and datetime objects to strings for JSON serialization
        serializable_changes = {}
        for key, value in changes.items():
            if isinstance(value, DemoPhase | AgentStatus):
                serializable_changes[key] = value.value
            elif hasattr(value, "isoformat"):  # Handle datetime objects
                serializable_changes[key] = value.isoformat()
            else:
                serializable_changes[key] = value

        for callback in self._subscribers:
            try:
                callback(agent_id, serializable_changes)
            except Exception as e:
                print(f"Subscriber callback error: {e}")

    def update_from_output(self, agent_id: str, output_line: str) -> None:
        """Update agent state from output line and broadcast changes"""
        with self._lock:
            agent = self._agents.get(agent_id)
            if not agent:
                return

            # Extract changes from output
            changes = agent.update_from_output(output_line)

            # Apply changes
            for key, value in changes.items():
                setattr(agent, key, value)

            agent.output_buffer.append(output_line)
            agent.last_activity = datetime.now()

            # Broadcast changes
            if changes:
                self._notify_subscribers(agent_id, changes)

    def update_agent(self, agent_id: str, **updates: Any) -> None:
        """Update agent with specific fields"""
        with self._lock:
            agent = self._agents.get(agent_id)
            if not agent:
                return

            changes = {}
            for key, value in updates.items():
                if hasattr(agent, key):
                    setattr(agent, key, value)
                    changes[key] = value

            if changes:
                self._notify_subscribers(agent_id, changes)

    def set_completed(self, agent_id: str) -> None:
        """Mark agent as completed"""
        with self._lock:
            agent = self._agents.get(agent_id)
            if agent:
                agent.status = AgentStatus.COMPLETED
                agent.phase = DemoPhase.COMPLETED
                agent.progress = 100
                agent.end_time = datetime.now()
                agent.update_execution_time()
                self._notify_subscribers(
                    agent_id,
                    {
                        "status": AgentStatus.COMPLETED,
                        "phase": DemoPhase.COMPLETED,
                        "progress": 100,
                        "end_time": agent.end_time,
                    },
                )

    def set_error(self, agent_id: str, error: str) -> None:
        """Mark agent as error"""
        with self._lock:
            agent = self._agents.get(agent_id)
            if agent:
                agent.status = AgentStatus.ERROR
                agent.phase = DemoPhase.ERROR
                agent.error_message = error
                agent.end_time = datetime.now()
                agent.update_execution_time()
                self._notify_subscribers(
                    agent_id,
                    {
                        "status": AgentStatus.ERROR,
                        "phase": DemoPhase.ERROR,
                        "error_message": error,
                        "end_time": agent.end_time,
                    },
                )

    def delete_agent(self, agent_id: str) -> bool:
        """Delete agent state"""
        with self._lock:
            if agent_id in self._agents:
                del self._agents[agent_id]
                return True
            return False

    def get_agent_count_by_status(self, status: AgentStatus) -> int:
        """Get count of agents with specific status"""
        with self._lock:
            return sum(1 for agent in self._agents.values() if agent.status == status)

    def _get_demo_total_steps(self, demo_type: str | None) -> int:
        """Get expected total steps for demo type"""
        if not demo_type:
            return 5
        return {"online": 6, "offline": 3, "continuous": 8}.get(demo_type, 5)


# Global unified state manager
unified_state = UnifiedStateManager()
