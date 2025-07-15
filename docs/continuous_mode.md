# Continuous Mode

Ikoma's continuous mode allows the AI assistant to run autonomously, pursuing a high-level goal through multiple plan-execute-reflect cycles without human intervention.

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
- **Time Limit**: Maximum 10 minutes by default (configurable)
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
| `--time-limit` | integer | 10 | Time limit in minutes |

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
3. **Safety Monitoring**: Each iteration checks against time and iteration limits
4. **Automatic Termination**: Stops when goal is achieved or limits are reached

## Exit Codes

- `0`: Successful completion
- `1`: User interruption (Ctrl-C) or error
- `2`: Invalid arguments (e.g., missing `--goal` with `--continuous`)

## Best Practices

### Goal Formulation
- **Be Specific**: "Create a REST API with authentication" vs "make an app"
- **Include Constraints**: "Research Python frameworks suitable for small teams"
- **Set Scope**: "Analyze the first 100 lines of code" vs "analyze everything"

### Safety Considerations
- **Start Small**: Use lower iteration/time limits for new goals
- **Monitor Progress**: Check intermediate results in the sandbox
- **Test Goals**: Verify goal clarity before long-running sessions

### Resource Management
- **LM Studio**: Ensure your local LLM server is stable
- **Disk Space**: Monitor sandbox directory growth
- **Memory**: Large tasks may consume significant resources

## Troubleshooting

### Common Issues

**Goal too vague**
```
Error: Agent keeps planning without progress
Solution: Make goals more specific and measurable
```

**Time limit too short**
```
Error: Task incomplete when time limit reached
Solution: Increase --time-limit or break into smaller goals
```

**Iteration limit too low**
```
Error: Complex task needs more planning cycles
Solution: Increase --max-iterations for complex goals
```

### Debug Mode
For development and debugging, you can run with verbose output:
```bash
python agent/agent.py --continuous --goal "test goal" --max-iterations 2
```

## Integration with Existing Features

### Memory Persistence
Continuous mode sessions are stored in the same memory system as interactive sessions, allowing for:
- Context preservation across runs
- Citation tracking and management
- Long-term learning from autonomous sessions

### Tool Access
Continuous mode has access to all available tools:
- File operations in the sandbox
- Web search and extraction
- Mathematical calculations
- Content creation and analysis

### Safety Sanitization
All web content and user inputs are sanitized according to the existing security policies, ensuring safe autonomous operation.

## Future Enhancements

Planned improvements for continuous mode:
- **Dynamic Limits**: Adaptive iteration/time limits based on task complexity
- **Human Checkpoints**: Periodic prompts for user approval
- **Goal Satisfaction**: Automatic detection of goal completion
- **Progress Tracking**: Real-time progress indicators and metrics 