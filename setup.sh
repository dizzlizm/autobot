#!/bin/bash
# Aider + Gemini Overnight Automation Setup Script
# This script installs EVERYTHING needed on a fresh Ubuntu machine

set -e

OVERNIGHT_DIR="$HOME/overnight"
VENV_DIR="$OVERNIGHT_DIR/venv"
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

#------------------------------------------------------------------------------
# STEP 1: Install System Dependencies
#------------------------------------------------------------------------------
install_system_deps() {
    echo_status "Installing system dependencies..."

    # Update package list
    sudo apt-get update

    # Install Python 3, pip, venv, git, and other essentials
    sudo apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        git \
        curl \
        wget \
        build-essential \
        libffi-dev \
        libssl-dev

    # Verify installations
    echo_status "Verifying installations..."
    python3 --version
    pip3 --version
    git --version

    echo_status "System dependencies installed successfully"
}

#------------------------------------------------------------------------------
# STEP 2: Create Directory Structure
#------------------------------------------------------------------------------
create_directories() {
    echo_status "Creating directory structure..."

    mkdir -p "$OVERNIGHT_DIR/templates"
    mkdir -p "$OVERNIGHT_DIR/logs"
    mkdir -p "$OVERNIGHT_DIR/systemd"
    mkdir -p "$HOME/reports"
    mkdir -p "$HOME/projects"
    mkdir -p "$CONFIG_DIR"

    echo_status "Directories created:"
    echo "  - $OVERNIGHT_DIR"
    echo "  - $HOME/reports"
    echo "  - $HOME/projects"
}

#------------------------------------------------------------------------------
# STEP 3: Create Python Virtual Environment and Install Aider
#------------------------------------------------------------------------------
setup_venv_and_aider() {
    echo_status "Setting up Python virtual environment..."

    # Create venv if it doesn't exist
    if [ ! -d "$VENV_DIR" ]; then
        python3 -m venv "$VENV_DIR"
        echo_status "Created virtual environment at $VENV_DIR"
    else
        echo_status "Virtual environment already exists"
    fi

    # Activate venv
    source "$VENV_DIR/bin/activate"

    # Upgrade pip
    echo_status "Upgrading pip..."
    pip install --upgrade pip

    # Install aider and google-generativeai
    echo_status "Installing Aider (this may take a few minutes)..."
    pip install aider-chat google-generativeai psutil

    # Verify aider installation
    if command -v aider &> /dev/null; then
        AIDER_VERSION=$(aider --version 2>/dev/null || echo "installed")
        echo_status "Aider installed successfully: $AIDER_VERSION"
    else
        echo_error "Aider installation failed"
        exit 1
    fi

    deactivate
}

#------------------------------------------------------------------------------
# STEP 4: Create Wrapper Scripts (so you don't need to activate venv manually)
#------------------------------------------------------------------------------
create_wrapper_scripts() {
    echo_status "Creating wrapper scripts..."

    # Create aider wrapper
    cat > "$OVERNIGHT_DIR/aider" << EOF
#!/bin/bash
# Wrapper script to run aider from the virtual environment
source "$VENV_DIR/bin/activate"
exec aider "\$@"
EOF
    chmod +x "$OVERNIGHT_DIR/aider"

    # Create overnight wrapper
    cat > "$OVERNIGHT_DIR/run-overnight" << EOF
#!/bin/bash
# Wrapper script to run overnight.py from the virtual environment
source "$VENV_DIR/bin/activate"
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

    # Check if GEMINI_API_KEY is already set
    if [ -n "$GEMINI_API_KEY" ]; then
        echo_status "GEMINI_API_KEY already set in environment"
    else
        echo_warn "GEMINI_API_KEY not found in environment"
        echo ""
        echo "You need a Gemini API key. Get one free at:"
        echo "  https://aistudio.google.com/app/apikey"
        echo ""
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
            echo_warn "Skipping API key configuration."
            echo_warn "You'll need to set GEMINI_API_KEY manually before using Aider."
        fi
    fi
}

#------------------------------------------------------------------------------
# STEP 6: Create Global Aider Config
#------------------------------------------------------------------------------
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

