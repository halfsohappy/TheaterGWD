#!/usr/bin/env bash
# Quick installer for running Gooey on an Ox64 board.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
PYTHON_BIN="${PYTHON:-python3}"

echo "[1/4] Checking for package manager (apt) to install Python + pip + git"
if command -v apt-get >/dev/null 2>&1; then
  if command -v sudo >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y python3 python3-venv python3-pip git
  else
    apt-get update
    apt-get install -y python3 python3-venv python3-pip git
  fi
else
  echo "apt-get not found; make sure python3 (3.8+), pip, and git are installed before continuing."
fi

echo "[2/4] Creating virtual environment at $VENV_DIR"
if [ ! -d "$VENV_DIR" ]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
else
  echo "Virtual environment already exists; reusing."
fi

echo "[3/4] Installing Gooey into the virtual environment"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip setuptools wheel
pip install "$REPO_ROOT/gooey"

echo "[4/4] Done."
echo "Run Gooey with:"
echo "  $VENV_DIR/bin/gooey --host 0.0.0.0 --port 5000 --no-browser"
echo
echo "If you want Gooey to start on boot, copy Ox64/gooey.service to ~/.config/systemd/user/,"
echo "adjust paths if needed, then run: systemctl --user enable --now gooey.service"
