#!/bin/bash

# iKOMA AI Agent Setup Script for New Machines
# This script will configure your environment for the iKOMA AI agent

set -e  # Exit on any error

echo "🚀 iKOMA AI Agent Setup Script"
echo "================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're on macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    print_status "Detected macOS system"
else
    print_warning "This script is optimized for macOS. You may need to adapt some steps for your system."
fi

# Step 1: Check Python version
print_status "Checking Python version..."

# Try different Python versions in order of preference (3.11+ preferred)
PYTHON_CMD=""
for cmd in python3.11 python3.12 python3.13 python3.10 python3; do
    if command -v $cmd &> /dev/null; then
        PYTHON_VERSION=$($cmd --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
        
        if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 10 ]; then
            PYTHON_CMD=$cmd
            if [ "$PYTHON_MINOR" -ge 11 ]; then
                print_success "Python $PYTHON_VERSION found (recommended 3.11+)"
            else
                print_warning "Python $PYTHON_VERSION found (acceptable, but 3.11+ recommended)"
            fi
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    print_error "No Python 3.10+ found, but iKOMA requires Python 3.10+"
    echo ""
    echo "To install Python 3.10+ on macOS:"
    echo "1. Install Homebrew: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    echo "2. Install Python: brew install python@3.11"
    echo "3. Add to PATH: echo 'export PATH=\"/opt/homebrew/bin:\$PATH\"' >> ~/.zshrc"
    echo "4. Restart terminal or run: source ~/.zshrc"
    echo ""
    echo "Alternatively, download from: https://www.python.org/downloads/"
    exit 1
fi

# Step 2: Check if virtual environment exists
if [ -d "venv" ]; then
    print_status "Virtual environment already exists"
else
    print_status "Creating virtual environment..."
    $PYTHON_CMD -m venv venv
    print_success "Virtual environment created"
fi

# Step 3: Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate
print_success "Virtual environment activated"

# Step 4: Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip
print_success "Pip upgraded"

# Step 5: Install dependencies
print_status "Installing Python dependencies..."
pip install -r requirements.txt
print_success "Dependencies installed"

# Step 6: Check if .env file exists
if [ -f ".env" ]; then
    print_success "Environment file (.env) already exists"
else
    print_status "Creating environment file from template..."
    cp config.env.template .env
    print_success "Environment file created from template"
fi

# Step 7: Create necessary directories
print_status "Creating necessary directories..."
mkdir -p agent/memory/vector_store
mkdir -p agent/ikoma_sandbox
print_success "Directories created"

# Step 8: Check for LM Studio
print_status "Checking for LM Studio..."
if command -v lmstudio &> /dev/null; then
    print_success "LM Studio found in PATH"
else
    print_warning "LM Studio not found in PATH"
    echo ""
    echo "To install LM Studio:"
    echo "1. Download from: https://lmstudio.ai/"
    echo "2. Install the application"
    echo "3. Start LM Studio and configure a model"
    echo "4. Start the local server on port 11434"
fi

# Step 9: Run tests to verify setup
print_status "Running basic tests to verify setup..."
if python -c "import langchain, langgraph, chromadb" 2>/dev/null; then
    print_success "Core dependencies imported successfully"
else
    print_error "Failed to import core dependencies"
    exit 1
fi

# Step 9.5: Check TUI and Dashboard imports
print_status "Checking TUI and Dashboard components..."
if python -c "from agent.ui.tui import IkomaTUI; from dashboard.app import app" 2>/dev/null; then
    print_success "TUI and Dashboard components imported successfully"
else
    print_error "Failed to import TUI and Dashboard components"
    exit 1
fi

# Step 10: Check formatting
print_status "Checking code formatting..."
if command -v ruff &> /dev/null; then
    ruff format --check --diff . || print_warning "Code formatting issues found (run 'ruff format .' to fix)"
else
    print_warning "Ruff not found - install with: pip install ruff"
fi

echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo ""
echo "Next steps:"
echo "1. Configure your .env file with your preferences"
echo "2. Install and start LM Studio (https://lmstudio.ai/)"
echo "3. Download a compatible model in LM Studio"
echo "4. Start the local server on port 11434"
echo "5. Run the agent: python run_agent.py"
echo ""
echo "Configuration files:"
echo "- .env: Environment variables (edit as needed)"
echo "- agent/memory/: Persistent memory storage"
echo "- agent/ikoma_sandbox/: Safe file operations area"
echo ""
echo "For more information, see README.md"

# Deactivate virtual environment
deactivate 