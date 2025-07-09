#!/usr/bin/env python3
r"""iKOMA utility — bulk‑create GitHub issues from a YAML/JSON manifest.

Features
========
* **Owner / thinker labels** are applied automatically.
* `--dry-run` prints `gh issue create …` commands instead of executing.
* Respects `GITHUB_TOKEN` and `GITHUB_REPO` env vars.
* Works from any repo clone — auto‑detects the current remote if `GITHUB_REPO` absent.
* Lightweight: only runtime dependency is PyYAML (declared in dev extras).

Usage
-----
```bash
# Print commands only ➜ useful for audit / piping to a bash file
python scripts/bulk_create_phase2.py --dry-run > bulk_cmds.sh

# Live create against the current repo remote\python scripts/bulk_create_phase2.py

# Live create against a fork (no need to `cd`)
GITHUB_REPO=myuser/ikoma-fork python scripts/bulk_create_phase2.py
```

Manifest format (`issues/phase2.yml`)
------------------------------------
```yaml
- title: Spike — integrate SerpAPI search tool
  body: |
    - Install SerpAPI client
    - Prototype `search_web(query)` returning top‑5 JSON
    - Demo prints titles & URLs
  labels: [epic:E-01, internet, owner:ca-auto, thinker:ca-sonnet4]
```

The script exits with non‑zero status if the manifest is missing or malformed so it can be gated in CI.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import subprocess
import sys
import textwrap
from typing import Any

try:
    import yaml  # Provided via dev‑extra in requirements.txt
except ModuleNotFoundError:
    sys.stderr.write(
        "PyYAML missing – run `pip install pyyaml` or install dev extras.\n"
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# CLI setup
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser(description="Bulk‑create GitHub issues from manifest")
parser.add_argument(
    "--manifest",
    "-m",
    type=pathlib.Path,
    default=pathlib.Path("issues/phase2.yml"),
    help="Path to YAML or JSON issue manifest (default: issues/phase2.yml)",
)
parser.add_argument(
    "--dry-run", action="store_true", help="Print gh commands instead of executing"
)
args = parser.parse_args()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def detect_repo() -> str:
    """Return <owner>/<name> of the current repo using gh CLI."""
    env_repo = os.getenv("GITHUB_REPO")
    if env_repo:
        return env_repo
    try:
        return subprocess.check_output(
            ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
            text=True,
        ).strip()
    except subprocess.CalledProcessError as e:
        sys.stderr.write(
            "Error: could not determine repository. Set $GITHUB_REPO or run inside a repo clone.\n"
        )
        sys.exit(e.returncode)


def read_manifest(path: pathlib.Path) -> list[dict[str, Any]]:
    if not path.exists():
        sys.stderr.write(f"Manifest file {path} not found.\n")
        sys.exit(1)

    if path.suffix in {".yaml", ".yml"}:
        data = yaml.safe_load(path.read_text())
    elif path.suffix == ".json":
        import json

        data = json.loads(path.read_text())
    else:
        sys.stderr.write("Manifest must be .yml, .yaml or .json\n")
        sys.exit(1)

    if not isinstance(data, list):
        sys.stderr.write("Manifest root must be a list of issues.\n")
        sys.exit(1)
    return data


def gh(cmd: list[str]):
    if args.dry_run:
        print("gh", " ".join(cmd))
    else:
        subprocess.run(["gh"] + cmd, check=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    repo = detect_repo()
    issues = read_manifest(args.manifest)

    for item in issues:
        title = item.get("title")
        if not title:
            sys.stderr.write("Skipping issue without title.\n")
            continue
        body = textwrap.dedent(item.get("body", "")).strip()
        labels = item.get("labels", [])
        cmd = [
            "issue",
            "create",
            "--repo",
            repo,
            "--title",
            title,
            "--label",
            ",".join(labels),
            "--body",
            body or "(no description)",
        ]
        gh(cmd)

    print("✅  Done – issues processed.")


if __name__ == "__main__":
    main()
