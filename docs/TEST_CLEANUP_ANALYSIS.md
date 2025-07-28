# Test Cleanup Analysis and Fixes

## Overview

This document provides a comprehensive analysis of potential resource cleanup issues in the test suite and the fixes applied to prevent CI hanging and resource leaks.

## Issues Identified

### 1. **Temporary File Cleanup Issues**

#### Problem Files:
- `tests/test_domain_filter.py` - Uses `tempfile.mkdtemp()` without proper error handling
- `tests/test_agent_phase1b.py` - Vector store fixture with potential cleanup issues
- `tests/test_metrics_dashboard.py` - Temporary file fixture without cleanup
- `tests/test_tui_demo.py` - Subprocess without timeout

#### Issues:
- Temporary files not properly cleaned up in error cases
- Subprocess calls without timeout protection
- Vector store connections not properly closed

### 2. **ChromaDB Connection Issues**

#### Problem Files:
- `tests/test_agent_phase1b.py` - Creates ChromaDB connections without cleanup
- `tests/test_persistence_vector_store.py` - Uses ChromaDB with persistent storage
- `tests/test_citation_vector_store.py` - ChromaDB citation storage tests

#### Issues:
- ChromaDB connections left open after tests
- Global ChromaDB instances not cleaned up
- Persistent storage directories not properly removed

### 3. **SQLite Database Issues**

#### Problem Files:
- `tests/test_checkpointer_crud.py` - Multiple SQLite database tests
- `tests/test_memory_manager_integration.py` - SQLite integration tests
- `tests/test_checkpointer.py` - Checkpointer SQLite tests

#### Issues:
- SQLite connections not properly closed
- Database files not cleaned up in error cases
- Multiple database instances created without cleanup

### 4. **Subprocess and Thread Issues**

#### Problem Files:
- `tests/test_tui_demo.py` - Subprocess without timeout
- Various tests that might create background threads

#### Issues:
- Subprocess calls without timeout protection
- Daemon threads that might prevent clean shutdown
- Background processes not properly terminated

## Fixes Applied

### 1. **Enhanced conftest.py**

✅ **Added comprehensive test isolation:**
```python
@pytest.fixture(autouse=True)
def cleanup_environment():
    """Ensure clean test environment and proper cleanup."""
    # Store original environment
    original_env = os.environ.copy()
    
    # Create temporary directories for test isolation
    temp_dir = Path(tempfile.mkdtemp())
    test_vector_store = temp_dir / "test_vector_store"
    test_conversations = temp_dir / "test_conversations.sqlite"
    
    # Set test environment variables
    os.environ["VECTOR_STORE_PATH"] = str(test_vector_store)
    os.environ["CONVERSATION_DB_PATH"] = str(test_conversations)
    os.environ["CHROMA_TELEMETRY"] = "false"
    os.environ["IKOMA_TUI_MODE"] = "false"
    
    yield
    
    # Cleanup after test
    try:
        import chromadb
        if hasattr(chromadb, '_client_instance'):
            chromadb._client_instance = None
    except ImportError:
        pass
    
    # Remove temporary files
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)
```

### 2. **Vector Store Cleanup Function**

✅ **Added `cleanup_vector_store()` function:**
```python
def cleanup_vector_store() -> None:
    """Clean up vector store connections and resources."""
    global vector_store
    if vector_store is not None:
        try:
            # Close ChromaDB client connection
            if hasattr(vector_store, 'client'):
                vector_store.client.reset()
            vector_store = None
        except Exception as e:
            print(f"Warning: Error during vector store cleanup: {e}")
    
    # Force close any ChromaDB global instances
    try:
        import chromadb
        if hasattr(chromadb, '_client_instance'):
            chromadb._client_instance = None
    except ImportError:
        pass
```

### 3. **Signal Handlers for Graceful Shutdown**

✅ **Added signal handlers in agent.py:**
```python
def signal_handler(sig: int, frame: Any) -> None:
    """Handle shutdown signals gracefully."""
    print("\n🛑 Received shutdown signal, cleaning up...")
    # Force close ChromaDB connections
    try:
        from tools.vector_store import cleanup_vector_store
        cleanup_vector_store()
    except ImportError:
        pass
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
```

