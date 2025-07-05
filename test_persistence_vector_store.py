import os
import shutil
from pathlib import Path
import uuid
from datetime import datetime

from tools.vector_store import get_vector_store


def test_vector_store_persistence(tmp_path):
    """Ensure memories survive process restarts (Chromadb persistent client)."""
    # Use a temporary directory so we don't touch the real store
    test_store_dir = tmp_path / "vector_store"
    os.environ["VECTOR_STORE_PATH"] = str(test_store_dir)

    # FIRST RUN: put a memory
    store1 = get_vector_store()
    ns = ("tests", str(uuid.uuid4()))
    key = "persistence_check"
    value = {"content": "persistent memory", "timestamp": datetime.now().isoformat()}
    store1.put(ns, key, value)

    # Simulate process exit by discarding store1
    del store1

    # SECOND RUN: new process -> new store instance
    store2 = get_vector_store()
    retrieved = store2.get(ns, key)

    assert retrieved is not None, "Memory was not retrieved after restart"
    assert retrieved["content"] == "persistent memory"

    # Cleanup
    shutil.rmtree(test_store_dir, ignore_errors=True) 