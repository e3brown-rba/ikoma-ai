# iKOMA - Intelligent AI Assistant with Memory

A sophisticated local AI assistant powered by LangGraph and your local LLM (LM Studio/Ollama) with advanced memory capabilities and continuous learning.

## ✨ Features

- 🧠 **Advanced Memory System**: Dual memory architecture with short-term and long-term memory
  - **Short-term**: Thread-scoped conversation state for immediate context
  - **Long-term**: Cross-session semantic memory with intelligent retrieval
  - **Learning**: Continuous improvement through nightly reflection and analysis
- 🤖 **Conversational AI**: Natural conversations with your local LLM
- 🧮 **Math Calculations**: Solve complex mathematical problems with step-by-step reasoning
- 📁 **Safe File Management**: Create, read, and manage files with confirmation prompts
- 🔄 **Reflection & Learning**: Automated nightly analysis to extract insights and improve responses
- 🛡️ **Enhanced Safety**: Confirmation prompts for all destructive operations
- 🔍 **Semantic Search**: Find relevant memories and context by meaning, not just keywords
- 🏗️ **Modern Architecture**: Built on LangGraph for reliable, scalable agent workflows

## 🚀 Quick Start

### Prerequisites

- Python 3.10+ 
- LM Studio or Ollama running locally
- Git

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd iKOMA

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### LM Studio Setup