### 4. **CI Workflow Timeouts**

✅ **Added timeout limits to all CI jobs:**
```yaml
lint:
  timeout-minutes: 10
typecheck:
  timeout-minutes: 10
test:
  timeout-minutes: 15  # Longer for ChromaDB operations
security:
  timeout-minutes: 10
build:
  timeout-minutes: 10
```

### 5. **Specific Test Fixes**

#### Fixed `tests/test_domain_filter.py`:
```python
def teardown_method(self):
    """Clean up test fixtures."""
    import shutil
    try:
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    except Exception:
        pass  # Ignore cleanup errors
```

#### Fixed `tests/test_agent_phase1b.py`:
```python
@pytest.fixture
def temp_vector_store(self):
    """Create a temporary vector store for testing."""
    temp_dir = tempfile.mkdtemp()
    
    # ... setup code ...
    
    yield store
    
    # Use ignore_errors to handle any remaining file locks
    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass  # Ignore cleanup errors
```

#### Fixed `tests/test_metrics_dashboard.py`:
```python
@pytest.fixture
def sample_metrics_file():
    """Create a temporary metrics file with sample data."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        # ... create file content ...
        temp_file = f.name
    
    # Yield the file name and clean up after the test
    yield temp_file
    
    # Cleanup
    try:
        if os.path.exists(temp_file):
            os.unlink(temp_file)
    except Exception:
        pass  # Ignore cleanup errors
```

#### Fixed `tests/test_tui_demo.py`:
```python
try:
    subprocess.run(cmd, timeout=30)  # Add timeout to prevent hanging
except (KeyboardInterrupt, subprocess.TimeoutExpired):
    print("\nDemo stopped by user or timeout.")
```

## Test Coverage Added

### 1. **Cleanup Test Suite**

✅ **Created `tests/test_ci_cleanup.py`:**
- Vector store cleanup verification
- ChromaDB global instance cleanup
- Environment isolation testing
- Signal handler smoke tests

### 2. **Resource Analysis Test**

✅ **Created `tests/test_cleanup_analysis.py`:**
- Temporary file cleanup analysis
- ChromaDB connection cleanup
- Subprocess cleanup verification
- Thread cleanup testing
- SQLite connection cleanup
- File handle cleanup
- Environment variable cleanup

## Environment Variables for Testing

The following environment variables are automatically set during tests:

```bash
VECTOR_STORE_PATH=/tmp/test_vector_store
CONVERSATION_DB_PATH=/tmp/test_conversations.sqlite
CHROMA_TELEMETRY=false
IKOMA_TUI_MODE=false
IKOMA_METRICS_ENABLED=false
```

## Best Practices Implemented

### 1. **Error Handling**
- All cleanup operations wrapped in try/except blocks
- Use `ignore_errors=True` for file operations
- Graceful degradation when cleanup fails

### 2. **Resource Isolation**
- Each test runs in its own temporary environment
- Environment variables are restored after each test
- Temporary files are created in isolated directories

### 3. **Timeout Protection**
- All subprocess calls have timeouts
- CI jobs have timeout limits
- Long-running operations are protected

### 4. **Connection Cleanup**
- ChromaDB connections are properly closed
- SQLite connections are explicitly closed
- Global instances are reset

## Verification

To verify the fixes work:

```bash
# Run the cleanup tests
pytest tests/test_ci_cleanup.py -v

# Run the analysis tests
pytest tests/test_cleanup_analysis.py -v

# Run existing tests to ensure they still work
pytest tests/test_agent_citations.py -v
pytest tests/test_persistence_vector_store.py -v

# Run a broader test suite
pytest tests/ -m "not dashboard" --cov
```

## Monitoring

To monitor for future cleanup issues:

1. **Watch for warnings** about unclosed connections
2. **Check for temporary files** left behind after tests
3. **Monitor subprocess timeouts** in CI logs
4. **Verify environment isolation** between tests

## Future Improvements

1. **Enhanced monitoring**: Add more detailed logging during cleanup operations
2. **Resource tracking**: Implement resource tracking to identify what's preventing cleanup
3. **Automated cleanup**: Add more aggressive cleanup for edge cases
4. **Performance optimization**: Optimize cleanup operations for faster test execution 