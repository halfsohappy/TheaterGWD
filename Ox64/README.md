# Gooey on Ox64 (Allwinner D1s / RISC-V)

This guide gets the Gooey Control Center running on a Sipeed Lichee **Ox64** (Allwinner D1s, RISC-V) using its Linux images (Armbian/Debian based). Everything is headless-friendly and bound to `0.0.0.0` so you can reach the UI from another machine on your network.

## What you'll build
- Gooey running in a Python virtual environment
- Optional **systemd user service** that auto-starts on boot
- Network access at `http://<ox64-ip>:5000`

## 0) Prerequisites
- Ox64 board + microSD card
- A Linux image for the board (e.g., Armbian / Debian)
- Network access (Ethernet USB dongle or Wi-Fi) and SSH

## 1) Flash and first boot
1. Flash the board image to the microSD card using `dd`, balenaEtcher, or Raspberry Pi Imager.
2. Boot the Ox64 and complete any first-boot prompts.
3. SSH into the board (find the IP via your router/DHCP lease list or `arp -a`).

## 2) Update packages
```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip git
```

> If your image does not include `apt`, install Python 3.8+ with pip using the package manager it provides, then continue.

## 3) Get the code
```bash
cd ~
git clone https://github.com/halfsohappy/TheaterGWD.git
cd TheaterGWD
```

## 4) Quick setup (script)
From inside the repository, run the Ox64 installer to create a virtual environment and install Gooey into it:
```bash
cd ~/TheaterGWD/Ox64
bash install.sh
```

When it finishes, start Gooey:
```bash
~/TheaterGWD/Ox64/.venv/bin/gooey --host 0.0.0.0 --port 5000 --no-browser
```

Open the UI from another device on the same network:
```
http://<ox64-ip>:5000
```

## 5) Run on boot (systemd user service)
Use the provided user-level unit so Gooey starts after networking is up.

1. Copy the unit:
   ```bash
   mkdir -p ~/.config/systemd/user
   cp ~/TheaterGWD/Ox64/gooey.service ~/.config/systemd/user/
   ```
2. If your repo is **not** in `~/TheaterGWD`, edit `WorkingDirectory` and `ExecStart` paths in the service file to match your location.
3. Enable the service:
   ```bash
   systemctl --user daemon-reload
   systemctl --user enable --now gooey.service
   # allow user services to run after logout
   sudo loginctl enable-linger "$USER"
   ```
4. Check status/logs:
   ```bash
   systemctl --user status gooey.service
   journalctl --user -u gooey.service -f
   ```

## 6) Updating Gooey on the Ox64
```bash
cd ~/TheaterGWD
git pull
source Ox64/.venv/bin/activate
pip install -U ./gooey
systemctl --user restart gooey.service   # if using systemd
```

## Notes
- Default port is **5000**; change with `--port 8080` in the service file or manual command.
- Use `--host 0.0.0.0` to make the UI reachable from other devices (already set in the service file above).
- The virtual environment lives in `Ox64/.venv` to keep the rest of the repo clean. Delete it safely with `rm -rf Ox64/.venv` if you need a fresh install.
