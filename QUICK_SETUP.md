# Quick Setup Guide for New Machines

## 🚀 Prerequisites

### 1. Python 3.10+ Required
Your current Python version is 3.9.6, but iKOMA requires Python 3.10+.

**Install Python 3.10+ on macOS:**

**Option A: Using Homebrew (Recommended)**
```bash
# Install Homebrew first
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Add Homebrew to PATH (for Apple Silicon Macs)
echo 'export PATH="/opt/homebrew/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# Install Python 3.11
brew install python@3.11
```

**Option B: Direct Download**
- Visit https://www.python.org/downloads/
- Download Python 3.11 or later
- Install the package

### 2. LM Studio (Required for Local AI)
- Download from: https://lmstudio.ai/
- Install and launch
- Download a compatible model (e.g., Meta Llama 3 8B Instruct)
- Start local server on port 11434

## 🛠️ Automated Setup

Run the setup script:
```bash
./setup.sh
```

This script will:
- ✅ Check Python version
- ✅ Create virtual environment
- ✅ Install all dependencies
- ✅ Create necessary directories
- ✅ Set up environment file
- ✅ Verify installation

## 🔧 Manual Setup (if automated fails)

### 1. Create Virtual Environment
```bash
python3.11 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
cp config.env.template .env
# Edit .env file as needed
```

### 4. Create Directories
```bash
mkdir -p agent/memory/vector_store
mkdir -p agent/ikoma_sandbox
```

## ⚙️ Configuration

### Environment Variables (.env file)
Key settings to configure:

```bash
# LM Studio Configuration
LMSTUDIO_BASE_URL=http://127.0.0.1:11434/v1
LMSTUDIO_MODEL=meta-llama-3-8b-instruct

# Memory Configuration
VECTOR_STORE_PATH=agent/memory/vector_store
MEMORY_SEARCH_LIMIT=5

# File Operations
SANDBOX_PATH=agent/ikoma_sandbox
```

### LM Studio Setup
1. Open LM Studio
2. Download a model (recommended: Meta Llama 3 8B Instruct)
3. Go to "Local Server" tab
4. Set port to **11434**
5. Click "Start Server"

## 🧪 Testing

### Run Basic Tests
```bash
# Activate virtual environment
source venv/bin/activate

# Test core functionality
python test_agent_phase1b.py

# Test memory persistence
python test_persistence_vector_store.py
```

### Check Code Formatting
```bash
# Install ruff if not already installed
pip install ruff

# Check formatting
ruff format --check --diff .

# Fix formatting issues
ruff format .
```

## 🚀 Running the Agent

### Start the Agent
```bash
# Activate virtual environment
source venv/bin/activate

# Run the agent
python run_agent.py
```

### Example Usage
```
🧑‍💻 You: "List all files in the sandbox"
🤖 Ikoma: Planning your request...

Plan Created:
✓ Step 1: List files in sandbox

Execution Results:
✓ Step 1: list_sandbox_files → Found 0 files

Task completed! Sandbox is currently empty.
```

## 📁 Project Structure

```
iKOMA/
├── agent/                    # Main agent code
│   ├── agent.py             # LangGraph agent
│   ├── memory/              # Persistent memory
│   └── ikoma_sandbox/       # Safe file operations
├── tools/                   # Tool system
│   ├── fs_tools.py          # File operations
│   ├── vector_store.py      # Memory system
│   └── mcp_schema.json      # Tool definitions
├── .env                     # Environment variables
├── requirements.txt         # Python dependencies
├── setup.sh                 # Setup script
└── run_agent.py            # Main entry point
```

## 🔍 Troubleshooting

### Common Issues

**1. Python Version Error**
```bash
# Check Python version
python3 --version

# If < 3.10, install newer version (see Prerequisites)
```

**2. Import Errors**
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

**3. LM Studio Connection Error**
- Ensure LM Studio is running
- Check port 11434 is open
- Verify model is loaded in LM Studio

**4. Memory/Vector Store Errors**
```bash
# Clear and recreate memory
rm -rf agent/memory/vector_store/*
mkdir -p agent/memory/vector_store
```

### Getting Help
- Check README.md for detailed documentation
- Review PHASE_1B_SUMMARY.md for technical details
- See CHROMA_MEMORY_SETUP.md for memory configuration

## ✅ Verification Checklist

- [ ] Python 3.10+ installed
- [ ] Virtual environment created and activated
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Environment file configured (`.env`)
- [ ] LM Studio installed and running on port 11434
- [ ] Model downloaded in LM Studio
- [ ] Tests passing (`python test_agent_phase1b.py`)
- [ ] Agent runs successfully (`python run_agent.py`)

## 🎯 Next Steps

1. **Customize Configuration**: Edit `.env` file for your preferences
2. **Download Models**: Add more models to LM Studio for different capabilities
3. **Explore Tools**: Check `tools/mcp_schema.json` for available operations
4. **Extend Functionality**: Add custom tools or modify agent behavior
5. **Monitor Performance**: Check memory usage and optimize settings

---

**Need help?** The setup script (`./setup.sh`) will guide you through most of this process automatically! 