import os
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
SANDBOX = Path(os.getenv("SANDBOX_PATH", "agent/ikoma_sandbox")).expanduser()


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


# Export all tools for dynamic loading
FILE_TOOLS = [list_sandbox_files, create_text_file, update_text_file, read_text_file]