1. Download and install [LM Studio](https://lmstudio.ai/)
2. Download a compatible model (e.g., Meta Llama 3 8B Instruct)
3. Start the local server (default: port 1234)
4. Configure environment variables (see Configuration section)

## 🎯 Usage

### Starting the Agent

```bash
python agent/agent.py
```

### Example Interactions

```
🧑‍💻 You: I prefer vegetarian food and I'm working on a Python project
🤖 Ikoma: I'll remember your dietary preferences and current project focus.

🧑‍💻 You: Create a file with my project notes
🤖 Ikoma: ⚠️  CONFIRMATION REQUIRED:
   Action: Create new file
   File: project_notes.txt
   Continue? (yes/no): yes
✓ Created file: project_notes.txt

🧑‍💻 You: What did I tell you about my preferences?
🤖 Ikoma: I remember you prefer vegetarian food and you're working on a Python project.

🧑‍💻 You: Calculate the Fibonacci sequence for 10 terms
🤖 Ikoma: [Shows step-by-step calculation using math tools]
```

## 📁 Project Structure

```
iKOMA/
├── agent/
│   ├── agent.py              # Main LangGraph agent with memory
│   ├── memory/
│   │   ├── conversations.sqlite  # Short-term memory (checkpoints)
│   │   └── chroma.sqlite3        # Legacy (no longer used)
│   └── ikoma_sandbox/        # Secure file operations area
├── cursor/
│   └── ikoma.cursor.yaml     # Cursor AI integration config
├── reflect.py               # Nightly reflection and learning script
├── requirements.txt         # Python dependencies (inc. langgraph)
├── test_agent_modern.py     # Comprehensive test suite
├── TODO.md                  # ✅ Completed development tasks
└── README.md               # This file
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file or set these environment variables:

```bash
# LM Studio Configuration
LMSTUDIO_BASE_URL=http://127.0.0.1:1234/v1
LMSTUDIO_MODEL=meta-llama-3-8b-instruct
LMSTUDIO_EMBED_MODEL=nomic-ai/nomic-embed-text-v1.5-GGUF

# File Operations
SANDBOX_PATH=agent/ikoma_sandbox

# OpenAI API (for cloud models, optional)
OPENAI_API_KEY=your-key-here
```

### Memory System

The agent automatically manages two types of memory:

1. **Short-term Memory**: Conversation state persisted via SQLite checkpointer
2. **Long-term Memory**: Semantic memories stored with embedding-based search

No manual configuration required - the system initializes automatically.

## 🔄 Reflection & Learning

### Automated Nightly Reflection

The `reflect.py` script analyzes daily conversations and extracts insights:

```bash
# Run reflection for yesterday (default)
python reflect.py

# Run for specific date
python reflect.py --date 2024-01-15

# Dry run (preview without storing)
python reflect.py --dry-run --verbose
```

### Schedule with Cron

Add to your crontab for automated learning:

```bash
# Run every night at 2 AM
0 2 * * * /usr/bin/python3 /path/to/iKOMA/reflect.py >> /var/log/ikoma_reflect.log 2>&1
```

### What Reflection Provides

- **Daily Summaries**: Overview of conversation topics and patterns
- **Lessons Learned**: Extracted insights about user preferences and behaviors  
- **User Patterns**: Identification of interaction patterns and common requests
- **Improvement Suggestions**: AI-generated recommendations for better responses

## 🛡️ Safety Features

### File Operation Safety

- **Confirmation Prompts**: All file creation/modification requires explicit user approval
- **Sandbox Isolation**: File operations restricted to designated sandbox directory
- **Clear Communication**: Users see exactly what action will be performed
- **Graceful Cancellation**: Easy to abort operations without side effects

### Memory Privacy

- **User-Scoped**: Memories are isolated per user (configurable user ID)
- **Controlled Storage**: Only meaningful content is stored (not everything)
- **Transparent Access**: Users can see what the agent remembers about them

## 🧪 Testing

Run the comprehensive test suite:

```bash
python test_agent_modern.py
```

Tests cover:
- Memory system functionality
- File operations with safety features
- LangGraph workflow execution
- Tool integration
- Error handling

## 🔧 Development

### Adding New Tools

1. Create a new `@tool` decorated function:

```python
@tool
def my_new_tool(input_param: str) -> str:
    """Description of what the tool does."""
    return f"Result: {input_param}"
```

2. Add to the tools list in `agent_response` function
3. The agent automatically discovers and uses new tools

### Extending Memory

Customize memory behavior in the `store_long_term_memory` function:

```python
# Add custom memory criteria
if any(keyword in msg.content.lower() for keyword in ['custom', 'criteria']):
    memorable_content.append(msg.content)
```

### Memory Namespaces

Organize memories using namespaces:

```python
# User-specific memories
namespace = ("memories", user_id)

# Reflection insights
namespace = ("reflections", "daily_summaries")

# Custom categories
namespace = ("preferences", user_id, "food")
```

## 🚀 Advanced Features

### Multi-User Support

The memory system supports multiple users:

```python
# Different users get isolated memory
config = {
    "configurable": {
        "thread_id": f"thread_{user_id}_{session_id}",
        "user_id": user_id  # Unique identifier
    }
}
```

### Semantic Memory Search

Memories are retrieved by meaning, not exact text:

```python
# User says: "What restaurants do you recommend?"
# Agent finds: "User prefers vegetarian food" (stored weeks ago)
```

### Conversation Resumption

Conversations can be resumed across sessions:

```python
# Same thread_id resumes the exact conversation state
# Memories persist across all threads for a user
```

## 🛠️ Troubleshooting

### Memory Issues

- **Database locked**: Ensure only one agent instance is running
- **Missing memories**: Check that the `user_id` is consistent across sessions
- **Performance**: Long-term memories are automatically optimized for retrieval

### Connection Errors

- Verify LM Studio is running and accessible
- Check model name matches exactly (case-sensitive)
- Ensure embedding model is available for memory functionality

### File Operation Errors

- Check sandbox directory permissions
- Ensure sufficient disk space
- Verify file paths don't contain invalid characters

## 📈 Performance

### Memory Optimization

- **Semantic Search**: Efficient embedding-based retrieval
- **Selective Storage**: Only meaningful content is persisted
- **Automatic Cleanup**: Reflection process can consolidate old memories
- **Streaming**: Real-time conversation processing

### Scaling Considerations

- **Database**: SQLite suitable for single-user; consider PostgreSQL for multi-user
- **Embeddings**: Local embeddings for privacy; cloud for performance
- **Storage**: InMemoryStore for development; persistent stores for production

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests (`python test_agent_modern.py`)
4. Commit changes (`git commit -m 'Add amazing feature'`)
5. Push to branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

### Development Guidelines

- Maintain test coverage for new features
- Update documentation for API changes
- Follow the existing memory namespace conventions
- Test with multiple user scenarios

## 📄 License

MIT License - see LICENSE file for details

## 🎯 Roadmap

- [ ] Multi-modal memory (images, documents)
- [ ] Advanced reflection algorithms
- [ ] Memory compression and archival
- [ ] Plugin system for custom tools
- [ ] Web interface for memory management
- [ ] Integration with external knowledge bases

---

*Built with ❤️ using LangGraph, LangChain, and modern AI patterns*
