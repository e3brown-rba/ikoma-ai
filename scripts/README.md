# iKOMA Utilities & Workflow Guide

> **Scope** – This README replaces the previous *scripts* README and folds in the Phase‑2 operating rules, label conventions and the new one‑stop **bulk issue creator**. If you already cloned the repo simply `git pull` to get this file.

---

## 1 Resource Model

| Tag                                   | Capability                     | Pushes Code?                   |
| ------------------------------------- | ------------------------------ | ------------------------------ |
| **owner**\*\*:ca-auto\*\*             | Cursor Auto Worker (local IDE) | **Yes** – the *only* committer |
| **thinker**\*\*:ca-sonnet4\*\*        | Cursor Sonnet‑4 (reasoning)    | No                             |
| **thinker**\*\*:ca-o3\*\*             | Cursor o3 (planner)            | No                             |
| **thinker**\*\*:claude-opus\*\*       | Claude Opus (safety/metrics)   | No                             |
| **thinker**\*\*:gpt-o3\*\*            | ChatGPT o3 (brainstorm)        | No                             |
| **thinker**\*\*:claude-sonnet-web\*\* | Claude Sonnet web (UX copy)    | No                             |

*We use ****labels**** – not GitHub accounts – to track who thinks vs. who codes.*

---

## 2 Label Conventions

```text
# Epic buckets
  epic:E-01 .. epic:E-06
# Functional tags
  internet, parsing, safety, memory, autonomy, planning, ux, backend, frontend,
  devops, metrics, security, docs, qa, carryover
# Resourcing tags
  owner:ca-auto           # single pusher
  thinker:<agent>         # advisory model
```

Create the labels once (Settings ▸ Labels) or run `scripts/create_labels.sh`.

---

## 3 Bulk Issue Creator

`scripts/bulk_create_phase2.py` migrates the earlier Bash script into a **parameterised Python CLI** that:

- reads an **issue manifest** (YAML or JSON) – default `issues/phase2.yml`
- adds `owner:` / `thinker:` labels automatically
- supports dry‑run and multi‑repo modes

### 3.1 Install deps (one‑off)

```bash
pip install -r requirements.txt   # installs PyYAML & GitPython via dev extra
```

### 3.2 Usage

```bash
# dry‑run – prints gh commands only
python scripts/bulk_create_phase2.py --dry-run  
# tip: pipe to a file if you want a standalone bash script
python scripts/bulk_create_phase2.py --dry-run > bulk_gh_commands.sh

# live create against current repo\python scripts/bulk_create_phase2.py

# create against a fork
GITHUB_REPO=me/ikoma-fork python scripts/bulk_create_phase2.py
```

*The script requires **``** if set.*

#### 3.3 Issue manifest example (`issues/phase2.yml`)

```yaml
- title: Spike — integrate SerpAPI search tool
  body: |
    - Install SerpAPI client
    - Prototype `search_web(query)` returning top‑5 JSON
    - Demo prints titles & URLs
  labels: [epic:E-01, internet, owner:ca-auto, thinker:ca-sonnet4]

- title: SQLite conversation state backend
  body: |
    - `checkpointer.py` save/load
    - Schema: run_id, step, tool_calls, memory
  labels: [epic:E-03, memory, owner:ca-auto, thinker:ca-o3]
```

---

## 4 Phase‑2 Operating Manual (TL;DR)

The full manual lives in \`\` (also visible in the canvas). Key points:

1. **Pick a ticket** → consult its `thinker:` label in Cursor.
2. Code & commit on a branch – you push as *your* Git account.
3. Open PR; CI must be green; merge closes issue.

---

## 5 Script Source

```python
#!/usr/bin/env python3
"""Bulk‑create Phase‑2 issues with owner / thinker labels.
   Usage: python scripts/bulk_create_phase2.py [--dry-run]
"""
from __future__ import annotations
import os, sys, json, subprocess, textwrap, pathlib, argparse
from typing import List, Dict, Any
try:
    import yaml  # PyYAML (dev extra)
except ImportError:
    print("PyYAML missing – run `pip install pyyaml` or install dev extras")
    sys.exit(1)

REPO = os.getenv("GITHUB_REPO", subprocess.check_output(["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"]).decode().strip())
MANIFEST_PATH = pathlib.Path("issues/phase2.yml")

parser = argparse.ArgumentParser(description="Create GitHub issues from manifest")
parser.add_argument("--dry-run", action="store_true", help="Print gh commands instead of executing")
args = parser.parse_args()

def read_manifest(path: pathlib.Path) -> List[Dict[str, Any]]:
    if not path.exists():
        sys.exit(f"Manifest file {path} not found")
    with path.open() as f:
        data = yaml.safe_load(f)
    if not isinstance(data, list):
        sys.exit("Manifest must be a YAML list of issues")
    return data

def gh(cmd: List[str]):
    if args.dry_run:
        print("gh", " ".join(cmd))
    else:
        subprocess.run(["gh"] + cmd, check=True)

def main():
    issues = read_manifest(MANIFEST_PATH)
    for item in issues:
        title = item["title"]
        body  = textwrap.dedent(item.get("body", "")).strip()
        labels = item.get("labels", [])
        cmd = [
            "issue", "create",
            "--repo", REPO,
            "--title", title,
            "--label", ",".join(labels),
            "--body", body or "(no description)"
        ]
        gh(cmd)
    print("✅  Done – issues processed.")

if __name__ == "__main__":
    main()
```

### Why switch to Python?

- Safer quoting than Bash for multi‑line bodies.
- Dry‑run flag shows exactly what will be executed.
- Easier to extend (e.g. multi‑repo, milestones, assignees).

---