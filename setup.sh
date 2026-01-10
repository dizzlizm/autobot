#!/bin/bash
# Aider + Gemini Overnight Automation Setup Script
# This script installs and configures Aider for use with the Gemini API

set -e

OVERNIGHT_DIR="$HOME/overnight"
CONFIG_DIR="$HOME/.config/aider"
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo_status() {
    echo -e "${GREEN}[+]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[!]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running on Ubuntu/Debian
check_system() {
    echo_status "Checking system requirements..."

    if ! command -v python3 &> /dev/null; then
        echo_error "Python3 is required but not installed."
        exit 1
    fi

    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    echo_status "Python version: $PYTHON_VERSION"

    if ! command -v git &> /dev/null; then
        echo_error "Git is required but not installed."
        exit 1
    fi

    if ! command -v pip3 &> /dev/null && ! command -v pipx &> /dev/null; then
        echo_warn "Neither pip3 nor pipx found. Installing pipx..."
        sudo apt-get update && sudo apt-get install -y pipx
        pipx ensurepath
    fi
}

# Install Aider using pipx (recommended) or pip
install_aider() {
    echo_status "Installing Aider..."

    if command -v pipx &> /dev/null; then
        echo_status "Using pipx for installation (recommended)..."
        pipx install aider-chat || pipx upgrade aider-chat
        # Install google-generativeai for Gemini support
        pipx inject aider-chat google-generativeai
    else
        echo_status "Using pip for installation..."
        pip3 install --user --upgrade aider-chat google-generativeai
    fi

    # Verify installation
    if command -v aider &> /dev/null; then
        AIDER_VERSION=$(aider --version 2>/dev/null || echo "unknown")
        echo_status "Aider installed successfully: $AIDER_VERSION"
    else
        echo_error "Aider installation failed. Please check the output above."
        exit 1
    fi
}

# Configure Gemini API
configure_gemini() {
    echo_status "Configuring Gemini API..."

    # Check if GEMINI_API_KEY is already set
    if [ -n "$GEMINI_API_KEY" ]; then
        echo_status "GEMINI_API_KEY already set in environment"
    else
        echo_warn "GEMINI_API_KEY not found in environment"
        read -p "Enter your Gemini API key (or press Enter to skip): " API_KEY

        if [ -n "$API_KEY" ]; then
            # Add to .bashrc if not already present
            if ! grep -q "GEMINI_API_KEY" ~/.bashrc 2>/dev/null; then
                echo "" >> ~/.bashrc
                echo "# Gemini API Key for Aider" >> ~/.bashrc
                echo "export GEMINI_API_KEY=\"$API_KEY\"" >> ~/.bashrc
                echo_status "Added GEMINI_API_KEY to ~/.bashrc"
            fi

            # Also create a .env file in overnight directory
            echo "GEMINI_API_KEY=$API_KEY" > "$OVERNIGHT_DIR/.env"
            chmod 600 "$OVERNIGHT_DIR/.env"
            echo_status "Created $OVERNIGHT_DIR/.env"

            export GEMINI_API_KEY="$API_KEY"
        else
            echo_warn "Skipping API key configuration. You'll need to set GEMINI_API_KEY manually."
        fi
    fi
}

# Create directory structure
create_directories() {
    echo_status "Creating directory structure..."

    mkdir -p "$OVERNIGHT_DIR/templates"
    mkdir -p "$OVERNIGHT_DIR/logs"
    mkdir -p "$HOME/reports"
    mkdir -p "$HOME/projects"
    mkdir -p "$CONFIG_DIR"

    echo_status "Directories created:"
    echo "  - $OVERNIGHT_DIR/templates"
    echo "  - $OVERNIGHT_DIR/logs"
    echo "  - $HOME/reports"
    echo "  - $HOME/projects"
}

# Create global aider config
create_aider_config() {
    echo_status "Creating global Aider configuration..."

    cat > "$CONFIG_DIR/.aider.conf.yml" << 'EOF'
# Global Aider Configuration
# This is loaded for all projects

# Model settings (use Gemini 2.5 Pro by default)
model: gemini

# Auto-commit settings
auto-commits: true
dirty-commits: true

# Don't stream output in scripts
stream: false

# Useful defaults
show-diffs: true
check-update: false
EOF

    echo_status "Created $CONFIG_DIR/.aider.conf.yml"
}

# Create shell aliases
create_aliases() {
    echo_status "Creating shell aliases..."

    ALIAS_BLOCK='
# Aider Overnight Automation aliases
alias overnight="python3 ~/overnight/overnight.py"
alias aider-gemini="aider --model gemini --yes"
alias aider-quick="aider --model gemini --yes --message"
'

    if ! grep -q "Aider Overnight" ~/.bashrc 2>/dev/null; then
        echo "$ALIAS_BLOCK" >> ~/.bashrc
        echo_status "Added aliases to ~/.bashrc"
    else
        echo_status "Aliases already exist in ~/.bashrc"
    fi

    # Also add to .zshrc if it exists
    if [ -f ~/.zshrc ]; then
        if ! grep -q "Aider Overnight" ~/.zshrc 2>/dev/null; then
            echo "$ALIAS_BLOCK" >> ~/.zshrc
            echo_status "Added aliases to ~/.zshrc"
        fi
    fi
}

# Verify Gemini connection
verify_gemini() {
    echo_status "Verifying Gemini API connection..."

    if [ -z "$GEMINI_API_KEY" ]; then
        echo_warn "GEMINI_API_KEY not set, skipping verification"
        return
    fi

    # Create a temporary test directory
    TEMP_DIR=$(mktemp -d)
    cd "$TEMP_DIR"
    git init -q
    echo "# Test" > README.md
    git add README.md
    git commit -q -m "Initial commit"

    # Test aider with a simple message
    echo_status "Testing Aider with Gemini (this may take a moment)..."
    if timeout 60 aider --model gemini --yes --message "Say 'Hello, Aider is working!' and nothing else" --no-auto-commits 2>&1 | grep -qi "hello"; then
        echo_status "Gemini API connection verified successfully!"
    else
        echo_warn "Could not verify Gemini connection. Please check your API key."
    fi

    # Cleanup
    cd -
    rm -rf "$TEMP_DIR"
}

# Print summary
print_summary() {
    echo ""
    echo "=============================================="
    echo "  Aider + Gemini Setup Complete!"
    echo "=============================================="
    echo ""
    echo "Quick Start:"
    echo "  # Interactive mode"
    echo "  cd ~/projects/your-project"
    echo "  aider --model gemini"
    echo ""
    echo "  # Single task (non-interactive)"
    echo "  aider --model gemini --yes --message 'Add a login feature'"
    echo ""
    echo "  # Overnight run"
    echo "  overnight --project ~/projects/your-project --tasks tasks.md"
    echo ""
    echo "Files created:"
    echo "  - $OVERNIGHT_DIR/overnight.py (main runner)"
    echo "  - $OVERNIGHT_DIR/templates/ (templates)"
    echo "  - $CONFIG_DIR/.aider.conf.yml (global config)"
    echo ""
    echo "Next steps:"
    echo "  1. Source your shell config: source ~/.bashrc"
    echo "  2. Create a project: mkdir ~/projects/my-app && cd ~/projects/my-app && git init"
    echo "  3. Add CONVENTIONS.md to your project for context"
    echo "  4. Create a tasks.md file with your overnight tasks"
    echo "  5. Run: overnight --project ~/projects/my-app --tasks tasks.md"
    echo ""
    echo "Model strings for reference:"
    echo "  - gemini          -> Gemini 2.5 Pro (default)"
    echo "  - gemini-exp      -> Gemini 2.5 Pro Experimental (free tier)"
    echo "  - gemini/gemini-2.5-flash -> Gemini 2.5 Flash (faster, cheaper)"
    echo ""
}

# Main
main() {
    echo "=============================================="
    echo "  Aider + Gemini Overnight Setup"
    echo "=============================================="
    echo ""

    check_system
    install_aider
    configure_gemini
    create_directories
    create_aider_config
    create_aliases

    # Optional verification
    read -p "Would you like to verify the Gemini connection? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        verify_gemini
    fi

    print_summary
}

main "$@"
