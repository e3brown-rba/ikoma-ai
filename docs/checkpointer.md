# SQLite Conversation State Backend

Ikoma uses SQLite to persist conversation state, allowing the agent to survive crashes or manual restarts and resume exactly where it stopped.

## Overview

The checkpointer system provides:
- **Short-term memory**: Persists every plan/execute/reflect cycle
- **Crash recovery**: Agent can resume from the last saved state
- **Thread safety**: WAL mode enables safe concurrent access
- **Configurable**: Can be disabled for testing or CI environments

## Quick Start

### Basic Usage

The checkpointer is enabled by default. No additional configuration is required:

```bash
# Run agent with checkpointer enabled (default)
python run_agent.py

# Run with checkpointer disabled
python run_agent.py --no-checkpoint
```

## Configuration

### Environment Variables

Configure the checkpointer via environment variables:

```bash
# Enable/disable checkpointer (recommended)
export CHECKPOINTER_ENABLED=true

# Legacy variable (deprecated - will be removed in Phase 3)
export IKOMA_DISABLE_CHECKPOINTER=false

# Custom database path
export CONVERSATION_DB_PATH=/path/to/conversations.sqlite

# Run agent
python run_agent.py
```

### Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `CHECKPOINTER_ENABLED` | `true` | Enable/disable conversation persistence |
| `IKOMA_DISABLE_CHECKPOINTER` | `false` | Legacy disable flag (deprecated) |
| `CONVERSATION_DB_PATH` | `agent/memory/conversations.sqlite` | Database file path |

### Evaluation Order

The checkpointer follows this precedence order:

1. **CLI Flag**: `--no-checkpoint` (highest priority)
2. **Legacy Variable**: `IKOMA_DISABLE_CHECKPOINTER` (any truthy value disables)
3. **New Variable**: `CHECKPOINTER_ENABLED` (defaults to `true`)

**Note**: The legacy `IKOMA_DISABLE_CHECKPOINTER` variable will be removed in Phase 3. Use `CHECKPOINTER_ENABLED=false` instead.

### Future Environment Variables

The following variables are planned for future releases:

| Variable | Default | Description |
|----------|---------|-------------|
| `IKOMA_CHECKPOINT_COMPRESSION` | `false` | Enable compression for large payloads |
| `IKOMA_CHECKPOINT_CLEANUP_DAYS` | `30` | Auto-cleanup old checkpoints |
| `IKOMA_CHECKPOINT_ENCRYPTION` | `false` | Enable encryption for sensitive data |

## Database Schema

The checkpointer uses a single table with the following schema:

```sql
CREATE TABLE conversation_steps (
    run_id TEXT NOT NULL,
    step INTEGER NOT NULL,
    tool_calls JSON NOT NULL,
    ts DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (run_id, step)
);
```

### Schema Details

- **`run_id`**: Unique identifier for each conversation session
- **`step`**: Sequential step number within the conversation
- **`tool_calls`**: JSON-serialized tool call data
- **`ts`**: Timestamp when the step was recorded

## CLI Management

Ikoma provides a command-line interface for managing checkpoints:

### List Checkpoint Runs

```bash
# List all runs (default limit: 50)
ikoma checkpoint list

# List with custom limit
ikoma checkpoint list --limit 100
```

### Show Run Details

```bash
# Show basic run information
ikoma checkpoint show <run_id>

# Show detailed step information
ikoma checkpoint show <run_id> --steps
```

### Remove Runs

```bash
# Remove a specific run (with confirmation)
ikoma checkpoint rm <run_id>

# Remove without confirmation
ikoma checkpoint rm <run_id> --force
```

### Clear All Runs

```bash
# Clear all runs (with confirmation)
ikoma checkpoint clear-all

# Clear all runs without confirmation
ikoma checkpoint clear-all --force
```

## Manual Database Management

### Reset Database

To clear all conversation state:

```bash
# Remove the database file
rm agent/memory/conversations.sqlite

# Or use SQLite directly
sqlite3 agent/memory/conversations.sqlite "DELETE FROM conversation_steps;"
```

### Inspect Database

View stored conversation data:

