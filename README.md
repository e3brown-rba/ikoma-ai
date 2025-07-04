# iKOMA - AI Assistant Agent

A local AI assistant powered by LangChain and your local LLM (LM Studio/Ollama).

## Features

- 🤖 **Conversational AI**: Chat with your local LLM
- 🧮 **Math Calculations**: Solve mathematical problems
- 📁 **File Management**: Create, read, and manage files in a secure sandbox
- 💾 **Memory**: Persistent conversation history
- 🔒 **Safety**: Sandboxed file operations for security

## Setup

### 1. Prerequisites

- Python 3.10+ 
- LM Studio running on port 1234 (or update the port in `agent/agent.py`)
- Git

### 2. Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd iKOMA

# Create virtual environment
python -m venv ikoma/.venv

# Activate virtual environment
# Windows:
ikoma\.venv\Scripts\activate
# macOS/Linux:
source ikoma/.venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. LM Studio Setup

1. Download and install [LM Studio](https://lmstudio.ai/)
2. Download a model (e.g., Meta Llama 3 8B Instruct)
3. Start the local server on port 1234
4. Make sure the model name in `agent/agent.py` matches your model

## Usage

### Option 1: Using the Runner Script (Recommended)

```bash
python run_agent.py
```

### Option 2: Direct Execution

```bash
# Make sure virtual environment is activated
cd agent
python agent.py
```

## Example Commands

```
🧑‍💻 You: Create a text file called notes.txt with my shopping list
🧑‍💻 You: What is 25 * 37?
🧑‍💻 You: List all files in the sandbox
🧑‍💻 You: Read the contents of notes.txt
🧑‍💻 You: What's the weather like? (general conversation)
```

## Project Structure

```
iKOMA/
├── agent/
│   └── agent.py          # Main agent code
├── ikoma/
│   └── .venv/            # Virtual environment
├── ikoma_sandbox/        # Secure file operations area
├── requirements.txt      # Python dependencies
├── run_agent.py         # Convenient runner script
└── README.md            # This file
```

## Configuration

### Changing LLM Server

Edit `agent/agent.py` and update:

```python
llm = ChatOpenAI(
    base_url="http://127.0.0.1:1234/v1",  # Your LM Studio port
    model="meta-llama-3-8b-instruct",     # Your model name
    temperature=0.1,
)
```

### Adding More Tools

The agent is designed to be extensible. Add new tools by:

1. Creating a new `@tool` decorated function
2. Adding it to the `tools` list
3. The agent will automatically discover and use it

## Safety Features

- File operations are restricted to the `ikoma_sandbox/` directory
- Only `.txt` files are allowed for now
- All operations are logged and visible
- No access to system files or network operations

## Troubleshooting

### Import Errors
Make sure the virtual environment is activated and dependencies are installed:
```bash
pip install -r requirements.txt
```

### Connection Errors
- Check that LM Studio is running on the correct port
- Verify the model name matches exactly
- Ensure the model is loaded and ready in LM Studio

### Tool Errors
- The agent may take a few iterations to get the tool format right
- Check the verbose output to see what's happening
- File operations are restricted to the sandbox for security

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

MIT License - see LICENSE file for details
