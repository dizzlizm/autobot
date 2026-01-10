#!/usr/bin/env bash
# Aider + Gemini Overnight Automation Setup Script
# Installs everything in the directory where this script lives

# Ensure we're running in bash, not sh
if [ -z "$BASH_VERSION" ]; then
    echo "Error: This script must be run with bash, not sh"
    echo "Run it with: bash $0"
    exit 1
fi

set -e

# Use the directory where this script is located as the base
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OVERNIGHT_DIR="$SCRIPT_DIR"
VENV_DIR="$OVERNIGHT_DIR/venv"
CONFIG_DIR="$HOME/.config/aider"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo_status() { echo -e "${GREEN}[+]${NC} $1"; }
echo_warn() { echo -e "${YELLOW}[!]${NC} $1"; }
echo_error() { echo -e "${RED}[ERROR]${NC} $1"; }

#------------------------------------------------------------------------------
# STEP 1: Install System Dependencies
#------------------------------------------------------------------------------
install_system_deps() {
    echo_status "Installing system dependencies..."
    sudo apt-get update
    sudo apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        git \
        curl \
        build-essential \
        libffi-dev \
        libssl-dev

    echo_status "System dependencies installed"
    python3 --version
    git --version
}

#------------------------------------------------------------------------------
# STEP 2: Create Directory Structure (all inside script directory)
#------------------------------------------------------------------------------
create_directories() {
    echo_status "Creating directory structure in $OVERNIGHT_DIR ..."
    mkdir -p "$OVERNIGHT_DIR/templates"
    mkdir -p "$OVERNIGHT_DIR/logs"
    mkdir -p "$OVERNIGHT_DIR/reports"
    mkdir -p "$OVERNIGHT_DIR/projects"
    mkdir -p "$CONFIG_DIR"
    echo_status "Directories created"
}

#------------------------------------------------------------------------------
# STEP 3: Create Python Virtual Environment and Install Aider
#------------------------------------------------------------------------------
setup_venv_and_aider() {
    echo_status "Setting up Python virtual environment at $VENV_DIR ..."

    if [ ! -d "$VENV_DIR" ]; then
        python3 -m venv "$VENV_DIR"
        echo_status "Created virtual environment"
    else
        echo_status "Virtual environment already exists"
    fi

    . "$VENV_DIR/bin/activate"

    echo_status "Upgrading pip..."
    pip install --upgrade pip

    echo_status "Installing Aider (this may take a few minutes)..."
    pip install aider-chat google-generativeai psutil

    if command -v aider &> /dev/null; then
        AIDER_VERSION=$(aider --version 2>/dev/null || echo "installed")
        echo_status "Aider installed: $AIDER_VERSION"
    else
        echo_error "Aider installation failed"
        exit 1
    fi

    deactivate
}

#------------------------------------------------------------------------------
# STEP 4: Create Wrapper Scripts
#------------------------------------------------------------------------------
create_wrapper_scripts() {
    echo_status "Creating wrapper scripts..."

    cat > "$OVERNIGHT_DIR/aider" << EOF
#!/bin/bash
. "$VENV_DIR/bin/activate"
exec aider "\$@"
EOF
    chmod +x "$OVERNIGHT_DIR/aider"

    cat > "$OVERNIGHT_DIR/run-overnight" << EOF
#!/bin/bash
. "$VENV_DIR/bin/activate"
exec python3 "$OVERNIGHT_DIR/overnight.py" "\$@"
EOF
    chmod +x "$OVERNIGHT_DIR/run-overnight"

    echo_status "Created wrapper scripts"
}

