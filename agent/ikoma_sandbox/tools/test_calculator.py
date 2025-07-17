"""
Dynamically created tool: test_calculator
Description: A simple calculator tool that adds two numbers
Created in sandbox environment
"""

try:
    from langchain.tools import tool  # LangChain <=0.1.x
except ImportError:
    try:
        from langchain_core.tools import tool  # New location
    except ImportError:
        # Fallback for demo environment
        def tool(func):
            return func


@tool
def test_calculator() -> str:
    """A simple calculator tool that adds two numbers"""
    try:
        try:
            # This would normally come from tool parameters
            # For demo, we'll use hardcoded values
            a = 5
            b = 3
            result = a + b
            return f"Result: {a} + {b} = {result}"
        except Exception as e:
            return f"Error in calculation: {e}"

    except Exception as e:
        return f"Error in test_calculator: {e}"
