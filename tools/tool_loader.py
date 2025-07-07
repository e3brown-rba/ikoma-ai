import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from .fs_tools import FILE_TOOLS


class ToolLoader:
    """Dynamic tool loader that reads MCP schema and loads tools once at startup."""

    def __init__(self, schema_path: Optional[str] = None):
        if schema_path is None:
            # Try to find the schema file relative to the project root
            current_dir = Path(__file__).parent
            candidate = current_dir / "mcp_schema.json"
            if candidate.exists():
                schema_path_obj = candidate
            else:
                schema_path_obj = Path("tools/mcp_schema.json")
        else:
            schema_path_obj = Path(schema_path)
        self.schema_path = schema_path_obj
        self.schema = self._load_schema()
        self._loaded_tools: Optional[List[Any]] = None

    def _load_schema(self) -> Dict[str, Any]:
        """Load the MCP schema from JSON file."""
        try:
            with open(self.schema_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            print(
                f"Warning: Schema file {self.schema_path} not found. Using default tools."
            )
            return {"tools": [], "categories": {}}
        except json.JSONDecodeError as e:
            print(f"Error parsing schema file: {e}")
            return {"tools": [], "categories": {}}

    def load_tools(self, llm: ChatOpenAI) -> List[Any]:
        """Load all tools based on the schema. Called once at startup."""
        if self._loaded_tools is not None:
            return self._loaded_tools

        tools = []

        # Load file system tools
        for tool_info in self.schema.get("tools", []):
            if tool_info["category"] == "file_system":
                # Find corresponding tool in FILE_TOOLS
                for file_tool in FILE_TOOLS:
                    if file_tool.name == tool_info["name"]:
                        tools.append(file_tool)
                        break

        # Load math tools
        math_tool_names = [
            tool["name"]
            for tool in self.schema.get("tools", [])
            if tool["category"] == "math"
        ]
        if math_tool_names:
            try:
                # Create a simple Calculator tool instead of using langchain's load_tools
                from langchain.tools import BaseTool  # type: ignore

                class Calculator(BaseTool):
                    name: str = "Calculator"
                    description: str = (
                        "Perform mathematical calculations and solve math problems"
                    )

                    def _run(self, question: str) -> str:
                        try:
                            # Simple eval for basic math - in production, use a safer approach
                            result = eval(question)
                            return f"The result of {question} is {result}"
                        except Exception as e:
                            return f"Error calculating {question}: {str(e)}"

                calculator = Calculator()
                tools.append(calculator)
            except Exception as e:
                print(f"Warning: Could not create Calculator tool: {e}")
        self._loaded_tools = tools
        return tools

    def get_tool_descriptions(self) -> str:
        """Get formatted descriptions of all available tools."""
        descriptions = []
        categories = self.schema.get("categories", {})

        for category, category_desc in categories.items():
            descriptions.append(f"\n{category_desc.upper()}:")

            category_tools = [
                tool
                for tool in self.schema.get("tools", [])
                if tool["category"] == category
            ]

            for tool in category_tools:
                descriptions.append(f"  - {tool['name']}: {tool['description']}")

        return "\n".join(descriptions)

    def get_tool_by_name(self, name: str) -> Any:
        """Get a specific tool by name."""
        if self._loaded_tools is None:
            return None

        for tool in self._loaded_tools:
            if tool.name == name:
                return tool
        return None

    def get_schema_version(self) -> str:
        """Get the schema version."""
        return self.schema.get("version", "unknown")


# Global instance for single loading
tool_loader = ToolLoader()