#------------------------------------------------------------------------------
# STEP 5: Configure Gemini API
#------------------------------------------------------------------------------
configure_gemini() {
    echo_status "Configuring Gemini API..."

    if [ -n "$GEMINI_API_KEY" ]; then
        echo_status "GEMINI_API_KEY already set"
    else
        echo_warn "GEMINI_API_KEY not found"
        echo ""
        echo "Get a free API key at: https://aistudio.google.com/app/apikey"
        echo ""
        read -p "Enter your Gemini API key (or press Enter to skip): " API_KEY

        if [ -n "$API_KEY" ]; then
            if ! grep -q "GEMINI_API_KEY" ~/.bashrc 2>/dev/null; then
                echo "" >> ~/.bashrc
                echo "# Gemini API Key for Aider" >> ~/.bashrc
                echo "export GEMINI_API_KEY=\"$API_KEY\"" >> ~/.bashrc
                echo_status "Added GEMINI_API_KEY to ~/.bashrc"
            fi

            echo "GEMINI_API_KEY=$API_KEY" > "$OVERNIGHT_DIR/.env"
            chmod 600 "$OVERNIGHT_DIR/.env"
            export GEMINI_API_KEY="$API_KEY"
        else
            echo_warn "Skipping API key. Set GEMINI_API_KEY manually later."
        fi
    fi
}

#------------------------------------------------------------------------------
# STEP 6: Create Aider Config
#------------------------------------------------------------------------------
create_aider_config() {
    echo_status "Creating Aider configuration..."

    mkdir -p "$CONFIG_DIR"
    cat > "$CONFIG_DIR/.aider.conf.yml" << 'EOF'
model: gemini
auto-commits: true
dirty-commits: true
stream: false
show-diffs: true
check-update: false
EOF

    echo_status "Created $CONFIG_DIR/.aider.conf.yml"
}

#------------------------------------------------------------------------------
# STEP 7: Add to PATH
#------------------------------------------------------------------------------
setup_shell() {
    echo_status "Setting up shell environment..."

    SHELL_BLOCK="
# Aider Overnight Automation
export PATH=\"$OVERNIGHT_DIR:\$PATH\"
alias overnight=\"$OVERNIGHT_DIR/run-overnight\"
alias aider-gemini=\"$OVERNIGHT_DIR/aider --model gemini --yes\"
"

    if ! grep -q "Aider Overnight" ~/.bashrc 2>/dev/null; then
        echo "$SHELL_BLOCK" >> ~/.bashrc
        echo_status "Added to ~/.bashrc"
    else
        echo_status "Already in ~/.bashrc"
    fi
}

#------------------------------------------------------------------------------
# STEP 8: Verify Installation
#------------------------------------------------------------------------------
verify_installation() {
    echo_status "Verifying installation..."
    . "$VENV_DIR/bin/activate"

    if ! command -v aider &> /dev/null; then
        echo_error "Aider not found"
        exit 1
    fi

    if ! python3 -c "import psutil" 2>/dev/null; then
        echo_error "psutil not installed"
        exit 1
    fi

    echo_status "All components verified"
    deactivate
}

#------------------------------------------------------------------------------
# Print Summary
#------------------------------------------------------------------------------
print_summary() {
    echo ""
    echo "=============================================="
    echo "  Setup Complete!"
    echo "=============================================="
    echo ""
    echo "Everything installed in: $OVERNIGHT_DIR"
    echo ""
    echo "Run this to load settings:"
    echo "  source ~/.bashrc"
    echo ""
    echo "Quick test:"
    echo "  cd $OVERNIGHT_DIR/projects"
    echo "  mkdir test && cd test && git init"
    echo "  $OVERNIGHT_DIR/aider --model gemini"
    echo ""
    echo "Overnight run:"
    echo "  $OVERNIGHT_DIR/run-overnight --project /path/to/project --tasks tasks.md"
    echo ""
}

#------------------------------------------------------------------------------
# Main
#------------------------------------------------------------------------------
main() {
    echo "=============================================="
    echo "  Aider + Gemini Setup"
    echo "  Installing to: $OVERNIGHT_DIR"
    echo "=============================================="
    echo ""

    install_system_deps
    create_directories
    setup_venv_and_aider
    create_wrapper_scripts
    configure_gemini
    create_aider_config
    setup_shell
    verify_installation
    print_summary
}

main "$@"
