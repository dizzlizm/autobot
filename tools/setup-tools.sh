#!/bin/bash
# Install dependencies for all tools

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Setting up testing tools..."

# Browser test tool
echo "Installing browser-test dependencies..."
cd "$SCRIPT_DIR/browser-test"
npm install
chmod +x test test-html.js

# Lint tool
echo "Installing lint dependencies..."
cd "$SCRIPT_DIR/lint"
npm install
chmod +x lint lint-js.js

# MCP Test Server
echo "Installing MCP test server dependencies..."
cd "$SCRIPT_DIR/mcp-test-server"
npm install
chmod +x server.js

echo ""
echo "Tools installed successfully!"
echo ""
echo "Usage:"
echo "  Browser test: $SCRIPT_DIR/browser-test/test /path/to/index.html"
echo "  JS Lint:      $SCRIPT_DIR/lint/lint /path/to/file.js"
echo "  MCP Server:   node $SCRIPT_DIR/mcp-test-server/server.js"
echo ""
echo "MCP Server Configuration:"
echo "  Add to your MCP client config to use intelligent testing tools"
