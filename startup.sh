#!/bin/bash
# Minimal Biomni MCP Server Startup Script
# This script runs the server using the existing biomni_e1 environment

set -e  # Exit on error

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if .env file exists and suggest configuration if not
if [[ ! -f ".env" ]]; then
    echo "⚠️  No .env file found."
    if [[ -f ".env.template" ]]; then
        echo "📝 Creating .env from template..."
        cp ".env.template" ".env"
        echo "✅ Created .env file"
        echo ""
        echo "🔑 Please edit .env and add your ANTHROPIC_API_KEY"
        echo "   Then run this script again."
    else
        echo "❌ No .env.template found either"
        echo "   Please create .env with ANTHROPIC_API_KEY"
    fi
    exit 1
fi

# Check if the biomni_e1 environment exists
BIOMNI_PYTHON="/Users/jiehoonk/micromamba/envs/biomni_e1/bin/python"
if [[ ! -f "$BIOMNI_PYTHON" ]]; then
    echo "❌ Error: biomni_e1 environment not found at: $BIOMNI_PYTHON"
    echo ""
    echo "Please make sure the biomni_e1 micromamba environment is properly set up."
    exit 1
fi

# Check if required packages are available
echo "🔍 Checking biomni installation..."
if ! "$BIOMNI_PYTHON" -c "import biomni; print(f'✓ Biomni v{biomni.__version__} found')" 2>/dev/null; then
    echo "❌ Error: Biomni not found in biomni_e1 environment"
    echo "Please ensure Biomni is installed in the biomni_e1 environment"
    exit 1
fi

# Check for required dependencies
if ! "$BIOMNI_PYTHON" -c "import mcp; print('✓ MCP library found')" 2>/dev/null; then
    echo "❌ Error: MCP library not found"
    echo "Installing MCP library..."
    "$BIOMNI_PYTHON" -m pip install mcp
fi

if ! "$BIOMNI_PYTHON" -c "import dotenv; print('✓ python-dotenv found')" 2>/dev/null; then
    echo "❌ Error: python-dotenv not found"
    echo "Installing python-dotenv..."
    "$BIOMNI_PYTHON" -m pip install python-dotenv
fi

echo ""
echo "🚀 Starting Minimal Biomni MCP Server..."
echo "   Using: $BIOMNI_PYTHON"
echo "   Directory: $SCRIPT_DIR"
echo ""

# Run the server
exec "$BIOMNI_PYTHON" "$SCRIPT_DIR/server.py" "$@"