import queue
import threading
import time
from collections import deque
from datetime import datetime
from typing import Any

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel

from agent.ui.components import InternetStatusBadge, PlanStatusTable
from agent.ui.state_broadcaster import broadcaster


def safe_get(d, key, default=None):
    return d[key] if d and key in d else default


class AsyncLogger:
    def __init__(self, filename="ikoma_agent.log"):
        self.filename = filename
        self.log_queue = queue.Queue()
        self.running = True
        self.thread = threading.Thread(target=self._log_worker, daemon=True)
        self.thread.start()

    def _log_worker(self):
        with open(self.filename, "a", encoding="utf-8") as f:
            while self.running:
                try:
                    entry = self.log_queue.get(timeout=1)
                    timestamp = datetime.now().isoformat()
                    f.write(f"{timestamp} - {entry}\n")
                    f.flush()  # Force write immediately
                except queue.Empty:
                    continue

    def log(self, level, message, data=None):
        entry = f"{level}: {message}"
        if data:
            entry += f" | Data: {data}"
        self.log_queue.put(entry)

    def stop(self):
        self.running = False


class IkomaTUI:
    def __init__(self, refresh_rate: int = 4):
        self.console = Console()
        self.refresh_rate = refresh_rate
        self.layout = Layout()
        self.agent_state: dict[str, Any] = {}
        self.execution_history = deque(maxlen=50)
        self.changelog = deque(maxlen=30)  # New: running changelog
        self.internet_enabled = False
        self.start_time = time.time()
        self.plan_steps = []
        self.execution_results = []

        # Setup async logging
        self.async_logger = AsyncLogger()
        print("[TUI DEBUG] TUI initialized")  # Console debug

        self.setup_layout()
        self.subscribe_events()

    def setup_layout(self):
        """Create responsive layout matching action plan requirements"""
        self.layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", ratio=2),
            Layout(name="changelog", size=8),  # New: changelog panel
            Layout(name="footer", size=8),
        )

        self.layout["main"].split_row(
            Layout(name="plan_status", ratio=2), Layout(name="context", ratio=1)
        )

    def subscribe_events(self):
        print("[TUI DEBUG] Subscribing to events")  # Console debug
        broadcaster.subscribe("planning_start", self.on_planning_start)
        broadcaster.subscribe("plan_generated", self.on_plan_generated)
        broadcaster.subscribe("step_start", self.on_step_start)
        broadcaster.subscribe("step_complete", self.on_step_complete)
        broadcaster.subscribe("reflection", self.on_reflection)
        broadcaster.subscribe("reflection_error", self.on_reflection_error)
        print("[TUI DEBUG] Event subscriptions complete")  # Console debug

    def on_planning_start(self, data):
        print(f"[TUI DEBUG] Planning started: {data}")  # Console debug
        self.async_logger.log(
            "PLANNING_START", f"Planning started: {data.get('user_request', '')}", data
        )
        self.agent_state["planning"] = True
        self.agent_state["user_request"] = data.get("user_request")
        self.agent_state["memory_context"] = data.get("memory_context")
        self.plan_steps = []
        self.execution_results = []
        message = f"Planning started: {data.get('user_request', '')}"
        self.changelog.appendleft(message)

    def on_plan_generated(self, data):
        print(f"[TUI DEBUG] Plan generated: {data}")  # Console debug
        self.async_logger.log(
            "PLAN_GENERATED",
            f"Plan generated with {data.get('step_count', 0)} steps",
            data,
        )
        self.agent_state["planning"] = False
        self.plan_steps = data.get("plan", [])
        self.agent_state["step_count"] = data.get("step_count", 0)
        message = f"Plan generated ({data.get('step_count', 0)} steps)"
        self.changelog.appendleft(message)
        # Optionally, show plan reasoning if available
        if "reasoning" in data:
            reasoning_msg = f"Reasoning: {data['reasoning']}"
            self.changelog.appendleft(reasoning_msg)
            self.async_logger.log("PLAN_REASONING", data["reasoning"])

    def on_step_start(self, data):
        print(f"[TUI DEBUG] Step start: {data}")  # Console debug
        self.async_logger.log(
            "STEP_START",
            f"Step {data.get('step_index')} started: {data.get('tool_name')} - {data.get('description')}",
            data,
        )
        self.agent_state["current_step"] = data.get("step_index")
        self.agent_state["current_tool"] = data.get("tool_name")
        self.agent_state["current_description"] = data.get("description")
        message = f"Step {data.get('step_index')} started: {data.get('tool_name')} - {data.get('description')}"
        self.changelog.appendleft(message)

    def on_step_complete(self, data):
        print(f"[TUI DEBUG] Step complete: {data}")  # Console debug
        self.async_logger.log(
            "STEP_COMPLETE",
            f"Step {data.get('step_index')} {data.get('status')}: {data.get('result')}",
            data,
        )
        idx = data.get("step_index", 0)
        while len(self.execution_results) < idx:
            self.execution_results.append({})
        if len(self.execution_results) == idx:
            self.execution_results.append(data)
        else:
            self.execution_results[idx] = data
        status = data.get("status", "?")
        result = data.get("result", "")
        message = f"Step {idx} {status}: {result}"
        self.changelog.appendleft(message)

    def on_reflection(self, data):
        print(f"[TUI DEBUG] Reflection: {data}")  # Console debug
        self.async_logger.log(
            "REFLECTION",
            f"Reflection: {data.get('reasoning', '')} | Summary: {data.get('summary', '')} | Success Rate: {data.get('success_rate', '')}",
            data,
        )
        if data.get("reasoning"):
            message = f"Reflection: {data['reasoning']}"
            self.changelog.appendleft(message)
        if data.get("summary"):
            message = f"Summary: {data['summary']}"
            self.changelog.appendleft(message)
        if data.get("success_rate"):
            message = f"Success Rate: {data['success_rate']}"
            self.changelog.appendleft(message)
        if data.get("task_completed") is not None:
            status = (
                "Task Completed" if data["task_completed"] else "Task Not Completed"
            )
            message = status
            self.changelog.appendleft(message)

    def on_reflection_error(self, data):
        print(f"[TUI DEBUG] Reflection error: {data}")  # Console debug
        self.async_logger.log(
            "REFLECTION_ERROR", f"Reflection error: {data.get('error')}", data
        )
        message = f"Reflection Error: {data.get('error')}"
        self.changelog.appendleft(message)
        if data.get("raw_response"):
            raw_msg = f"Raw Response: {data['raw_response']}"
            self.changelog.appendleft(raw_msg)

    def update_display(self):
        # Header
        self.layout["header"].update(
            Panel(
                "Ikoma Agent TUI - [bold green]Monitoring[/bold green]",
                style="bold blue",
            )
        )
        # Plan Status Table
        plan_table = PlanStatusTable()
        plan_table.update_plan(self.plan_steps, self.execution_results)
        self.layout["plan_status"].update(plan_table.table)
        # Context
        context_text = (
            f"User Request: {safe_get(self.agent_state, 'user_request', '')}\n"
        )
        if self.agent_state.get("memory_context"):
            context_text += f"\nMemory Context:\n{self.agent_state['memory_context']}"
        self.layout["context"].update(Panel(context_text, title="Context"))
        # Changelog panel - use simple text for now
        changelog_text = "\n".join(list(self.changelog)[:8])
        self.layout["changelog"].update(
            Panel(
                changelog_text,
                title="Agent Changelog / Thought Process",
                border_style="magenta",
            )
        )
        # Footer: Internet status badge (placeholder)
        badge = InternetStatusBadge().render(self.internet_enabled)
        self.layout["footer"].update(Panel(badge, title="Status"))

    def start_monitoring(self, agent_state_callback=None):
        """Start TUI monitoring with live updates"""
        print("[TUI DEBUG] TUI monitoring started")  # Console debug
        self.async_logger.log("TUI_START", "TUI monitoring started")
        with Live(
            self.layout, refresh_per_second=self.refresh_rate, screen=True
        ) as live:
            while True:
                self.update_display()
                live.update(self.layout)
                time.sleep(1.0 / self.refresh_rate)

    def __del__(self):
        if hasattr(self, "async_logger"):
            self.async_logger.stop()
