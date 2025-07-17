from enum import Enum

from rich.table import Table


class StatusIndicator(Enum):
    IDLE = ("○", "grey50")
    PLANNING = ("◐", "blue")
    EXECUTING = ("●", "green")
    REFLECTING = ("◑", "yellow")
    COMPLETE = ("✓", "green")
    ERROR = ("✗", "red")


class PlanStatusTable:
    def __init__(self) -> None:
        self.table = Table(title="Execution Plan")
        self.setup_columns()

    def setup_columns(self) -> None:
        self.table.add_column("Step", style="cyan", width=4)
        self.table.add_column("Tool", style="magenta", width=15)
        self.table.add_column("Description", style="white", min_width=30)
        self.table.add_column("Status", style="green", width=12)
        self.table.add_column("Result", style="yellow", width=20)

    def update_plan(
        self, plan_steps: list[dict], execution_results: list[dict]
    ) -> None:
        """Update table with current plan and execution status"""
        self.table = Table(title="Execution Plan")
        self.setup_columns()

        for i, step in enumerate(plan_steps):
            status_indicator, status_color = self._get_step_status(
                step, execution_results, i
            )
            result_text = self._get_step_result(execution_results, i)

            self.table.add_row(
                str(step.get("step", i + 1)),
                step.get("tool_name", "unknown"),
                step.get("description", ""),
                f"[{status_color}]{status_indicator}[/{status_color}]",
                result_text,
            )

    def _get_step_status(
        self, step: dict, results: list[dict], step_index: int
    ) -> tuple[str, str]:
        """Determine step status with color coding"""
        if step_index < len(results):
            result = results[step_index]
            if result.get("status") == "success":
                return StatusIndicator.COMPLETE.value
            else:
                return StatusIndicator.ERROR.value
        return StatusIndicator.IDLE.value

    def _get_step_result(self, results: list[dict], step_index: int) -> str:
        if step_index < len(results):
            return str(results[step_index].get("result", ""))
        return ""


class InternetStatusBadge:
    def render(
        self, internet_enabled: bool, rate_limit_info: dict | None = None
    ) -> str:
        """Render internet connectivity badge"""
        if internet_enabled:
            badge_text = "🌐 ONLINE"
            badge_color = "green"
            if rate_limit_info and rate_limit_info.get("remaining", 0) < 10:
                badge_color = "yellow"
                badge_text += f" ({rate_limit_info['remaining']} left)"
        else:
            badge_text = "📱 OFFLINE"
            badge_color = "red"

        return f"[{badge_color}]{badge_text}[/{badge_color}]"
