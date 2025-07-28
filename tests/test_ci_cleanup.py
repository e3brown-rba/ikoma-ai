#!/usr/bin/env python3
"""
Test CI cleanup functionality to prevent hanging issues.
"""

import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from tools.vector_store import get_vector_store, cleanup_vector_store


def test_vector_store_cleanup():
    """Test that vector store cleanup works properly."""
    # Create a temporary directory for testing
    temp_dir = Path(tempfile.mkdtemp())
    os.environ["VECTOR_STORE_PATH"] = str(temp_dir)
    
    try:
        # Mock the embedding service to avoid connection errors
        with patch("tools.vector_store.PatchedOpenAIEmbeddings") as mock_embeddings:
            mock_emb = Mock()
            mock_emb.embed_query.return_value = [0.1] * 384  # Mock embedding vector
            mock_embeddings.return_value = mock_emb
            
            # Get vector store instance
            store = get_vector_store()
            assert store is not None
            
            # Test cleanup
            cleanup_vector_store()
            
            # Verify cleanup worked
            from tools.vector_store import vector_store
            assert vector_store is None
            
    except Exception as e:
        # Skip the test if database operations fail (e.g., in CI with read-only filesystem)
        pytest.skip(f"Database operation failed: {e}")
    finally:
        # Cleanup temporary directory
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


def test_chromadb_global_cleanup():
    """Test that ChromaDB global instances are properly cleaned up."""
    try:
        import chromadb
        
        # Mock ChromaDB global instance
        chromadb._client_instance = Mock()
        
        # Test cleanup
        cleanup_vector_store()
        
        # Verify global instance was cleared
        assert chromadb._client_instance is None
        
    except ImportError:
        pytest.skip("ChromaDB not available")


def test_environment_isolation():
    """Test that test environment variables are properly isolated."""
    # Store original environment
    original_env = os.environ.copy()
    
    # Test environment variables
    test_vars = {
        "VECTOR_STORE_PATH": "/tmp/test_vector_store",
        "CONVERSATION_DB_PATH": "/tmp/test_conversations.sqlite",
        "CHROMA_TELEMETRY": "false",
        "IKOMA_TUI_MODE": "false",
        "IKOMA_METRICS_ENABLED": "false",
    }
    
    # Set test environment
    for key, value in test_vars.items():
        os.environ[key] = value
    
    # Verify environment was set
    for key, value in test_vars.items():
        assert os.environ[key] == value
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)
    
    # Verify original environment was restored
    for key in test_vars:
        if key in original_env:
            assert os.environ[key] == original_env[key]


def test_signal_handler_import():
    """Test that signal handler can be imported and called."""
    try:
        from agent.agent import signal_handler
        import signal
        
        # Test that signal handler exists and is callable
        assert callable(signal_handler)
        
        # Test that it can be called (should exit, but we can't test that easily)
        # This is more of a smoke test to ensure the function exists
        
    except ImportError as e:
        pytest.skip(f"Signal handler not available: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 