#!/usr/bin/env bash
# Aider + Ollama Overnight Automation Setup Script
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
    pip install aider-chat psutil

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
# STEP 5: Install and Configure Ollama
#------------------------------------------------------------------------------
configure_ollama() {
    echo_status "Setting up Ollama..."

    # Check if Ollama is already installed
    if command -v ollama &> /dev/null; then
        echo_status "Ollama already installed: $(ollama --version 2>/dev/null || echo 'installed')"
    else
        echo_status "Installing Ollama..."
        curl -fsSL https://ollama.com/install.sh | sh

        if command -v ollama &> /dev/null; then
            echo_status "Ollama installed successfully"
        else
            echo_error "Ollama installation failed"
            echo_warn "Install manually from: https://ollama.com/download"
        fi
    fi

    # Pull the default model (qwen2.5-coder:7b)
    echo_status "Pulling qwen2.5-coder:7b model (this may take a while)..."
    if ollama pull qwen2.5-coder:7b; then
        echo_status "Model qwen2.5-coder:7b ready"
    else
        echo_warn "Failed to pull model. Run manually: ollama pull qwen2.5-coder:7b"
    fi
}

#------------------------------------------------------------------------------
# STEP 6: Create Aider Config
#------------------------------------------------------------------------------
create_aider_config() {
    echo_status "Creating Aider configuration..."

    mkdir -p "$CONFIG_DIR"
    cat > "$CONFIG_DIR/.aider.conf.yml" << 'EOF'
model: ollama/qwen2.5-coder:7b
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
alias aider-ollama=\"$OVERNIGHT_DIR/aider --model ollama/qwen2.5-coder:7b --yes\"
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
    echo "  $OVERNIGHT_DIR/aider --model ollama/qwen2.5-coder:7b"
    echo ""
    echo "Overnight run:"
    echo "  $OVERNIGHT_DIR/run-overnight --project /path/to/project --tasks tasks.md"
    echo ""
    echo "Alternative models (change with --model):"
    echo "  ollama/codellama:7b        # Meta's coding model"
    echo "  ollama/deepseek-coder:6.7b # DeepSeek coding model"
    echo "  ollama/mistral:7b          # General purpose"
    echo ""
}

#------------------------------------------------------------------------------
# Main
#------------------------------------------------------------------------------
main() {
    echo "=============================================="
    echo "  Aider + Ollama Setup"
    echo "  Installing to: $OVERNIGHT_DIR"
    echo "=============================================="
    echo ""

    install_system_deps
    create_directories
    setup_venv_and_aider
    create_wrapper_scripts
    configure_ollama
    create_aider_config
    setup_shell
    verify_installation
    print_summary
}

main "$@"
