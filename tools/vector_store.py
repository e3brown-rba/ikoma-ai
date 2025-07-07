import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime
import chromadb
from chromadb.config import Settings
from langchain_openai import OpenAIEmbeddings
import openai

class PersistentVectorStore:
    """
    Persistent vector store using Chromadb for long-term memory storage.
    Replaces the ephemeral InMemoryStore with persistent storage.
    """
    
    def __init__(self, 
                 persist_directory: str = "agent/memory/vector_store",
                 collection_name: str = "agent_memories",
                 embedding_model: str = "nomic-ai/nomic-embed-text-v1.5-GGUF",
                 base_url: str = "http://127.0.0.1:11434/v1"):
        
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.base_url = base_url
        
        # Initialize Chromadb client
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(collection_name)
        except Exception:
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"description": "Agent long-term memory storage"}
            )
        
        # Initialize embeddings
        self.embeddings = PatchedOpenAIEmbeddings(
            openai_api_key="sk-dummy",
            openai_api_base=base_url,
            model=embedding_model
        )
    
    def put(self, namespace: tuple, key: str, value: Dict[str, Any]) -> None:
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
                "context": value.get("context", "unknown")
            }
            
            # Add custom metadata
            if value.get("plan_context"):
                metadata["plan_context"] = json.dumps(value["plan_context"])
            if value.get("reflection"):
                metadata["reflection"] = value["reflection"]
            
            # Store in collection
            self.collection.add(
                documents=[content],
                embeddings=[embedding],
                metadatas=[metadata],
                ids=[doc_id]
            )
            
        except Exception as e:
            print(f"Error storing memory: {e}")
    
    def search(self, namespace: tuple, query: str, limit: int = 5) -> List[Dict[str, Any]]:
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
                query_embeddings=[query_embedding],
                n_results=limit,
                where={"namespace": "-".join(namespace)}
            )
            
            # Format results
            memories = []
            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                    
                    memory = {
                        "value": {
                            "content": doc,
                            "timestamp": metadata.get("timestamp"),
                            "context": metadata.get("context")
                        },
                        "distance": results["distances"][0][i] if results["distances"] else 1.0
                    }
                    
                    # Add custom metadata
                    if metadata.get("plan_context"):
                        try:
                            memory["value"]["plan_context"] = json.loads(metadata["plan_context"])
                        except (json.JSONDecodeError, TypeError):
                            pass
                    if metadata.get("reflection"):
                        memory["value"]["reflection"] = metadata["reflection"]
                    
                    memories.append(memory)
            
            return memories
            
        except Exception as e:
            print(f"Error searching memories: {e}")
            return []
    
    def get(self, namespace: tuple, key: str) -> Optional[Dict[str, Any]]:
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
                    "context": metadata.get("context")
                }
            
            return None
            
        except Exception as e:
            print(f"Error getting memory: {e}")
            return None
    
    def delete(self, namespace: tuple, key: str) -> bool:
        """Delete a specific memory."""
        try:
            doc_id = f"{'-'.join(namespace)}-{key}"
            self.collection.delete(ids=[doc_id])
            return True
            
        except Exception as e:
            print(f"Error deleting memory: {e}")
            return False
    
    def list_memories(self, namespace: tuple, limit: int = 10) -> List[Dict[str, Any]]:
        """List all memories in a namespace."""
        try:
            results = self.collection.get(
                where={"namespace": "-".join(namespace)},
                limit=limit
            )
            
            memories = []
            if results["documents"]:
                for i, doc in enumerate(results["documents"]):
                    metadata = results["metadatas"][i] if results["metadatas"] else {}
                    
                    memory = {
                        "key": metadata.get("key"),
                        "content": doc,
                        "timestamp": metadata.get("timestamp"),
                        "context": metadata.get("context")
                    }
                    memories.append(memory)
            
            return memories
            
        except Exception as e:
            print(f"Error listing memories: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the memory store."""
        try:
            count = self.collection.count()
            return {
                "total_memories": count,
                "collection_name": self.collection_name,
                "persist_directory": str(self.persist_directory)
            }
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {"error": str(e)}
    
    def migrate_from_memory_store(self, old_memories: List[Dict[str, Any]]) -> int:
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
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> List[float]:
        temp_client = openai.OpenAI(
            api_key=self.openai_api_key,
            base_url=self.openai_api_base
        )
        response = temp_client.embeddings.create(input=text, model=self.model)
        return response.data[0].embedding


# Global instance for easy access
vector_store = None

def get_vector_store() -> PersistentVectorStore:
    """Get or create the global vector store instance."""
    global vector_store
    if vector_store is None:
        vector_store = PersistentVectorStore(
            persist_directory=os.getenv("VECTOR_STORE_PATH", "agent/memory/vector_store"),
            embedding_model=os.getenv("LMSTUDIO_EMBED_MODEL", "nomic-ai/nomic-embed-text-v1.5-GGUF"),
            base_url=os.getenv("LMSTUDIO_BASE_URL", "http://127.0.0.1:11434/v1")
        )
    return vector_store 

def example_persist():
    """Minimal example to verify persistence in regression tests."""
    store = get_vector_store()
    test_ns = ("tests", "persistence")
    test_key = "demo"
    test_value = {"content": "Hello persistence", "timestamp": datetime.now().isoformat()}
    store.put(test_ns, test_key, test_value)
    return store.get(test_ns, test_key)

if __name__ == "__main__":
    import argparse
    import shutil

    parser = argparse.ArgumentParser(description="PersistentVectorStore utility helper")
    parser.add_argument("--reset", action="store_true", help="Delete the entire persistent vector store (irreversible)")
    parser.add_argument("--path", type=str, default="agent/memory/vector_store", help="Path to the persistent vector store directory")

    args = parser.parse_args()

    if args.reset:
        target_path = Path(args.path)
        if target_path.exists() and target_path.is_dir():
            confirmation = input(f"⚠️  This will permanently delete the vector store at {target_path}. Continue? (yes/no): ").strip().lower()
            if confirmation == "yes":
                shutil.rmtree(target_path)
                print(f"✅ Vector store at {target_path} has been deleted.")
            else:
                print("❌ Reset cancelled.")
        else:
            print(f"Vector store directory {target_path} does not exist.") 