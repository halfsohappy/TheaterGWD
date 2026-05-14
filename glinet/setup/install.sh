#!/bin/sh
# TheaterGWD Gooey – GL.iNet Router Installer
# Run this via SSH on your GL.iNet router.

set -e

REPO_URL="https://github.com/halfsohappy/TheaterGWD"
GOOEY_SRC="/opt/theatergwd/gooey"
VENV="/opt/gooey-env"
INIT_SCRIPT="/etc/init.d/gooey"

echo ""
echo "  TheaterGWD Gooey – GL.iNet Installer"
echo "  ──────────────────────────────────────"
echo ""

# ── 1. System packages ──────────────────────────────────────────────────────

echo "[1/5] Installing system packages..."
opkg update
opkg install git-http python3 python3-pip python3-setuptools

# USB CDC-ACM so the router sees the Teensy as /dev/ttyACM0
opkg install kmod-usb-acm 2>/dev/null || true

# Load the module now without rebooting
modprobe cdc_acm 2>/dev/null || true

# ── 2. Clone repository ─────────────────────────────────────────────────────

echo "[2/5] Fetching TheaterGWD source..."

if [ -d "/opt/theatergwd/.git" ]; then
    echo "  Repository exists – pulling latest..."
    git -C /opt/theatergwd pull --ff-only
else
    git clone --depth=1 "$REPO_URL" /opt/theatergwd
fi

# ── 3. Python virtual environment ───────────────────────────────────────────

echo "[3/5] Setting up Python environment..."

if python3 -m venv --help >/dev/null 2>&1; then
    python3 -m venv "$VENV"
    PYTHON="$VENV/bin/python3"
    PIP="$VENV/bin/pip"
else
    PYTHON="$(command -v python3)"
    PIP="$(command -v pip3)"
fi

"$PIP" install --quiet --upgrade pip
"$PIP" install --quiet \
    "flask>=3.0" \
    "flask-socketio>=5.3" \
    "python-osc>=1.8" \
    "markdown>=3.7" \
    "pyserial>=3.5"

echo "  Python dependencies installed."

# ── 4. Service script ────────────────────────────────────────────────────────

echo "[4/5] Installing service..."

INIT_TEMPLATE="/opt/theatergwd/glinet/setup/gooey"

if [ ! -f "$INIT_TEMPLATE" ]; then
    echo "ERROR: Service template not found at $INIT_TEMPLATE"
    exit 1
fi

sed "s|__PYTHON__|$PYTHON|g; s|__GOOEY_SRC__|$GOOEY_SRC|g" \
    "$INIT_TEMPLATE" > "$INIT_SCRIPT"
chmod +x "$INIT_SCRIPT"
"$INIT_SCRIPT" enable
"$INIT_SCRIPT" start

# ── 5. Done ──────────────────────────────────────────────────────────────────

echo "[5/5] Done!"

# GL.iNet default LAN address
ROUTER_IP=$(uci get network.lan.ipaddr 2>/dev/null || echo "192.168.8.1")

echo ""
echo "  ✓ Gooey is running!"
echo ""
echo "  Open in browser:  http://$ROUTER_IP:5000"
echo ""
echo "  Teensy serial port: plug in the Teensy and it should appear"
echo "  as /dev/ttyACM0. Connect to it inside the Gooey interface."
echo ""
