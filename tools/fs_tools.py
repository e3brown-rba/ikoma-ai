import os
import re
from pathlib import Path

try:
    from langchain.tools import tool  # LangChain <=0.1.x
except ImportError:
    try:
        from langchain_core.tools import tool  # New location
    except ImportError:
        from .tool_fallback import tool_callable as _tool_fallback

        tool = _tool_fallback

# Sandbox configuration
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
SANDBOX = (
    Path(os.getenv("SANDBOX_PATH", PROJECT_ROOT / "agent/ikoma_sandbox"))
    .expanduser()
    .resolve()
)

# Repository root (project root)
REPO_ROOT = Path(__file__).parent.parent


def confirm_destructive_action(action_description: str, filename: str) -> bool:
    """Ask user for confirmation before performing destructive file operations."""
    print("\n⚠️  CONFIRMATION REQUIRED:")
    print(f"   Action: {action_description}")
    print(f"   File: {filename}")

    while True:
        response = input("   Continue? (yes/no): ").strip().lower()
        if response in ["yes", "y"]:
            return True
        elif response in ["no", "n"]:
            return False
        else:
            print("   Please enter 'yes' or 'no'")


@tool
def list_sandbox_files(query: str = "") -> str:
    """List all files in the sandbox directory. No input needed."""
    SANDBOX.mkdir(parents=True, exist_ok=True)
    try:
        files = os.listdir(SANDBOX)
        if not files:
            return "📁 Sandbox directory is empty. Create some files to get started!"
        file_list = [
            f"📄 {file} ({os.path.getsize(os.path.join(SANDBOX, file))} bytes)"
            for file in files
        ]
        return "Files in sandbox:\n" + "\n".join(file_list)
    except Exception as e:
        return f"Error listing files: {e}"


@tool
def update_text_file(filename_and_content: str) -> str:
    """Update/modify an existing text file in the sandbox. Format: filename|||new_content"""
    SANDBOX.mkdir(parents=True, exist_ok=True)
    try:
        if "|||" not in filename_and_content:
            return "Error: Use format 'filename|||new_content'"
        filename, content = filename_and_content.split("|||", 1)
        filename = filename.strip()
        if not filename.endswith(".txt"):
            filename += ".txt"
        filepath = os.path.join(SANDBOX, filename)
        if not os.path.exists(filepath):
            return f"File '{filename}' not found. Use create_text_file to create new files."

        # Request confirmation before overwriting
        if not confirm_destructive_action("Overwrite existing file", filename):
            return f"❌ Operation cancelled: File '{filename}' was not modified."

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return f"✓ Updated file: {filename} with new content."
    except Exception as e:
        return f"Error updating file: {e}"


@tool
def create_text_file(filename_and_content: str) -> str:
    """Create a NEW text file in the sandbox. Format: filename|||content"""
    SANDBOX.mkdir(parents=True, exist_ok=True)
    try:
        if "|||" not in filename_and_content:
            return "Error: Use format 'filename|||content'"
        filename, content = filename_and_content.split("|||", 1)
        filename = filename.strip()
        if not filename.endswith(".txt"):
            filename += ".txt"
        filepath = os.path.join(SANDBOX, filename)
        if os.path.exists(filepath):
            return f"File '{filename}' already exists. Use update_text_file."

        # Request confirmation before creating new file
        if not confirm_destructive_action("Create new file", filename):
            return f"❌ Operation cancelled: File '{filename}' was not created."

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return f"✓ Created file: {filename} with content."
    except Exception as e:
        return f"Error creating file: {e}"


@tool
def read_text_file(filename: str) -> str:
    """Read a text file from the sandbox. If no filename provided, list available files."""
    SANDBOX.mkdir(parents=True, exist_ok=True)
    try:
        filename = filename.strip()
        if not filename:
            files = os.listdir(SANDBOX)
            return (
                f"Available files: {', '.join(files)}"
                if files
                else "No files in sandbox."
            )
        if not filename.endswith(".txt"):
            filename += ".txt"
        filepath = os.path.join(SANDBOX, filename)
        if not os.path.exists(filepath):
            files = os.listdir(SANDBOX)
            return f"File '{filename}' not found. Available: {', '.join(files) if files else 'none'}"
        with open(filepath, encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"


@tool
def scan_sandbox_files(
    pattern: str = "TODO|FIXME", file_extension: str = ".py,.md,.txt"
) -> str:
    """Scan sandbox files for specific patterns (like TODO, FIXME comments).
    Args:
        pattern: Regex pattern to search for (default: TODO|FIXME)
        file_extension: Comma-separated file extensions to scan (default: .py,.md,.txt)
    """
    try:
        extensions = [ext.strip() for ext in file_extension.split(",")]
        results = []

        # Ensure sandbox exists
        SANDBOX.mkdir(parents=True, exist_ok=True)

        for root, dirs, files in os.walk(SANDBOX):
            # Skip hidden directories and common exclusions
            dirs[:] = [
                d for d in dirs if not d.startswith(".") and d not in ["__pycache__"]
            ]

            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, encoding="utf-8") as f:
                            content = f.read()
                            matches = re.finditer(pattern, content, re.IGNORECASE)
                            file_matches = []
                            for match in matches:
                                line_num = content[: match.start()].count("\n") + 1
                                line_start = content.rfind("\n", 0, match.start()) + 1
                                line_end = content.find("\n", match.end())
                                if line_end == -1:
                                    line_end = len(content)
                                line_content = content[line_start:line_end].strip()
                                file_matches.append(f"Line {line_num}: {line_content}")

                            if file_matches:
                                rel_path = os.path.relpath(filepath, SANDBOX)
                                results.append(f"\n📄 {rel_path}:")
                                results.extend([f"  {match}" for match in file_matches])
                    except Exception as e:
                        results.append(f"\n❌ Error reading {file}: {e}")

        if not results:
            return f"No {pattern} comments found in sandbox {file_extension} files."

        return "Found TODO/FIXME comments in sandbox:\n" + "\n".join(results)
    except Exception as e:
        return f"Error scanning sandbox: {e}"


