import json
import logging
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import chromadb
import openai
from chromadb.config import Settings
from langchain_openai import OpenAIEmbeddings

from tools.citation_manager import CitationSource
from tools.security import sanitize_citation_content, validate_citation_metadata

# Suppress ChromaDB telemetry errors (noisy, not critical)
logging.getLogger("chromadb.telemetry").setLevel(logging.ERROR)
# Optionally, suppress all ChromaDB logs:
# logging.getLogger("chromadb").setLevel(logging.WARNING)


class PersistentVectorStore:
    """
    Persistent vector store using Chromadb for long-term memory storage.
    Replaces the ephemeral InMemoryStore with persistent storage.
    """

    def __init__(
        self,
        persist_directory: str = "agent/memory/vector_store",
        collection_name: str = "agent_memories",
        embedding_model: str = "nomic-ai/nomic-embed-text-v1.5-GGUF",
        base_url: str = "http://127.0.0.1:11434/v1",
    ):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.base_url = base_url

        # Initialize Chromadb client
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )

        # Get or create collection
        try:
            self.collection = self.client.get_collection(collection_name)
        except Exception:
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"description": "Agent long-term memory storage"},
            )

        # Initialize embeddings
        self.embeddings = PatchedOpenAIEmbeddings(
            openai_api_key="sk-dummy",
            openai_api_base=base_url,
            model=embedding_model,
            chunk_size=1000,  # Add chunk_size parameter
        )

    def put(self, namespace: tuple[str, str], key: str, value: dict[str, Any]) -> None:
        """Store a memory entry with namespace and key."""
        try:
            # Create document ID from namespace and key
            doc_id = f"{'-'.join(namespace)}-{key}"

            # Prepare document content
            content = value.get("content", "")
            if not content:
                content = json.dumps(value)

            # Generate embedding
            embedding = self.embeddings.embed_query(content)

            # Prepare metadata
            metadata = {
                "namespace": "-".join(namespace),
                "key": key,
                "timestamp": value.get("timestamp", datetime.now().isoformat()),
                "context": value.get("context", "unknown"),
            }

            # Add custom metadata
            if value.get("plan_context"):
                metadata["plan_context"] = json.dumps(value["plan_context"])
            if value.get("reflection"):
                metadata["reflection"] = value["reflection"]

            # Store in collection
            self.collection.add(
                documents=[content],
                embeddings=[embedding],  # type: ignore[arg-type]
                metadatas=[metadata],
                ids=[doc_id],
            )

        except Exception as e:
            print(f"Error storing memory: {e}")

    def search(
        self, namespace: tuple[str, str], query: str, limit: int = 5
    ) -> list[dict[str, Any]]:
        """Search for memories using semantic similarity.

        Returns:
            List[Dict[str, Any]]: List of memory dictionaries, each containing:
                - "value": Dict with "content", "timestamp", "context", and optional "plan_context"/"reflection"
                - "distance": Float representing semantic similarity distance (lower = more similar)

        The return structure ensures compatibility with retrieve_long_term_memory() which expects
        objects with .value attributes or plain dictionaries.
        """
        try:
            # Generate query embedding
            query_embedding = self.embeddings.embed_query(query)

            # Search collection
            results = self.collection.query(
                query_embeddings=[query_embedding],  # type: ignore[arg-type]
                n_results=limit,
                where={"namespace": "-".join(namespace)},
            )

            # Format results
            memories = []
            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    metadata = (
                        results["metadatas"][0][i] if results["metadatas"] else {}
                    )

                    memory = {
                        "value": {
                            "content": doc,
                            "timestamp": metadata.get("timestamp"),
                            "context": metadata.get("context"),
                        },
                        "distance": results["distances"][0][i]
                        if results["distances"]
                        else 1.0,
                    }

                    # Add custom metadata
                    if metadata.get("plan_context"):
                        try:
                            value_dict = (
                                memory["value"]
                                if isinstance(memory["value"], dict)
                                else {}
                            )
                            plan_context = metadata["plan_context"]
                            if isinstance(plan_context, str):
                                value_dict["plan_context"] = json.loads(plan_context)
                            memory["value"] = value_dict
                        except (json.JSONDecodeError, TypeError):
                            pass
                    if metadata.get("reflection"):
                        value_dict = (
                            memory["value"] if isinstance(memory["value"], dict) else {}
                        )
                        value_dict["reflection"] = metadata["reflection"]
                        memory["value"] = value_dict

                    memories.append(memory)

            return memories

        except Exception as e:
            print(f"Error searching memories: {e}")
            return []

    def get(self, namespace: tuple[str, str], key: str) -> dict[str, Any] | None:
        """Get a specific memory by namespace and key."""
        try:
            doc_id = f"{'-'.join(namespace)}-{key}"

            results = self.collection.get(ids=[doc_id])

            if results["documents"] and results["documents"][0]:
                doc = results["documents"][0]
                metadata = results["metadatas"][0] if results["metadatas"] else {}

                return {
                    "content": doc,
                    "timestamp": metadata.get("timestamp"),
                    "context": metadata.get("context"),
                }

            return None

        except Exception as e:
            print(f"Error getting memory: {e}")
            return None

    def delete(self, namespace: tuple[str, str], key: str) -> bool:
        """Delete a specific memory."""
        try:
            doc_id = f"{'-'.join(namespace)}-{key}"
            self.collection.delete(ids=[doc_id])
            return True

        except Exception as e:
            print(f"Error deleting memory: {e}")
            return False

    def list_memories(
        self, namespace: tuple[str, str], limit: int = 10
    ) -> list[dict[str, Any]]:
        """List all memories in a namespace."""
        try:
            results = self.collection.get(
                where={"namespace": "-".join(namespace)}, limit=limit
            )

            memories = []
            if results["documents"]:
                for i, doc in enumerate(results["documents"]):
                    metadata = results["metadatas"][i] if results["metadatas"] else {}

                    memory = {
                        "key": metadata.get("key"),
                        "content": doc,
                        "timestamp": metadata.get("timestamp"),
                        "context": metadata.get("context"),
                    }
                    memories.append(memory)

            return memories

        except Exception as e:
            print(f"Error listing memories: {e}")
            return []

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about the memory store."""
        try:
            count = self.collection.count()
            return {
                "total_memories": count,
                "collection_name": self.collection_name,
                "persist_directory": str(self.persist_directory),
            }
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {"error": str(e)}

    def migrate_from_memory_store(self, old_memories: Any) -> int:
        """Migrate memories from old InMemoryStore format."""
        migrated = 0

        for memory in old_memories:
            try:
                # Extract namespace and key from memory structure
                namespace = memory.get("namespace", ("memories", "default"))
                key = memory.get("key", str(uuid.uuid4()))
                value = memory.get("value", memory)

                self.put(namespace, key, value)
                migrated += 1

            except Exception as e:
                print(f"Error migrating memory: {e}")

        return migrated


class PatchedOpenAIEmbeddings(OpenAIEmbeddings):
    """
    A patch to handle local servers that do not support batching.
    """

    def __init__(
        self,
        *args: Any,
        openai_api_key: Any = None,
        openai_api_base: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.openai_api_key = openai_api_key
        self.openai_api_base = openai_api_base

    def embed_documents(
        self, texts: list[str], chunk_size: int | None = None, **kwargs: Any
    ) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str, **kwargs: Any) -> list[float]:
        temp_client = openai.OpenAI(
            api_key=str(self.openai_api_key) if self.openai_api_key else None,
            base_url=self.openai_api_base,
        )
        response = temp_client.embeddings.create(input=text, model=self.model)
        return response.data[0].embedding


# Global instance for easy access
vector_store: PersistentVectorStore | None = None


def get_vector_store() -> PersistentVectorStore:
    """Get or create the global vector store instance."""
    global vector_store
    if vector_store is None:
        vector_store = PersistentVectorStore(
            persist_directory=os.getenv(
                "VECTOR_STORE_PATH", "agent/memory/vector_store"
            ),
            embedding_model=os.getenv(
                "LMSTUDIO_EMBED_MODEL", "nomic-ai/nomic-embed-text-v1.5-GGUF"
            ),
            base_url=os.getenv("LMSTUDIO_BASE_URL", "http://127.0.0.1:11434/v1"),
        )
    return vector_store


def example_persist() -> dict[str, Any] | None:
    """Minimal example to verify persistence in regression tests."""
    store = get_vector_store()
    test_ns = ("tests", "persistence")
    test_key = "demo"
    test_value = {
        "content": "Hello persistence",
        "timestamp": datetime.now().isoformat(),
    }
    store.put(test_ns, test_key, test_value)
    return store.get(test_ns, test_key)


def get_citation_collection(client: Any = None) -> Any:
    """Get or create the optimized citation collection in ChromaDB."""
    import chromadb
    if client is None:
        client = chromadb.PersistentClient(
            path="agent/memory/vector_store",
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )
    try:
        collection = client.get_collection("citations_v2")
    except Exception:
        collection = client.create_collection(
            name="citations_v2",
            metadata={
                "description": "Citation storage for agent",
                "hnsw:space": "cosine",
                "hnsw:M": 16,
                "hnsw:batch_size": 1000,
                "hnsw:sync_threshold": 10000,
            },
        )
    return collection


def store_citation_with_metadata(citation_source: CitationSource, content: str, client: Any = None) -> None:
    """Store a citation in the citation collection with optimized metadata and security validation."""
    start_time = time.time()
    # Validate and sanitize citation metadata
    metadata = {
        "url": citation_source.url,
        "title": citation_source.title,
        "domain": citation_source.domain,
        "confidence_score": citation_source.confidence_score,
        "content_preview": citation_source.content_preview,
        "source_type": citation_source.source_type,
    }

    try:
        validated_metadata = validate_citation_metadata(metadata)
    except ValueError as e:
        print(f"Warning: Citation metadata validation failed: {e}")
        # Use fallback metadata for invalid citations
        validated_metadata = {
            "url": "https://example.com/invalid",
            "title": "Invalid Citation",
            "domain": "unknown",
            "confidence_score": 0.0,
            "content_preview": "",
            "source_type": "unknown",
        }

    # Sanitize content before storage
    sanitized_content = sanitize_citation_content(content)

    # Add additional metadata for storage
    storage_metadata = {
        **validated_metadata,
        "timestamp": citation_source.timestamp,
        "retrieval_rank": citation_source.id,
    }

    collection = get_citation_collection(client)
    collection.add(
        documents=[sanitized_content],
        metadatas=[storage_metadata],
        ids=[f"citation_{citation_source.id}"]
    )
    elapsed = time.time() - start_time
    logging.info(f"store_citation_with_metadata: Stored citation {citation_source.id} in {elapsed:.4f} seconds.")


def get_citation_metadata(citation_id: int, client: Any = None) -> Any:
    """Retrieve citation metadata by citation ID."""
    collection = get_citation_collection(client)
    result = collection.get(ids=[f"citation_{citation_id}"])
    metadatas = result.get("metadatas") if result else None
    if isinstance(metadatas, list) and len(metadatas) > 0 and metadatas[0]:
        return metadatas[0]
    return None


def get_citation_by_id(citation_id: int, client: Any = None) -> Any:
    """Retrieve a citation by its ID and log performance."""
    start_time = time.time()
    collection = get_citation_collection(client)
    result = collection.get(ids=[f"citation_{citation_id}"])
    elapsed = time.time() - start_time
    logging.info(f"get_citation_by_id: Retrieved citation {citation_id} in {elapsed:.4f} seconds.")
    return result


if __name__ == "__main__":
    import argparse
    import shutil

    parser = argparse.ArgumentParser(description="PersistentVectorStore utility helper")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete the entire persistent vector store (irreversible)",
    )
    parser.add_argument(
        "--path",
        type=str,
        default="agent/memory/vector_store",
        help="Path to the persistent vector store directory",
    )

    args = parser.parse_args()

    if args.reset:
        target_path = Path(args.path)
        if target_path.exists() and target_path.is_dir():
            confirmation = (
                input(
                    f"⚠️  This will permanently delete the vector store at {target_path}. Continue? (yes/no): "
                )
                .strip()
                .lower()
            )
            if confirmation == "yes":
                shutil.rmtree(target_path)
                print(f"✅ Vector store at {target_path} has been deleted.")
            else:
                print("❌ Reset cancelled.")
        else:
            print(f"Vector store directory {target_path} does not exist.")
