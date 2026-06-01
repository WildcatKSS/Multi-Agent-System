#!/bin/bash
# Multi-Agent System - Automated Installation Script
#
# Usage: ./install.sh [--with-redis]
#
# This script handles complete installation for development or production.
# Optional: pass --with-redis to also start Redis server

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
WITH_REDIS=false

# Parse arguments
if [[ "$1" == "--with-redis" ]]; then
    WITH_REDIS=true
fi

echo "🚀 Multi-Agent System Installation"
echo "===================================="
echo ""

# Check Python version
echo "📋 Checking Python 3.12+ availability..."
if ! command -v python3.12 &> /dev/null; then
    echo "❌ Python 3.12 is required but not installed."
    echo "   Please install Python 3.12 or later and try again."
    exit 1
fi
PYTHON_VERSION=$(python3.12 --version)
echo "✅ Found $PYTHON_VERSION"
echo ""

# Create virtual environment
echo "📦 Creating virtual environment..."
if [ -d "$VENV_DIR" ]; then
    echo "   Virtual environment already exists at $VENV_DIR"
    read -p "   Recreate it? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$VENV_DIR"
        python3.12 -m venv "$VENV_DIR"
        echo "✅ Created new virtual environment"
    fi
else
    python3.12 -m venv "$VENV_DIR"
    echo "✅ Created virtual environment at $VENV_DIR"
fi
echo ""

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source "$VENV_DIR/bin/activate"
echo "✅ Virtual environment activated"
echo ""

# Upgrade pip
echo "🔄 Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1
echo "✅ pip upgraded"
echo ""

# Install package with dependencies
echo "📥 Installing package with dependencies..."
if [ "$WITH_REDIS" = true ]; then
    pip install -e ".[dev,memory]" > /dev/null 2>&1
    echo "✅ Installed with dev + memory (Redis) dependencies"
else
    pip install -e ".[dev]" > /dev/null 2>&1
    echo "✅ Installed with dev dependencies"
fi
echo ""

# Optional: Start Redis if requested
if [ "$WITH_REDIS" = true ]; then
    echo "🔴 Checking Redis..."
    if command -v redis-server &> /dev/null; then
        if ! redis-cli ping > /dev/null 2>&1; then
            echo "   Starting Redis server..."
            redis-server --daemonize yes > /dev/null 2>&1
            sleep 1
            if redis-cli ping > /dev/null 2>&1; then
                echo "✅ Redis server started"
            else
                echo "⚠️  Could not start Redis. Working memory will operate in no-op mode."
            fi
        else
            echo "✅ Redis server is already running"
        fi
    else
        echo "⚠️  Redis is not installed. To use working memory in production:"
        echo "   Ubuntu: sudo apt-get install redis-server"
        echo "   macOS:  brew install redis"
        echo "   Working memory will operate in no-op mode (dev/testing)."
    fi
    echo ""
fi

# Verify installation
echo "✅ Running verification tests..."
if python -m pytest tests/ -q --tb=no > /dev/null 2>&1; then
    TEST_COUNT=$(python -m pytest tests/ --collect-only -q 2>/dev/null | tail -1 | grep -oE '[0-9]+' | head -1)
    echo "✅ All $TEST_COUNT tests passed!"
else
    echo "⚠️  Some tests failed. Check with: pytest -v"
fi
echo ""

# Summary
echo "════════════════════════════════════════════════════════"
echo "✅ Installation Complete!"
echo "════════════════════════════════════════════════════════"
echo ""
echo "📝 Next Steps:"
echo ""
echo "1️⃣  Activate the virtual environment (if not already active):"
echo "   source venv/bin/activate"
echo ""
echo "2️⃣  Run the agent system:"
echo "   mas run"
echo ""
echo "3️⃣  Run tests:"
echo "   pytest -v"
echo ""
echo "4️⃣  Check CLI:"
echo "   mas --version"
echo ""
if [ "$WITH_REDIS" = false ]; then
    echo "💡 Tip: For production with Redis working memory, install again with:"
    echo "   ./install.sh --with-redis"
    echo ""
fi
echo "📚 Documentation:"
echo "   - INSTALL.md     (detailed system requirements)"
echo "   - README.md      (project overview)"
echo "   - docs/roadmap.md (milestone plan)"
echo ""
