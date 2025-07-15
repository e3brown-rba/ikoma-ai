# Continuous Mode

Ikoma's continuous mode allows the AI assistant to run autonomously, pursuing a high-level goal through multiple plan-execute-reflect cycles without human intervention.

---

**New in v0.3.1:**
- Continuous mode now enforces both an **iteration limit** and a **wall-clock time limit** using a unified, extensible criteria engine.
- The time limit is configurable via the `IKOMA_MAX_MINS` environment variable or the `--time-limit` CLI flag.

---

## Quick Start

```bash
# Basic continuous mode with default limits
python agent/agent.py --continuous --goal "Research and summarize the latest Python best practices"

# Custom iteration and time limits
python agent/agent.py --continuous --goal "Create a project plan for a web application" --max-iterations 10 --time-limit 15
```

## Safety Features

### Hard Limits
- **Iteration Cap**: Maximum 25 iterations by default (configurable)
- **Time Limit**: Maximum 10 minutes by default (configurable via `IKOMA_MAX_MINS` or `--time-limit`)
- **Unified Criteria Engine**: Both limits are checked together at each cycle for robust safety
- **Kill Switch**: Press `Ctrl-C` to abort at any time

### Safety Banner
When continuous mode is activated, Ikoma displays a clear warning banner:

```
┌─ Ikoma Autonomy ──────────────────────────────────────────────────────────────┐
│ ⚠  Continuous mode activated                                                  │
│ Ikoma will pursue the goal:                                                  │
│                                                                               │
│ Research and summarize the latest Python best practices                       │
│                                                                               │
│ Max iterations: 25 · Time limit: 10 min                                      │
│ Press Ctrl-C to abort at any time.                                           │
└───────────────────────────────────────────────────────────────────────────────┘
```

## Command Line Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--continuous` | flag | - | Enable continuous mode |
| `--goal` | string | required | High-level goal to pursue |
| `--max-iterations` | integer | 25 | Maximum iteration count |
| `--time-limit` | integer | 10 | Time limit in minutes (overrides `IKOMA_MAX_MINS`) |

## Examples

### Research Task
```bash
python agent/agent.py --continuous --goal "Research machine learning frameworks for beginners and create a comparison document"
```

### Development Task
```bash
python agent/agent.py --continuous --goal "Set up a Python project structure with testing, linting, and documentation" --max-iterations 15
```

### Analysis Task
```bash
python agent/agent.py --continuous --goal "Analyze the codebase and identify potential improvements" --time-limit 20
```

## How It Works

1. **Goal Setting**: The `--goal` parameter becomes the initial user message
2. **Autonomous Execution**: Ikoma runs through plan-execute-reflect cycles
3. **Safety Monitoring**: Each iteration checks against both time and iteration limits using a unified criteria engine
4. **Automatic Termination**: Stops when goal is achieved or either limit is reached

---

### Environment Variable
- `IKOMA_MAX_MINS`: Sets the default wall-clock time limit (in minutes) for continuous mode. Can be overridden by `--time-limit`.

---

## Exit Codes

- `0`: Successful completion
- `1`: User interruption (Ctrl-C) or error
- `