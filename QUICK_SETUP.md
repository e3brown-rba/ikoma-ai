# Quick Setup Guide for New Machines

## 🚀 Prerequisites

### 1. Python 3.11+ Required
Your current Python version is 3.9.6, but iKOMA requires Python 3.11+.

**Install Python 3.11+ on macOS:**

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
- ✅ Check Python version (3.11+ required)
- ✅ Create virtual environment
- ✅ Install all dependencies
- ✅ Create necessary directories
- ✅ Set up environment file with enhanced validation
- ✅ Verify installation and configuration
- ✅ Run environment sanity checks
- ✅ Validate GitHub token format (if provided)

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
python -m pytest tests/test_agent_phase1b.py

# Test memory persistence
python -m pytest tests/test_persistence_vector_store.py

# Test Phase 2 features
python -m pytest tests/test_dashboard_mvp.py
python -m pytest tests/test_web_extraction.py
python -m pytest tests/test_continuous_mode.py
```

### Check Code Quality
```bash
# Run linting checks
ruff check .

# Check code formatting
ruff format --check --diff .

# Run type checking
python -m mypy . --explicit-package-bases
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

### Phase 2 Features

#### Interactive Dashboard
```bash
# Start the metrics dashboard
python dashboard/app.py

# Access at http://localhost:8000
# View real-time performance metrics and agent statistics
```

#### Continuous Mode (Autonomous)
```bash
# Run with safety limits (25 iterations, 10 minutes max)
python run_agent.py --continuous --goal "Research Python best practices"

# Custom limits
python run_agent.py --continuous --goal "Create project structure" --max-iterations 15 --time-limit 20

# Human checkpoint every 3 iterations
python run_agent.py --continuous --goal "Refactor code" --checkpoint-every 3
```

#### Web Content Extraction
```bash
# The agent can now safely extract and process web content
# With OWASP-compliant domain filtering and security validation
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

- [ ] Python 3.11+ installed
- [ ] Virtual environment created and activated
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Environment file configured (`.env`) with enhanced validation
- [ ] LM Studio installed and running on port 11434
- [ ] Model downloaded in LM Studio
- [ ] Tests passing (`python -m pytest tests/test_agent_phase1b.py`)
- [ ] Phase 2 tests passing (`python -m pytest tests/test_dashboard_mvp.py`)
- [ ] Agent runs successfully (`python run_agent.py`)
- [ ] Dashboard accessible (`python dashboard/app.py`)
- [ ] Code quality checks pass (`ruff check . && ruff format --check --diff .`)

## 🎯 Next Steps

1. **Customize Configuration**: Edit `.env` file for your preferences
2. **Download Models**: Add more models to LM Studio for different capabilities
3. **Explore Tools**: Check `tools/mcp_schema.json` for available operations
4. **Extend Functionality**: Add custom tools or modify agent behavior
5. **Monitor Performance**: Use the dashboard to track metrics and performance
6. **Try Continuous Mode**: Experiment with autonomous execution for complex tasks
7. **Web Research**: Test the agent's web content extraction capabilities
8. **Security Features**: Explore the enhanced validation and safety features

## 🎉 Phase 2 Complete!

This release includes all Phase 2 features:
- ✅ **Internet Tooling**: Security-first web content extraction
- ✅ **Continuous Mode**: Autonomous execution with safety guardrails
- ✅ **Dashboard MVP**: Real-time metrics and performance monitoring
- ✅ **Enhanced Security**: GitHub token validation and environment sanity checks
- ✅ **Performance Benchmarking**: CI-integrated regression detection

---

**Need help?** The setup script (`./setup.sh`) will guide you through most of this process automatically! 