#------------------------------------------------------------------------------
# STEP 7: Add to PATH and Create Aliases
#------------------------------------------------------------------------------
setup_shell() {
    echo_status "Setting up shell environment..."

    SHELL_BLOCK="
# Aider Overnight Automation
export PATH=\"\$HOME/overnight:\$PATH\"
alias overnight=\"\$HOME/overnight/run-overnight\"
alias aider-gemini=\"\$HOME/overnight/aider --model gemini --yes\"
alias aider-quick=\"\$HOME/overnight/aider --model gemini --yes --message\"
"

    if ! grep -q "Aider Overnight" ~/.bashrc 2>/dev/null; then
        echo "$SHELL_BLOCK" >> ~/.bashrc
        echo_status "Added PATH and aliases to ~/.bashrc"
    else
        echo_status "Shell config already exists in ~/.bashrc"
    fi

    # Also add to .zshrc if it exists
    if [ -f ~/.zshrc ]; then
        if ! grep -q "Aider Overnight" ~/.zshrc 2>/dev/null; then
            echo "$SHELL_BLOCK" >> ~/.zshrc
            echo_status "Added PATH and aliases to ~/.zshrc"
        fi
    fi
}

#------------------------------------------------------------------------------
# STEP 8: Verify Installation
#------------------------------------------------------------------------------
verify_installation() {
    echo_status "Verifying installation..."

    # Activate and test
    source "$VENV_DIR/bin/activate"

    # Check aider
    if ! command -v aider &> /dev/null; then
        echo_error "Aider not found in PATH"
        exit 1
    fi

    # Check psutil (needed for overnight.py)
    if ! python3 -c "import psutil" 2>/dev/null; then
        echo_error "psutil not installed"
        exit 1
    fi

    echo_status "All components verified"
    deactivate
}

#------------------------------------------------------------------------------
# STEP 9: Test Gemini Connection (Optional)
#------------------------------------------------------------------------------
test_gemini() {
    echo_status "Testing Gemini API connection..."

    if [ -z "$GEMINI_API_KEY" ]; then
        echo_warn "GEMINI_API_KEY not set, skipping test"
        return
    fi

    # Create a temporary test directory
    TEMP_DIR=$(mktemp -d)
    cd "$TEMP_DIR"
    git init -q
    git config user.email "test@test.com"
    git config user.name "Test"
    echo "# Test" > README.md
    git add README.md
    git commit -q -m "Initial commit"

    # Activate venv and test
    source "$VENV_DIR/bin/activate"

    echo_status "Sending test request to Gemini (this may take a moment)..."
    if timeout 120 aider --model gemini --yes --no-auto-commits --message "Reply with exactly: AIDER_TEST_OK" 2>&1 | grep -q "AIDER_TEST_OK\|OK\|working"; then
        echo_status "Gemini API connection verified!"
    else
        echo_warn "Could not verify Gemini connection. Check your API key."
        echo_warn "You can test manually with: aider --model gemini"
    fi

    deactivate

    # Cleanup
    cd "$HOME"
    rm -rf "$TEMP_DIR"
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
    echo "IMPORTANT: Run this to load the new settings:"
    echo "  source ~/.bashrc"
    echo ""
    echo "Quick Start:"
    echo ""
    echo "  # Test aider interactively"
    echo "  cd ~/projects/my-app"
    echo "  git init"
    echo "  ~/overnight/aider --model gemini"
    echo ""
    echo "  # Single task (non-interactive)"
    echo "  ~/overnight/aider --model gemini --yes -m 'Add hello world'"
    echo ""
    echo "  # Overnight run"
    echo "  ~/overnight/run-overnight --project ~/projects/my-app --tasks tasks.md"
    echo ""
    echo "Files:"
    echo "  $OVERNIGHT_DIR/aider         - Aider wrapper (uses venv)"
    echo "  $OVERNIGHT_DIR/run-overnight - Overnight runner wrapper"
    echo "  $OVERNIGHT_DIR/overnight.py  - Main overnight script"
    echo "  $OVERNIGHT_DIR/venv/         - Python virtual environment"
    echo ""
    echo "Next steps:"
    echo "  1. source ~/.bashrc"
    echo "  2. Create a test project:"
    echo "     mkdir -p ~/projects/test && cd ~/projects/test && git init"
    echo "  3. Test aider:"
    echo "     ~/overnight/aider --model gemini"
    echo ""
}

#------------------------------------------------------------------------------
# Main
#------------------------------------------------------------------------------
main() {
    echo "=============================================="
    echo "  Aider + Gemini Overnight Setup"
    echo "  For Fresh Ubuntu Installation"
    echo "=============================================="
    echo ""

    # Run all setup steps
    install_system_deps
    create_directories
    setup_venv_and_aider
    create_wrapper_scripts
    configure_gemini
    create_aider_config
    setup_shell
    verify_installation

    # Optional: Test Gemini connection
    if [ -n "$GEMINI_API_KEY" ]; then
        read -p "Would you like to test the Gemini API connection? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            test_gemini
        fi
    fi

    print_summary
}

main "$@"
