from typing import Any


def format_agent_status(state: dict[str, Any]) -> str:
    status = state.get("status", "IDLE")
    return f"Status: {status}"


def format_execution_result(result: dict[str, Any]) -> str:
    return str(result.get("result", ""))
