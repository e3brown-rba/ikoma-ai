"""
Dynamically created tool: sandbox_test_tool
Description: A test tool created in sandbox environment
Created in sandbox environment
"""

from typing import Any


# Define the tool decorator
def tool(func: Any) -> Any:
    """Simple tool decorator for sandbox environment."""
    return func


# Try to import the real tool decorator if available
try:
    from langchain.tools import tool as langchain_tool  # LangChain <=0.1.x

    tool = langchain_tool  # type: ignore
except ImportError:
    try:
        from langchain_core.tools import tool as langchain_tool  # New location

        tool = langchain_tool  # type: ignore
    except ImportError:
        # Use the fallback tool decorator defined above
        pass


@tool
def sandbox_test_tool(tool_input: str | None = None) -> str:
    """A test tool created in sandbox environment"""
    try:
        return "Hello from sandbox test tool! This tool was created safely within the sandbox environment."

    except Exception as e:
        return f"Error in sandbox_test_tool: {e}"
