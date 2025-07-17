# iKOMA Agent Sandbox Architecture

## Overview

The iKOMA agent operates within a **sandboxed environment** for all file system operations and tool creation. This ensures safety, isolation, and prevents the agent from accidentally modifying the main codebase or system files.

## Sandbox Configuration

### Default Sandbox Location
```python
SANDBOX = Path(os.getenv("SANDBOX_PATH", "agent/ikoma_sandbox")).expanduser()
```

- **Default**: `agent/ikoma_sandbox/`
- **Configurable**: Set `SANDBOX_PATH` environment variable to change location
- **Automatic Creation**: Sandbox directory is created if it doesn't exist

### Sandbox Structure
```
agent/ikoma_sandbox/
├── hello.txt                    # User files
├── who_are_you.txt             # User files
├── tools/                       # Dynamically created tools
│   ├── test_calculator.py      # Agent-created tools
│   └── ...                     # More tools as needed
└── ...                         # Other sandbox content
```

## Sandboxed Tools

### File System Operations
All file operations are **strictly limited to the sandbox**:

1. **`list_sandbox_files()`** - Lists files in sandbox only
2. **`create_text_file()`** - Creates files in sandbox only
3. **`update_text_file()`** - Updates files in sandbox only
4. **`read_text_file()`** - Reads files from sandbox only
5. **`scan_sandbox_files()`** - Scans files in sandbox only

### Tool Creation & Management
6. **`create_tool()`** - Creates new tools in `sandbox/tools/`
7. **`list_sandbox_tools()`** - Lists tools in sandbox
8. **`load_sandbox_tool()`** - Executes sandbox tools

## Security Principles

### 1. Complete Isolation
- **No Access to Main Codebase**: Agent cannot read/write outside sandbox
- **No System File Access**: Cannot access system directories
- **No Repository Access**: Cannot scan or modify main repository files

### 2. Controlled Environment
- **Predictable Behavior**: All file operations are contained
- **Safe Tool Creation**: New tools are created in sandbox
- **Isolated Execution**: Sandbox tools run in controlled environment

### 3. User Confirmation
- **Destructive Operations**: User confirmation required for file overwrites
- **Tool Creation**: Tools are created safely within sandbox
- **Clear Feedback**: All operations provide clear status messages

## Agent Learning Within Sandbox

### Tool Discovery Process
1. **Task Analysis**: Agent analyzes what tools it needs
2. **Tool Creation**: Uses `create_tool()` to build new capabilities
3. **Tool Testing**: Uses `list_sandbox_tools()` and `load_sandbox_tool()`
4. **Task Completion**: Uses created tools to accomplish goals

### Example Learning Flow
```
Task: "Scan for TODO comments and create a report"

1. Agent tries existing tools (list_sandbox_files)
2. Realizes it needs to scan files for patterns
3. Creates new tool: scan_sandbox_files
4. Uses new tool to find TODO comments
5. Creates report using create_text_file
6. Task completed entirely within sandbox
```

## External Tool Categories

### Safe External Operations
The following tools operate outside the sandbox but have their own security measures:

- **Web Tools**: Domain filtering, rate limiting, security validation
- **HTTP Tools**: Rate limiting, domain restrictions, safety checks
- **Internet Tools**: Domain allowlists, content filtering
- **Vector Store**: Memory operations with security validation

### Why External Tools Are Safe
- **No File System Access**: Don't read/write local files
- **Network Security**: Domain filtering and rate limiting
- **Content Validation**: Security checks on all content
- **Controlled APIs**: Only access allowed external services

## Normal Operation vs Demo Mode

### Normal Operation
- **All file operations** happen in sandbox
- **Tool creation** happens in sandbox
- **Learning and adaptation** within sandbox
- **External tools** have security restrictions

### Demo Mode
- **Same sandbox restrictions** apply
- **Additional logging** for debugging
- **TUI monitoring** for real-time visibility
- **Enhanced debugging** capabilities

## Benefits of Sandbox Architecture

### 1. Safety
- **No Accidental Damage**: Cannot modify main codebase
- **Controlled Environment**: Predictable behavior
- **User Protection**: Confirmation for destructive operations

### 2. Learning
- **Safe Experimentation**: Agent can try new approaches
- **Tool Creation**: Can build new capabilities safely
- **Failure Recovery**: Mistakes are contained

### 3. Debugging
- **Clear Boundaries**: Easy to see what agent is doing
- **Isolated State**: Sandbox state is separate from system
- **Reproducible**: Same environment for testing

### 4. Scalability
- **Multiple Instances**: Each agent can have its own sandbox
- **Version Control**: Sandbox can be versioned separately
- **Backup/Restore**: Easy to backup or reset sandbox

## Configuration Options

### Environment Variables
```bash
# Change sandbox location
export SANDBOX_PATH="/path/to/custom/sandbox"

# Run agent with custom sandbox
python run_agent.py --goal "Your task here"
```

### Sandbox Management
```bash
# Clear sandbox (start fresh)
rm -rf agent/ikoma_sandbox/*

# Backup sandbox
cp -r agent/ikoma_sandbox backup_sandbox_$(date +%Y%m%d)

# Restore sandbox
cp -r backup_sandbox_20250116/* agent/ikoma_sandbox/
```

## Best Practices

### 1. Regular Cleanup
- Periodically clear old sandbox content
- Archive important agent-created tools
- Monitor sandbox size and performance

### 2. Tool Management
- Review created tools for quality
- Archive useful tools for reuse
- Clean up experimental tools

### 3. Monitoring
- Use TUI for real-time monitoring
- Check logs for agent behavior
- Monitor sandbox usage patterns

## Conclusion

The sandbox architecture ensures that the iKOMA agent can:
- **Learn safely** without risking system damage
- **Create tools** in a controlled environment
- **Experiment freely** within defined boundaries
- **Scale effectively** with multiple instances
- **Debug easily** with clear isolation

This design enables autonomous AI agents that can extend their capabilities while maintaining safety and reliability. 