@tool
def create_tool(tool_definition: str) -> str:
    """Create a new tool dynamically within the sandbox environment.
    Args:
        tool_definition: JSON string with tool name, description, and implementation
    """
    try:
        import json

        # Parse tool definition
        tool_data = json.loads(tool_definition)
        tool_name = tool_data.get("name")
        tool_description = tool_data.get("description")
        tool_code = tool_data.get("code")

        if not all([tool_name, tool_description, tool_code]):
            return "Error: Tool definition must include name, description, and code"

        # Create tools directory in sandbox if it doesn't exist
        sandbox_tools_dir = SANDBOX / "tools"
        sandbox_tools_dir.mkdir(parents=True, exist_ok=True)

        # Create the tool file in sandbox
        tool_file = sandbox_tools_dir / f"{tool_name}.py"

        # Check if tool already exists
        if tool_file.exists():
            return f"Error: Tool '{tool_name}' already exists in sandbox"

        # Indent tool_code for function body
        indented_code = (
            tool_code
            if tool_code.startswith("        ")
            else "        " + tool_code.replace("\n", "\n        ")
        )

        # Write the tool code to sandbox
        tool_content = f'''"""
Dynamically created tool: {tool_name}
Description: {tool_description}
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
def {tool_name}(tool_input=None) -> str:
    """{tool_description}"""
    try:
{indented_code}
    except Exception as e:
        return f"Error in {tool_name}: {{e}}"
'''

        with open(tool_file, "w", encoding="utf-8") as f:
            f.write(tool_content)

        return f"✓ Successfully created tool '{tool_name}' in sandbox at: {tool_file}"

    except Exception as e:
        return f"Error creating tool: {e}"


@tool
def list_sandbox_tools() -> str:
    """List all tools available in the sandbox environment."""
    try:
        sandbox_tools_dir = SANDBOX / "tools"
        if not sandbox_tools_dir.exists():
            return "📁 No tools directory found in sandbox. Use create_tool to create new tools."

        tools = list(sandbox_tools_dir.glob("*.py"))
        if not tools:
            return "📁 No tools found in sandbox. Use create_tool to create new tools."

        tool_list = []
        for tool_file in tools:
            tool_name = tool_file.stem
            size = tool_file.stat().st_size
            tool_list.append(f"🔧 {tool_name} ({size} bytes)")

        return "Tools available in sandbox:\n" + "\n".join(tool_list)
    except Exception as e:
        return f"Error listing sandbox tools: {e}"


@tool
def load_sandbox_tool(tool_name: str) -> str:
    """Load and execute a tool from the sandbox environment.
    Args:
        tool_name: Name of the tool to load (without .py extension)
    """
    try:
        import importlib.util

        sandbox_tools_dir = SANDBOX / "tools"
        tool_file = sandbox_tools_dir / f"{tool_name}.py"

        if not tool_file.exists():
            available = (
                list(sandbox_tools_dir.glob("*.py"))
                if sandbox_tools_dir.exists()
                else []
            )
            available_names = [f.stem for f in available]
            return f"Error: Tool '{tool_name}' not found. Available tools: {', '.join(available_names) if available_names else 'none'}"

        # Load the tool module
        spec = importlib.util.spec_from_file_location(f"sandbox_{tool_name}", tool_file)
        if spec is None:
            return f"Error: Could not create module spec for {tool_name}"

        module = importlib.util.module_from_spec(spec)
        if spec.loader is None:
            return f"Error: Could not load module for {tool_name}"

        spec.loader.exec_module(module)

        # Get the tool function
        tool_func = getattr(module, tool_name, None)
        if tool_func is None:
            return f"Error: Tool function '{tool_name}' not found in module"

        # Execute the tool using LangChain's .invoke({}) interface
        try:
            result = tool_func.invoke({})
        except AttributeError:
            # Fallback: call directly if .invoke is not available
            result = tool_func()
        return f"✓ Successfully executed sandbox tool '{tool_name}':\n{result}"

    except Exception as e:
        return f"Error loading sandbox tool: {e}"


# Export all tools for dynamic loading
FILE_TOOLS = [
    list_sandbox_files,
    create_text_file,
    update_text_file,
    read_text_file,
    scan_sandbox_files,
    create_tool,
    list_sandbox_tools,
    load_sandbox_tool,
]
