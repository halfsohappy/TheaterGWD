#!/usr/bin/env bash
# setup.sh — Install and configure Symon on Raspberry Pi OS (Bookworm)
#
# Run as root (or with sudo) on a freshly-flashed Raspberry Pi OS Lite or
# Raspberry Pi OS Desktop image:
#
#   sudo bash setup.sh
#
# What this script does:
#   1. Updates apt and installs system dependencies
#   2. Creates /home/pi/audio and /home/pi/symon
#   3. Copies symon.py and symon.service from this directory
#   4. Installs Python dependencies via pip
#   5. Installs and enables the systemd service
#
# After running, place .wav/.mp3/.ogg files in /home/pi/audio and reboot
# (or run: sudo systemctl start symon).

set -euo pipefail

PI_HOME="/home/pi"
SYMON_DIR="$PI_HOME/symon"
AUDIO_DIR="$PI_HOME/audio"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── 1. System packages ───────────────────────────────────────────────────────
echo "[setup] Updating package lists..."
apt-get update -qq

echo "[setup] Installing dependencies..."
apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-pygame \
    alsa-utils \
    libasound2-plugins

# ── 2. Create directories ────────────────────────────────────────────────────
echo "[setup] Creating directories..."
install -d -o pi -g pi -m 755 "$SYMON_DIR"
install -d -o pi -g pi -m 755 "$AUDIO_DIR"

# ── 3. Copy service files ────────────────────────────────────────────────────
echo "[setup] Copying symon.py..."
install -o pi -g pi -m 644 "$SCRIPT_DIR/symon.py" "$SYMON_DIR/symon.py"

# ── 4. Install Python dependencies ──────────────────────────────────────────
# Use a virtual environment so pip does not conflict with system packages.
# --system-site-packages gives the venv access to python3-pygame installed
# via apt without needing to reinstall it inside the venv.
echo "[setup] Creating virtual environment..."
sudo -u pi python3 -m venv --system-site-packages "$SYMON_DIR/venv"

echo "[setup] Installing Python packages into venv..."
"$SYMON_DIR/venv/bin/pip" install --quiet -r "$SCRIPT_DIR/requirements.txt"

# ── 5. Install systemd service ───────────────────────────────────────────────
echo "[setup] Installing systemd service..."
install -o root -g root -m 644 "$SCRIPT_DIR/symon.service" /etc/systemd/system/symon.service

systemctl daemon-reload
systemctl enable symon.service

echo ""
echo "✓ Symon installed successfully."
echo ""
echo "  Audio files go in : $AUDIO_DIR"
echo "  OSC listen port   : 8000 (UDP)"
echo ""
echo "  Start now  : sudo systemctl start symon"
echo "  Check logs : journalctl -u symon -f"
echo ""
echo "  To customize the port or reply host, edit:"
echo "    /etc/systemd/system/symon.service"
echo "  then run: sudo systemctl daemon-reload && sudo systemctl restart symon"
