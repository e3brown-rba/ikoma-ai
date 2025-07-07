"""
Fallback tool decorator for when langchain tools are not available.
This module provides a no-op decorator that can be imported when the main langchain imports fail.
"""

from typing import Callable, TypeVar, cast

T = TypeVar('T')

def tool(fn: T) -> T:
    """No-op decorator for when langchain tools are not available."""
    return fn

# Export as a callable for type safety
tool_callable = cast(Callable, tool) 