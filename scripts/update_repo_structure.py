#!/usr/bin/env python3
"""
Update repo_structure.jsonl to reflect current repository state
"""

import os
import json
from pathlib import Path
from datetime import datetime


def get_file_info(file_path):
    """Get file information for repo structure entry"""
    stat = file_path.stat()
    return {
        "size_kb": round(stat.st_size / 1024, 1),
        "lines": len(file_path.read_text().splitlines()) if file_path.is_file() else 0,
    }


def update_repo_structure():
    """Update the repo_structure.jsonl file with current repository state"""

    # Read existing structure
    repo_structure_file = Path("repo_structure.jsonl")
    if repo_structure_file.exists():
        with open(repo_structure_file, "r") as f:
            existing_entries = [json.loads(line) for line in f if line.strip()]
    else:
        existing_entries = []

    # Create a map of existing entries by path
    existing_map = {}
    for entry in existing_entries:
        if "path" in entry:
            existing_map[entry["path"]] = entry

    # Update the scripts folder entry
    scripts_dir = Path("scripts")
    if scripts_dir.exists():
        script_files = list(scripts_dir.glob("*.py")) + list(scripts_dir.glob("*.md"))
        script_contents = [f.name for f in script_files]

        # Update scripts directory entry
        scripts_entry = {
            "type": "scripts_directory",
            "path": "scripts/",
            "purpose": "utility_scripts",
            "status": "active",
            "description": "Collection of utility scripts for project management and automation",
            "contents": script_contents,
            "last_updated": "current_structure_update",
        }

        # Update individual script files
        for script_file in script_files:
            file_info = get_file_info(script_file)

            if script_file.name == "bulk_create_phase2.py":
                script_entry = {
                    "type": "script_file",
                    "path": f"scripts/{script_file.name}",
                    "purpose": "phase_2_preparation",
                    "language": "python",
                    "lines": file_info["lines"],
                    "size_kb": file_info["size_kb"],
                    "status": "active",
                    "description": "Script for bulk creation of Phase 2 components and data structures",
                    "features": [
                        "automated_setup",
                        "data_generation",
                        "phase_2_preparation",
                    ],
                    "last_updated": "current_structure_update",
                }
            elif script_file.name == "README.md":
                script_entry = {
                    "type": "documentation_file",
                    "path": f"scripts/{script_file.name}",
                    "purpose": "scripts_documentation",
                    "language": "markdown",
                    "lines": file_info["lines"],
                    "size_kb": file_info["size_kb"],
                    "status": "active",
                    "description": "Documentation for utility scripts and their usage",
                    "sections": [
                        "script_overview",
                        "usage_instructions",
                        "phase_2_preparation",
                    ],
                    "last_updated": "current_structure_update",
                }
            else:
                # Generic script entry
                script_entry = {
                    "type": "script_file",
                    "path": f"scripts/{script_file.name}",
                    "purpose": "utility_script",
                    "language": "python" if script_file.suffix == ".py" else "markdown",
                    "lines": file_info["lines"],
                    "size_kb": file_info["size_kb"],
                    "status": "active",
                    "description": f"Utility script: {script_file.name}",
                    "last_updated": "current_structure_update",
                }

            existing_map[f"scripts/{script_file.name}"] = script_entry

        existing_map["scripts/"] = scripts_entry

    # Add a current structure update entry
    def count_lines_safe(file_path):
        """Safely count lines in a file, handling binary files"""
        try:
            return len(
                file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
            )
        except:
            return 0

    current_structure_entry = {
        "type": "current_structure",
        "total_files": len(list(Path(".").rglob("*"))),
        "total_lines": sum(
            count_lines_safe(f) for f in Path(".").rglob("*.py") if f.is_file()
        ),
        "python_files": len(list(Path(".").rglob("*.py"))),
        "markdown_files": len(list(Path(".").rglob("*.md"))),
        "config_files": len(list(Path(".").rglob("*.{yaml,yml,toml,json,txt}"))),
        "data_files": len(list(Path(".").rglob("*.{sqlite3,txt}"))),
        "system_files": len(list(Path(".").rglob("*.{DS_Store,ini}"))),
        "directories": len([d for d in Path(".").iterdir() if d.is_dir()]),
        "last_updated": datetime.now().strftime("%Y-%m-%d"),
        "structure_version": "2.1",
        "phase": "1B_complete",
        "next_phase": "phase_2_preparation",
        "update_note": "scripts_folder_renamed",
    }

    # Write updated structure
    with open(repo_structure_file, "w") as f:
        for entry in existing_entries:
            if (
                entry.get("type") != "current_structure"
            ):  # Skip old current_structure entries
                f.write(json.dumps(entry) + "\n")

        # Write updated entries
        for path, entry in existing_map.items():
            if path.startswith("scripts/"):
                f.write(json.dumps(entry) + "\n")

        # Write new current structure entry
        f.write(json.dumps(current_structure_entry) + "\n")

    print(f"Updated {repo_structure_file} with current repository structure")
    print(f"Scripts folder contents: {script_contents}")


if __name__ == "__main__":
    update_repo_structure()
