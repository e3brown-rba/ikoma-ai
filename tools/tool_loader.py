import ast
import json
from pathlib import Path
from typing import Any

from langchain_openai import ChatOpenAI

from .fs_tools import FILE_TOOLS
from .internet_tools import (
    check_domain_allowed,
    get_domain_filter_status,
    list_allowed_domains,
    list_denied_domains,
    reload_domain_filter_config,
    validate_url_for_access,
)
from .web_tools import (
    extract_web_content,
    get_web_extraction_status,
    search_web,
    search_web_memories,
)


class ToolLoader:
    """Dynamic tool loader that reads MCP schema and loads tools once at startup."""

    def __init__(self, schema_path: str | None = None):
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
        self._loaded_tools: list[Any] | None = None

    def _load_schema(self) -> Any:
        """Load the MCP schema from JSON file."""
        try:
            with open(self.schema_path) as f:
                return json.load(f)
        except FileNotFoundError:
            print(
                f"Warning: Schema file {self.schema_path} not found. Using default tools."
            )
            return {"tools": [], "categories": {}}
        except json.JSONDecodeError as e:
            print(f"Error parsing schema file: {e}")
            return {"tools": [], "categories": {}}

    def load_tools(self, llm: ChatOpenAI) -> list[Any]:
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

        # Load internet tools
        internet_tools = {
            "check_domain_allowed": check_domain_allowed,
            "get_domain_filter_status": get_domain_filter_status,
            "list_allowed_domains": list_allowed_domains,
            "list_denied_domains": list_denied_domains,
            "reload_domain_filter_config": reload_domain_filter_config,
            "validate_url_for_access": validate_url_for_access,
            "search_web": search_web,
        }

        for tool_info in self.schema.get("tools", []):
            if tool_info["category"] == "internet":
                tool_name = tool_info["name"]
                if tool_name in internet_tools:
                    tools.append(internet_tools[tool_name])

        # Load web tools
        web_tools = {
            "extract_web_content": extract_web_content,
            "search_web_memories": search_web_memories,
            "get_web_extraction_status": get_web_extraction_status,
        }

        for tool_info in self.schema.get("tools", []):
            if tool_info["category"] == "web":
                tool_name = tool_info["name"]
                if tool_name in web_tools:
                    tools.append(web_tools[tool_name])

        # Load math tools
        math_tool_names = [
            tool["name"]
            for tool in self.schema.get("tools", [])
            if tool["category"] == "math"
        ]
        if math_tool_names:
            try:
                # Create a simple Calculator tool instead of using langchain's load_tools
                from langchain.tools import BaseTool

                class Calculator(BaseTool):
                    name: str = "Calculator"
                    description: str = (
                        "Perform mathematical calculations and solve math problems"
                    )

                    def _run(self, question: str) -> str:
                        try:
                            # Safe evaluation of math expressions using AST
                            result = self._safe_eval(question)
                            return f"The result of {question} is {result}"
                        except Exception as e:
                            return f"Error calculating {question}: {str(e)}"

                    def _safe_eval(self, expr: str) -> float:
                        """Safely evaluate basic math expressions."""
                        # Parse the expression into an AST
                        node = ast.parse(expr, mode="eval")
                        return self._eval_node(node.body)

                    def _eval_node(self, node: ast.AST) -> float:
                        """Recursively evaluate AST nodes for basic math operations."""
                        if isinstance(node, ast.Constant):
                            if isinstance(node.value, int | float):
                                return float(node.value)
                            else:
                                raise ValueError(
                                    f"Unsupported constant type: {type(node.value)}"
                                )
                        elif isinstance(node, ast.BinOp):
                            left = self._eval_node(node.left)
                            right = self._eval_node(node.right)
                            if isinstance(node.op, ast.Add):
                                return float(left + right)
                            elif isinstance(node.op, ast.Sub):
                                return float(left - right)
                            elif isinstance(node.op, ast.Mult):
                                return float(left * right)
                            elif isinstance(node.op, ast.Div):
                                return float(left / right)
                            elif isinstance(node.op, ast.Pow):
                                return float(left**right)
                            elif isinstance(node.op, ast.Mod):
                                return float(left % right)
                            else:
                                raise ValueError(
                                    f"Unsupported operation: {type(node.op)}"
                                )
                        elif isinstance(node, ast.UnaryOp):
                            operand = self._eval_node(node.operand)
                            if isinstance(node.op, ast.UAdd):
                                return float(+operand)
                            elif isinstance(node.op, ast.USub):
                                return float(-operand)
                            else:
                                raise ValueError(
                                    f"Unsupported unary operation: {type(node.op)}"
                                )
                        else:
                            raise ValueError(f"Unsupported node type: {type(node)}")

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

    def get_tool_by_name(self, name: str) -> Any | None:
        """Get a specific tool by name."""
        if self._loaded_tools is None:
            return None

        for tool in self._loaded_tools:
            if tool.name == name:
                return tool
        return None

    def get_schema_version(self) -> str:
        """Get the schema version."""
        return str(self.schema.get("version", "unknown"))

    def get_tool_names(self) -> list[str]:
        """Get list of available tool names from the schema."""
        return [tool["name"] for tool in self.schema.get("tools", [])]


# Global instance for single loading
tool_loader = ToolLoader()