```bash
# List all runs
sqlite3 agent/memory/conversations.sqlite "SELECT DISTINCT run_id FROM conversation_steps;"

# View steps for a specific run
sqlite3 agent/memory/conversations.sqlite "SELECT step, tool_calls FROM conversation_steps WHERE run_id = 'your-run-id';"

# Count total steps
sqlite3 agent/memory/conversations.sqlite "SELECT COUNT(*) FROM conversation_steps;"
```

### Database Location

The default database location is:
- **Path**: `agent/memory/conversations.sqlite`
- **Permissions**: Read/write for the user running Ikoma
- **Backup**: Consider backing up this file for important conversations

## Troubleshooting

### Common Issues

#### Database Locked
```
sqlite3.OperationalError: database is locked
```

**Solution**: The database uses WAL mode for concurrent access. If you encounter locks:
1. Ensure only one Ikoma instance is running
2. Check for other processes accessing the database
3. Restart Ikoma if necessary

#### Permission Denied
```
sqlite3.OperationalError: unable to open database file
```

**Solution**: Check file permissions:
```bash
# Ensure write permissions
chmod 644 agent/memory/conversations.sqlite
chmod 755 agent/memory/
```

#### Corrupted Database
```
sqlite3.DatabaseError: database disk image is malformed
```

**Solution**: Reset the database:
```bash
# Backup corrupted database
mv agent/memory/conversations.sqlite agent/memory/conversations.sqlite.bak

# Restart Ikoma (will create new database)
python run_agent.py
```

### Performance Considerations

- **Large payloads**: Tool calls are stored as JSON. Consider compression for >1MB payloads
- **Database size**: Monitor database growth with `du -h agent/memory/conversations.sqlite`
- **Concurrent access**: WAL mode allows multiple readers, but only one writer

## Development

### Testing

Run the checkpointer tests:

```bash
# Run all checkpointer tests
pytest tests/test_checkpointer.py -v

# Run with coverage
pytest tests/test_checkpointer.py --cov=agent.checkpointer
```

### Disabling in CI

To disable checkpointer in CI environments:

```yaml
# .github/workflows/test.yml
env:
  IKOMA_DISABLE_CHECKPOINTER: true
```

### Integration

The checkpointer integrates with LangGraph's checkpoint system:

```python
from agent.checkpointer import IkomaCheckpointer

# Create checkpointer
checkpointer = IkomaCheckpointer("path/to/db.sqlite")

# Compile workflow with checkpointer
app = workflow.compile(checkpointer=checkpointer)
```

## Architecture

The checkpointer system consists of multiple layers:

### Service Layer
- **`CheckpointRecord`**: Pydantic model for type-safe checkpoint data
- **`CheckpointerService`**: CRUD operations with thread-safe singleton pattern
- **`SQLiteCRUDMixin`**: Low-level SQLite operations with proper parameterization

### LangGraph Integration
- **`IkomaMemoryManager`**: Implements LangGraph's `BaseCheckpointSaver` interface
- **`IkomaCheckpointer`**: Legacy interface for backward compatibility

### Data Flow

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Agent State   │───▶│ IkomaMemoryManager │───▶│ CheckpointerService │───▶│  SQLite DB     │
│                 │    │                  │    │                  │    │                 │
│ • Messages      │    │ • LangGraph API  │    │ • CRUD Ops      │    │ • conversation_ │
│ • Tool Calls    │    │ • State Mapping  │    │ • Thread Safe   │    │   steps table   │
│ • Context       │    │ • Error Handling │    │ • Singleton     │    │ • Indexed       │
└─────────────────┘    └──────────────────┘    └─────────────────┘    └─────────────────┘
```

### Data Flow

1. **Plan**: Agent creates execution plan
2. **Execute**: Tools are called and results stored
3. **Reflect**: Agent analyzes results and updates state
4. **Persist**: State is saved to SQLite via checkpointer
5. **Resume**: On restart, agent loads last saved state

## Future Enhancements

- **Compression**: Automatic compression for large payloads
- **Cleanup**: Automatic cleanup of old conversation data
- **Migration**: Schema versioning and migration support
- **Encryption**: Optional encryption for sensitive conversations 