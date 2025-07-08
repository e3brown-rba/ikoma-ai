# Issue Examples for Phase 1B

## Issue 1: Telemetry Capture Errors

**Title**: `[BUG] Telemetry capture errors during agent startup`

**Template**: Bug Report

**Labels**: `bug`, `low`, `agent`, `needs-triage`

**Description**:
```
Failed to send telemetry event ClientStartEvent: capture() takes 1 positional argument but 3 were given
```

**Steps to Reproduce**:
1. Start iKOMA agent: `python run_agent.py`
2. Observe telemetry errors in console output

**Expected Behavior**: No telemetry errors during startup

**Actual Behavior**: Multiple telemetry capture errors appear

**Environment**:
- Platform: macOS
- Python Version: 3.11.13
- iKOMA Version: Phase 1B
- LM Studio Version: Latest

**Impact**: Low - doesn't affect functionality but creates noise in logs

---

## Issue 2: File Operation Confirmation UX

**Title**: `[ENHANCEMENT] Improve file operation confirmation UX`

**Template**: Enhancement Request

**Labels**: `enhancement`, `medium`, `ui/ux`, `needs-triage`

**Description**:
The current confirmation system for file operations is repetitive and interrupts the user flow.

**Problem Statement**:
When the agent attempts file operations, it shows multiple confirmation prompts that can be confusing and interrupt the conversation flow.

**Proposed Solution**:
1. Implement a single confirmation per operation
2. Add option to disable confirmations for safe operations
3. Provide clearer messaging about what will be created/modified

**Impact**:
- User Experience: High - improves conversation flow
- Performance: Low - minimal impact
- Maintainability: Medium - requires UX improvements

**Platform Support**: All

---

## Issue 3: macOS Setup Requirements

**Title**: `[PLATFORM] macOS setup requires Homebrew and Python 3.10+`

**Template**: Platform Issue

**Labels**: `platform`, `platform:macos`, `setup`, `needs-triage`

**Description**:
macOS setup requires additional steps not documented in the main setup process.

**Platform Information**:
- Platform: macOS
- OS Version: 26.0
- Architecture: ARM64
- Python Version: 3.9.6 (system default)
- Package Manager: Homebrew

**Steps to Reproduce**:
1. Clone repository on macOS
2. Follow main setup instructions
3. Encounter Python version requirement issues

**Expected Behavior**: Setup works with system Python

**Actual Behavior**: Requires Homebrew and Python 3.10+ installation

**Comparison with Other Platforms**: Windows setup doesn't require package manager installation

**Impact Assessment**:
- Severity: Medium
- Affects Main Branch: No (macOS-specific)
- Affects Development: Yes
- User Impact: Medium

---

## Issue 4: Module Import Path Issues

**Title**: `[BUG] Module import error with tools package on macOS`

**Template**: Bug Report

**Labels**: `bug`, `medium`, `tools`, `platform:macos`, `needs-triage`

**Description**:
The agent fails to import the tools module due to Python path configuration issues.

**Steps to Reproduce**:
1. Set up iKOMA on macOS
2. Run `python run_agent.py`
3. Observe ModuleNotFoundError for tools package

**Expected Behavior**: Agent starts without import errors

**Actual Behavior**: ModuleNotFoundError: No module named 'tools'

**Environment**:
- Platform: macOS
- Python Version: 3.11.13
- Virtual Environment: Active

**Workarounds**: 
- Set PYTHONPATH environment variable
- Modify run_agent.py to include project root in path

**Impact**: Medium - prevents agent from starting

---

## Issue 5: Virtual Environment Path Mismatch

**Title**: `[BUG] run_agent.py uses incorrect virtual environment path`

**Template**: Bug Report

**Labels**: `bug`, `medium`, `setup`, `needs-triage`

**Description**:
The run_agent.py script looks for virtual environment in wrong location.

**Steps to Reproduce**:
1. Create virtual environment with `python -m venv venv`
2. Run `python run_agent.py`
3. Script fails to find virtual environment

**Expected Behavior**: Script finds venv in project root

**Actual Behavior**: Script looks for venv in `ikoma/.venv`

**Environment**:
- Platform: macOS
- Python Version: 3.11.13

**Impact**: Medium - prevents agent from running

---

## Issue 6: Memory Artifacts in Git

**Title**: `[ENHANCEMENT] Exclude memory artifacts from version control`

**Template**: Enhancement Request

**Labels**: `enhancement`, `low`, `memory`, `needs-triage`

**Description**:
Memory and database files are being tracked in git, creating unnecessary diffs.

**Problem Statement**:
Local memory files (chroma.sqlite3, vector store data) are being committed to git, making the repository dirty.

**Proposed Solution**:
Update .gitignore to exclude:
- `agent/memory/vector_store/*/`
- `agent/memory/*.sqlite3`
- `agent/memory/vector_store/*.sqlite3`

**Impact**:
- User Experience: Low
- Performance: Low
- Maintainability: Medium - cleaner repository

**Platform Support**: All 