#!/bin/bash

# Script to establish new performance baselines for Ikoma agent
# This should be run when performance improvements are made or when
# the baseline becomes outdated due to legitimate changes.

set -e

echo "🎯 Establishing new performance baseline for Ikoma agent"
echo "======================================================"

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# Install dependencies if needed
if [ ! -d "venv" ] && [ ! -d ".venv" ]; then
    echo "📦 Setting up virtual environment..."
    python -m venv venv
    source venv/bin/activate
    pip install -e .
    pip install matplotlib
else
    echo "✅ Virtual environment found"
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Run benchmarks and save baseline
echo "🚀 Running performance benchmarks..."
python -m benchmarks.bench --save-baseline

echo ""
echo "✅ New baseline established!"
echo "📊 Baseline data saved to: benchmarks/baselines.json"
echo ""
echo "💡 Tips:"
echo "  - Run 'python -m benchmarks.bench' to test against this baseline"
echo "  - The CI will automatically check for regressions on PRs"
echo "  - Re-run this script when making performance improvements" 