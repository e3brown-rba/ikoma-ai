#!/usr/bin/env python3
"""
Test script for sandbox tool creation and loading functionality.
"""

import json
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.fs_tools import create_tool, list_sandbox_tools, load_sandbox_tool


def test_sandbox_tools():
    """Test the sandbox tool creation and loading functionality."""

    print("🧪 Testing Sandbox Tool Creation and Loading")
    print("=" * 50)

    # Test 1: List initial tools
    print("\n1. Listing initial sandbox tools:")
    result = list_sandbox_tools.invoke({})
    print(result)

    # Test 2: Create a simple test tool
    print("\n2. Creating a test tool:")
    test_tool_definition = {
        "name": "test_calculator",
        "description": "A simple calculator tool that adds two numbers",
        "code": """
        try:
            # This would normally come from tool parameters
            # For demo, we'll use hardcoded values
            a = 5
            b = 3
            result = a + b
            return f"Result: {a} + {b} = {result}"
        except Exception as e:
            return f"Error in calculation: {e}"
        """,
    }

    result = create_tool.invoke({"tool_definition": json.dumps(test_tool_definition)})
    print(result)

    # Test 3: List tools again to see the new tool
    print("\n3. Listing tools after creation:")
    result = list_sandbox_tools.invoke({})
    print(result)

    # Test 4: Load and execute the created tool
    print("\n4. Loading and executing the created tool:")
    result = load_sandbox_tool.invoke({"tool_name": "test_calculator"})
    print(result)

    # Test 5: Try to load a non-existent tool
    print("\n5. Testing error handling with non-existent tool:")
    result = load_sandbox_tool.invoke({"tool_name": "non_existent_tool"})
    print(result)

    print("\n✅ Sandbox tool tests completed!")


if __name__ == "__main__":
    test_sandbox_tools()
