#!/bin/bash
# Install systemd service and timer for overnight coding automation

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER_SYSTEMD_DIR="$HOME/.config/systemd/user"

echo "Installing overnight-coder systemd units..."

# Create user systemd directory
mkdir -p "$USER_SYSTEMD_DIR"

# Copy service file with user substitution
sed "s|%h|$HOME|g; s|%i|$USER|g" "$SCRIPT_DIR/overnight-coder.service" > "$USER_SYSTEMD_DIR/overnight-coder.service"
cp "$SCRIPT_DIR/overnight-coder.timer" "$USER_SYSTEMD_DIR/overnight-coder.timer"

# Reload systemd
systemctl --user daemon-reload

echo ""
echo "Systemd units installed!"
echo ""
echo "Usage:"
echo "  # Enable the timer (starts at 11 PM daily)"
echo "  systemctl --user enable overnight-coder.timer"
echo "  systemctl --user start overnight-coder.timer"
echo ""
echo "  # Check timer status"
echo "  systemctl --user status overnight-coder.timer"
echo "  systemctl --user list-timers"
echo ""
echo "  # Run manually (one-time)"
echo "  systemctl --user start overnight-coder.service"
echo ""
echo "  # View logs"
echo "  journalctl --user -u overnight-coder.service"
echo ""
echo "IMPORTANT: Edit the service file to set your project path:"
echo "  nano $USER_SYSTEMD_DIR/overnight-coder.service"
echo ""
echo "Change the ExecStart line to point to your project and tasks file."
