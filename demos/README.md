# Ikoma Demos

This folder contains demo scripts for showcasing Ikoma's features and TUI interface.

## EV Tax Credits Demo

- **Script:** `demo_script.py`
- **Scenario:**
  > Track the latest policy proposals on U.S. federal EV tax credits, summarise the changes since 2023, list three credible sources, store the summary to long‑term memory, and add a weekly watch-task that pings me if legislation status changes.

### How to Run

From the project root:

```bash
python demos/demo_script.py
```

Or, equivalently:

```bash
python -m agent.agent --demo
```

This will:
- Pre-load the EV tax credits scenario as the agent's goal
- Enable the TUI for real-time monitoring
- Run in continuous mode with auto-continue
- Show plan, execution, and reflection updates in the TUI

You can record the session with [asciinema](https://asciinema.org/):

```bash
asciinema rec demo_track_v0.cast
python demos/demo_script.py
```

Press Ctrl+C to stop the demo. 