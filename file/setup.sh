#!/bin/bash
# One-time setup script for secauto automation.
# Run this ONCE with: sudo bash setup.sh
# After this, scheduled updates run automatically without password prompts.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="/opt/secauto"
SUDOERS_FILE="/etc/sudoers.d/secauto"

echo "=============================================="
echo "  secauto - One-Time Setup"
echo "=============================================="

# Must run as root
if [ "$(id -u)" -ne 0 ]; then
    echo "Error: This script must be run as root (sudo bash setup.sh)"
    exit 1
fi

# 1. Install to /opt/secauto
echo "[1/4] Installing secauto to $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"
cp -r "$SCRIPT_DIR/automation" "$INSTALL_DIR/"
cp -r "$SCRIPT_DIR/systemd" "$INSTALL_DIR/"
if [ -f "$SCRIPT_DIR/secauto" ]; then
    cp "$SCRIPT_DIR/secauto" "$INSTALL_DIR/"
fi
chmod +x "$INSTALL_DIR/automation/"*.py 2>/dev/null || true

# 2. Create log directory
echo "[2/4] Creating log directory..."
mkdir -p /var/log/secauto
chmod 755 /var/log/secauto

# 3. Set up passwordless sudo for apt commands (for manual runs)
echo "[3/4] Configuring passwordless sudo for apt commands..."
cat > "$SUDOERS_FILE" << 'EOF'
# Allow secauto to run apt-get commands without password
# This enables the automation to work without interactive prompts
ALL ALL=(root) NOPASSWD: /usr/bin/apt-get update
ALL ALL=(root) NOPASSWD: /usr/bin/apt-get upgrade *
ALL ALL=(root) NOPASSWD: /usr/bin/apt-get full-upgrade *
ALL ALL=(root) NOPASSWD: /usr/bin/apt-get autoremove *
ALL ALL=(root) NOPASSWD: /usr/bin/apt-get autoclean *
ALL ALL=(root) NOPASSWD: /usr/bin/systemctl daemon-reload
ALL ALL=(root) NOPASSWD: /usr/bin/systemctl enable *secauto*
ALL ALL=(root) NOPASSWD: /usr/bin/systemctl disable *secauto*
ALL ALL=(root) NOPASSWD: /usr/bin/systemctl start *secauto*
ALL ALL=(root) NOPASSWD: /usr/bin/systemctl stop *secauto*
ALL ALL=(root) NOPASSWD: /usr/bin/systemctl list-timers *
ALL ALL=(root) NOPASSWD: /usr/bin/install -m 0644 * /etc/systemd/system/*
EOF
chmod 440 "$SUDOERS_FILE"
echo "   Created $SUDOERS_FILE"

# 4. Install and enable systemd timer
echo "[4/4] Installing systemd timer..."
cp "$INSTALL_DIR/systemd/secauto-update.service" /etc/systemd/system/
cp "$INSTALL_DIR/systemd/secauto-update.timer" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now secauto-update.timer

echo ""
echo "=============================================="
echo "  Setup Complete!"
echo "=============================================="
echo ""
echo "The automation is now active. Updates will run:"
echo "  - First run: 10 minutes after boot"
echo "  - Then: Every 7 hours"
echo ""
echo "Check status:    systemctl list-timers secauto-update.timer"
echo "View logs:       cat /var/log/secauto/update.log"
echo "Disable:         systemctl disable --now secauto-update.timer"
echo "Manual run:      python3 $INSTALL_DIR/automation/secauto.py update"
echo ""
