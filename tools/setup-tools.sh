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

# Smart test (auto-detects project type)
echo "Setting up smart-test..."
chmod +x "$SCRIPT_DIR/smart-test/test" "$SCRIPT_DIR/smart-test/smart-test.py"

echo ""
echo "Tools installed successfully!"
echo ""
echo "Usage:"
echo "  Smart test:   $SCRIPT_DIR/smart-test/test all /path/to/project"
echo "  Browser test: $SCRIPT_DIR/browser-test/test /path/to/index.html"
echo "  JS Lint:      $SCRIPT_DIR/lint/lint /path/to/file.js"
