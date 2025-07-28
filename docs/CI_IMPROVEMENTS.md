# CI Improvements for Hanging Prevention

## Overview

This document outlines the improvements made to the CI workflow to prevent hanging issues that were occurring after test completion. The main culprits were identified as:

1. **ChromaDB persistence**: Tests were using ChromaDB with persistent storage, leaving database connections open
2. **Thread cleanup**: TUI and dashboard components using threading that wasn't being properly cleaned up
3. **Subprocess hanging**: Some tests creating subprocesses that weren't being properly terminated

## Changes Made

### 1. Test Environment Isolation (`tests/conftest.py`)

Created a new `conftest.py` file with pytest fixtures to ensure proper test isolation:

- **`cleanup_environment` fixture**: Creates temporary directories for test isolation and sets appropriate environment variables
- **`disable_background_threads` fixture**: Disables TUI and metrics collection in tests
- **Automatic cleanup**: Forces ChromaDB connection cleanup and removes temporary files after each test

### 2. Vector Store Cleanup (`tools/vector_store.py`)

Added a `cleanup_vector_store()` function that:

- Closes ChromaDB client connections properly
- Resets the global vector store instance
- Forces cleanup of ChromaDB global instances
- Handles exceptions gracefully during cleanup

### 3. Signal Handlers (`agent/agent.py`)

Added graceful shutdown handling:

- **Signal handler function**: `signal_handler()` that cleans up resources before exit
- **Signal registration**: Registers handlers for SIGINT and SIGTERM in the main function
- **Vector store cleanup**: Calls the cleanup function when shutdown signals are received

### 4. CI Workflow Timeouts (`.github/workflows/ci.yml`)

Added timeout limits to all CI jobs to prevent indefinite hanging:

- **Lint job**: 10-minute timeout
- **Typecheck job**: 10-minute timeout  
- **Test job**: 15-minute timeout (longer due to ChromaDB operations)
- **Security job**: 10-minute timeout
- **Build job**: 10-minute timeout

### 5. Test Coverage (`tests/test_ci_cleanup.py`)

Created comprehensive tests to verify cleanup functionality:

- **Vector store cleanup test**: Verifies that ChromaDB connections are properly closed
- **Global instance cleanup test**: Ensures ChromaDB global instances are cleared
- **Environment isolation test**: Verifies test environment variables are properly isolated
- **Signal handler test**: Smoke test to ensure signal handlers are properly defined

## Environment Variables for Testing

The following environment variables are automatically set during tests:

```bash
VECTOR_STORE_PATH=/tmp/test_vector_store
CONVERSATION_DB_PATH=/tmp/test_conversations.sqlite
CHROMA_TELEMETRY=false
IKOMA_TUI_MODE=false
IKOMA_METRICS_ENABLED=false
```

## Benefits

1. **Prevents CI hanging**: Tests now properly clean up resources and exit cleanly
2. **Improved test isolation**: Each test runs in its own temporary environment
3. **Better resource management**: ChromaDB connections are properly closed
4. **Graceful shutdown**: Agent can handle shutdown signals properly
5. **Timeout protection**: CI jobs will fail fast if they hang instead of running indefinitely

## Testing the Changes

To verify the improvements work:

```bash
# Run the cleanup tests
pytest tests/test_ci_cleanup.py -v

# Run existing tests to ensure they still work
pytest tests/test_agent_citations.py -v
pytest tests/test_persistence_vector_store.py -v

# Run a broader test suite
pytest tests/ -m "not dashboard" --cov
```

## Troubleshooting

If tests still hang after these changes:

1. **Check ChromaDB connections**: Look for any remaining ChromaDB client instances
2. **Verify signal handlers**: Ensure signal handlers are being called properly
3. **Check thread cleanup**: Look for any daemon threads that might be preventing shutdown
4. **Review timeout settings**: Adjust timeouts if tests legitimately need more time

## Future Improvements

1. **Enhanced monitoring**: Add more detailed logging during cleanup operations
2. **Resource tracking**: Implement resource tracking to identify what's preventing cleanup
3. **Automated cleanup**: Add more aggressive cleanup for edge cases
4. **Performance optimization**: Optimize cleanup operations for faster test execution 