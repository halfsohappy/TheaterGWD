#!/bin/sh
# TheaterGWD Gooey – Ox64 Installer
# Run this on the Ox64 after WiFi is connected.

set -e

REPO_URL="https://github.com/halfsohappy/TheaterGWD"
GOOEY_SRC="/opt/theatergwd/gooey"
VENV="/opt/gooey-env"
INIT_SCRIPT="/etc/init.d/gooey"

echo ""
echo "  TheaterGWD Gooey – Ox64 Installer"
echo "  ──────────────────────────────────"
echo ""

# ── 1. System packages ──────────────────────────────────────────────────────

echo "[1/5] Installing system packages..."

if command -v opkg >/dev/null 2>&1; then
    opkg update
    opkg install git-http python3 python3-pip python3-setuptools python3-venv \
        || opkg install git-http python3 python3-pip python3-setuptools
elif command -v apt-get >/dev/null 2>&1; then
    apt-get update -q
    apt-get install -y git python3 python3-pip python3-venv
elif command -v apk >/dev/null 2>&1; then
    apk add git python3 py3-pip
else
    echo "ERROR: No supported package manager found (opkg / apt / apk)."
    exit 1
fi

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

# Try venv first; fall back to plain pip if venv module is unavailable
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
    "markdown>=3.7"

echo "  Python dependencies installed."

# ── 4. Service script ────────────────────────────────────────────────────────

echo "[4/5] Installing system service..."

INIT_TEMPLATE="/opt/theatergwd/ox64/setup/gooey"

if [ ! -f "$INIT_TEMPLATE" ]; then
    echo "ERROR: Service template not found at $INIT_TEMPLATE"
    exit 1
fi

# Patch the Python path into the service script
sed "s|__PYTHON__|$PYTHON|g; s|__GOOEY_SRC__|$GOOEY_SRC|g" \
    "$INIT_TEMPLATE" > "$INIT_SCRIPT"

chmod +x "$INIT_SCRIPT"

if command -v systemctl >/dev/null 2>&1; then
    # systemd path – install the unit file instead
    UNIT_SRC="/opt/theatergwd/ox64/setup/gooey.service"
    sed "s|__PYTHON__|$PYTHON|g; s|__GOOEY_SRC__|$GOOEY_SRC|g" \
        "$UNIT_SRC" > /etc/systemd/system/gooey.service
    systemctl daemon-reload
    systemctl enable gooey
    systemctl start gooey
elif command -v /etc/rc.common >/dev/null 2>&1 || [ -d /etc/init.d ]; then
    # OpenWRT procd path
    "$INIT_SCRIPT" enable
    "$INIT_SCRIPT" start
fi

# ── 5. Done ──────────────────────────────────────────────────────────────────

echo "[5/5] Finishing up..."

# Detect the device's IP on the most likely interface
IP=$(ip addr show 2>/dev/null \
    | grep 'inet ' \
    | grep -v '127\.0\.0\.1' \
    | awk '{print $2}' \
    | cut -d/ -f1 \
    | head -1)

echo ""
echo "  ✓ Installation complete!"
echo ""
if [ -n "$IP" ]; then
    echo "  Open Gooey at:  http://$IP:5000"
else
    echo "  Open Gooey at:  http://<ox64-ip>:5000"
    echo "  (Run 'ip addr' to find your Ox64's IP address)"
fi
echo ""
