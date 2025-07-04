# Chroma Memory Integration for iKOMA Agent

## Overview

The iKOMA agent now includes persistent memory using Chroma vector database. This allows the agent to remember previous conversations and provide more contextual responses across sessions.

## Features

- **Persistent Memory**: Conversations are stored in a local Chroma database
- **Vector Search**: Semantic search for relevant conversation history
- **Context Awareness**: Agent can reference previous interactions
- **Automatic Storage**: Memory is automatically saved and retrieved

## Setup

### Prerequisites

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure LM Studio is running with embeddings support

### Configuration

The memory system is automatically configured in `agent/agent.py`:

```python
import chromadb

# Chroma client with persistent storage
chroma_client = chromadb.PersistentClient(path="agent/memory")
collection = chroma_client.get_or_create_collection("ikoma_mem")

# Vector store with embeddings
vectorstore = Chroma(
    client=chroma_client,
    collection_name="ikoma_mem",
    embedding_function=embeddings
)

# Memory system
memory = VectorStoreRetrieverMemory(
    retriever=vectorstore.as_retriever(search_kwargs={"k": 6}),
    memory_key="chat_history",
    return_docs=True
)
```

## Usage

### Running the Agent

```bash
python agent/agent.py
```

The agent will automatically:
- Load previous conversation context
- Save new conversations to memory
- Use semantic search to find relevant history

### Testing the Integration

Run the test script to verify everything works:

```bash
python test_chroma_memory.py
```

## Memory Storage

- **Location**: `agent/memory/` directory
- **Collection**: `ikoma_mem`
- **Retrieval**: Top 6 most relevant conversation snippets
- **Persistence**: Automatic across sessions

## How It Works

1. **Input Processing**: User input is processed by the agent
2. **Memory Retrieval**: Relevant conversation history is retrieved using vector search
3. **Context Integration**: Previous context is included in the prompt
4. **Response Generation**: Agent generates response with full context
5. **Memory Storage**: New conversation is automatically saved to Chroma

## Benefits

- **Continuity**: Conversations feel more natural across sessions
- **Relevance**: Only the most relevant history is retrieved
- **Efficiency**: Vector search is fast and semantic
- **Scalability**: Can handle large conversation histories

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed
2. **LM Studio Connection**: Verify LM Studio is running with embeddings
3. **Memory Directory**: Check that `agent/memory/` directory exists

### Reset Memory

To clear all conversation history:

```bash
rm -rf agent/memory/
```

The directory will be recreated on the next run.

## Advanced Configuration

### Memory Parameters

You can adjust memory behavior by modifying these parameters:

```python
memory = VectorStoreRetrieverMemory(
    retriever=vectorstore.as_retriever(search_kwargs={"k": 6}),  # Number of relevant snippets
    memory_key="chat_history",  # Key for memory in prompt
    return_docs=True  # Return full documents instead of just text
)
```

### Embedding Model

The system uses OpenAI-compatible embeddings. You can change the model by modifying the `OpenAIEmbeddings` configuration in `agent/agent.py`. 