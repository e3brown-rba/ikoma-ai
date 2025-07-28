# tests/conftest.py
import os
import shutil
import tempfile
from pathlib import Path

import pytest


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
    os.environ["IKOMA_TUI_MODE"] = "false"  # Disable TUI in tests

    yield

    # Cleanup after test
    try:
        # Force close any ChromaDB connections
        import chromadb

        if hasattr(chromadb, "_client_instance"):
            chromadb._client_instance = None
    except ImportError:
        pass

    # Remove temporary files
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture(autouse=True)
def disable_background_threads():
    """Disable background threads that might prevent test cleanup."""
    # Disable TUI broadcaster
    os.environ["IKOMA_TUI_MODE"] = "false"

    # Disable metrics collection in tests
    os.environ["IKOMA_METRICS_ENABLED"] = "false"

    yield
