# Gooey on Ox64

Run the TheaterGWD Gooey control center on a Pine64 Ox64 — a cheap, low-power
device that puts the web interface on your network 24/7 without needing a laptop
running.

---

## What you need

| Item | Notes |
|------|-------|
| [Pine64 Ox64](https://pine64.com/product/ox64-sbc/) | The board itself |
| microSD card | 4 GB minimum, Class 10 recommended |
| microSD card reader | For flashing the image |
| USB-C cable | For power and serial console |
| USB serial adapter | Any CH340 / CP2102 / FTDI adapter |
| Computer | macOS, Linux, or Windows to flash and configure |

You do **not** need a keyboard, mouse, or monitor — everything is done over serial
and then SSH.

---

## Step 1 – Flash the image

### Download

Download the latest Ox64 OpenWRT image from the Fishwaldo builds:

```
https://github.com/fishwaldo/bl808-linux/releases
```

Download the file named something like `openwrt-bl808-pine64_ox64-sdcard.img.gz`.

### Write to microSD

**macOS / Linux:**
```bash
# Find your SD card device (e.g. /dev/disk4 or /dev/sdb)
# macOS
diskutil list

# Linux
lsblk

# Unmount the card
# macOS: diskutil unmountDisk /dev/diskN
# Linux: umount /dev/sdXN  (if mounted)

# Flash (replace /dev/diskN with your card)
gunzip -c openwrt-bl808-pine64_ox64-sdcard.img.gz | sudo dd of=/dev/diskN bs=4M status=progress
sync
```

**Windows:** Use [balenaEtcher](https://etcher.balena.io/) — select the `.img.gz`
file and your SD card, then click Flash.

Eject the card when done.

---

## Step 2 – Connect the serial console

The Ox64 boots headless. You communicate with it over a 3-wire serial connection
until WiFi is set up.

### Wiring

Connect your USB serial adapter to the Ox64's **UART0** pins:

| Ox64 pin | Serial adapter pin |
|----------|--------------------|
| TX (GPIO14) | RX |
| RX (GPIO15) | TX |
| GND | GND |

> Do **not** connect 3.3V/5V from the serial adapter — power the Ox64 from
> USB-C only.

### Open a terminal

**macOS / Linux:**
```bash
# Find the serial port
ls /dev/tty.*        # macOS
ls /dev/ttyUSB*      # Linux

# Connect (replace the port name)
screen /dev/tty.usbserial-XXXX 2000000
# Or with minicom:
minicom -b 2000000 -D /dev/ttyUSB0
```

**Windows:** Use [PuTTY](https://putty.org/) — set Connection Type to Serial,
Speed to `2000000`.

Insert the microSD card, then plug in the USB-C power cable. You should see
boot messages appear. Press **Enter** at the login prompt and log in as `root`
(no password by default).

---

## Step 3 – Connect to WiFi

Once you have a root shell, run the WiFi setup script:

```sh
wget -qO /tmp/wifi-setup.sh \
  https://github.com/halfsohappy/TheaterGWD/raw/main/ox64/setup/wifi-setup.sh \
  && sh /tmp/wifi-setup.sh
```

The script will ask for your network name and password, configure the wireless
interface, and print the IP address when connected.

```
  Ox64 WiFi Setup
  ───────────────

  Network name (SSID): MyTheaterNetwork
  Password:            ••••••••

  Configuring WiFi...
  Restarting wireless...
  Waiting for connection (up to 20 seconds)...

  ✓ Connected!

  IP address:  192.168.1.42
  SSH access:  ssh root@192.168.1.42
```

Write down the IP address — you will use it to access Gooey.

> **Tip:** Assign the Ox64 a static IP (or DHCP reservation) in your router so
> the address never changes.

---

## Step 4 – Install Gooey

You can now switch to SSH from your normal computer (the serial adapter is no
longer needed):

```bash
ssh root@<ox64-ip>
```

Then run the one-line installer:

```sh
wget -qO /tmp/install.sh \
  https://github.com/halfsohappy/TheaterGWD/raw/main/ox64/setup/install.sh \
  && sh /tmp/install.sh
```

This will:
1. Install Python 3 via opkg
2. Clone the TheaterGWD repository
3. Set up a Python virtual environment and install Flask + dependencies
4. Register and start a `gooey` service that survives reboots

The whole process takes about 3–5 minutes. When it finishes you will see:

```
  ✓ Installation complete!

  Open Gooey at:  http://192.168.1.42:5000
```

---

## Step 5 – Open the interface

Open the URL printed by the installer in any browser on the same network:

```
http://<ox64-ip>:5000
```

Gooey starts automatically every time the Ox64 boots. You do not need to log in
or run any commands — just plug it in and wait about 30 seconds.

---

## Managing the service

```bash
# Check status
/etc/init.d/gooey status       # OpenWRT
systemctl status gooey         # systemd (if applicable)

# View live logs
logread -f                     # OpenWRT
journalctl -fu gooey           # systemd

# Restart
/etc/init.d/gooey restart
systemctl restart gooey

# Stop
/etc/init.d/gooey stop
systemctl stop gooey
```

---

## Updating Gooey

SSH into the Ox64 and pull the latest changes:

```bash
git -C /opt/theatergwd pull --ff-only
/etc/init.d/gooey restart
```

---

## Troubleshooting

### Can't see boot messages over serial
- Check TX/RX are not swapped. If you see nothing, swap them and try again.
- Make sure the baud rate is exactly **2000000** (two million).
- Try a different USB-C cable — some are charge-only and carry no data.

### WiFi connected but Gooey URL doesn't load
- Confirm the service is running: `/etc/init.d/gooey status`
- Confirm the port is open: `netstat -tlnp | grep 5000`
- Check logs: `logread | grep gooey`
- Make sure your browser and the Ox64 are on the same network.

### opkg install fails
- The Ox64 needs a working internet connection for opkg.
- Verify DNS: `ping -c 3 8.8.8.8`
- Try: `opkg update` first, then re-run `install.sh`.

### Python venv not available
The installer automatically falls back to a system-wide pip install if the `venv`
module is missing from the OpenWRT Python package. You can also install manually:

```bash
opkg install python3-venv
sh /tmp/install.sh
```

### IP address changed after reboot
Set a DHCP reservation for the Ox64's MAC address in your router, or configure
a static IP via UCI:

```bash
uci set network.wlan.proto='static'
uci set network.wlan.ipaddr='192.168.1.42'
uci set network.wlan.netmask='255.255.255.0'
uci set network.wlan.gateway='192.168.1.1'
uci set network.wlan.dns='8.8.8.8'
uci commit network
service network restart
```

---

## Hardware notes

The Pine64 Ox64 uses the **Bouffalo Lab BL808** SoC:

- **D0 core** — 64-bit T-Head C906 RISC-V @ 480 MHz — runs Linux + Gooey
- **M0 core** — 32-bit RISC-V — handles WiFi/BLE low-level stack
- **64 MB DRAM** shared between cores
- **WiFi** — 2.4 GHz 802.11b/g/n (WiFi 4)

Gooey's idle RAM footprint is roughly 25–40 MB, well within the 64 MB limit.
CPU usage is negligible outside of page loads.

Power draw at idle is approximately 200–400 mW from the USB-C port — suitable
for a USB charger or powered USB hub at the tech table.
