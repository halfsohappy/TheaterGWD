# Gooey on GL.iNet + Teensy

Run the TheaterGWD Gooey control center on your GL.iNet router with a Teensy
plugged into the USB port. The router serves the web interface to your whole
network and talks to the Teensy directly over USB serial.

---

## Why this works well

- The router is already on the network — no image flashing, no WiFi setup
- The router runs OpenWRT, the same OS targeted by the Ox64 setup
- The Teensy shows up as a standard USB serial device (`/dev/ttyACM0`)
- Gooey has built-in serial support — connect to the port directly in the UI
- The router stays on 24/7 so Gooey is always available

---

## Hardware requirements

| Item | Notes |
|------|-------|
| GL.iNet router | See model recommendations below |
| Teensy (4.0, 4.1, 3.x) | With TheaterGWD firmware flashed |
| USB-A to USB-Micro/Type-C cable | To connect Teensy to the router's USB-A port |
| A separate computer | To flash the Teensy firmware (one-time) |

### GL.iNet model recommendations

| Model | RAM | Verdict |
|-------|-----|---------|
| GL-MT300N-V2 (Mango) | 128 MB | Too tight — not recommended |
| GL-AR750 / AR750S | 128 MB | Too tight — not recommended |
| GL-MT1300 (Beryl) | 256 MB | Works |
| GL-SFT1200 (Opal) | 128 MB | Too tight — not recommended |
| GL-AXT1800 (Slate AX) | 512 MB | Works great |
| GL-MT2500 (Brume 2) | 1 GB | Works great |
| GL-MT6000 (Flint 2) | 1 GB | Works great |
| GL-X3000 (Spitz AX) | 1 GB | Works great |

Gooey's idle memory footprint is roughly 35–50 MB. Any router with 256 MB or
more RAM is comfortable. 128 MB models can technically run it but leave very
little headroom.

---

## Step 1 – Flash the Teensy firmware

Do this on your regular computer before touching the router.

1. Install [PlatformIO](https://platformio.org/) (VS Code extension or CLI)
2. Clone this repository and open it
3. Copy the appropriate Teensy config into `platformio.ini`:
   ```bash
   # For Teensy 4.1 (recommended)
   cp platforms/platformio.teensy41.ini platformio.ini

   # For Teensy 4.0
   cp platforms/platformio.teensy40.ini platformio.ini
   ```
4. Plug the Teensy into your computer and flash:
   ```bash
   pio run -t upload
   ```
5. Unplug from your computer — it's ready to go into the router.

---

## Step 2 – Enable SSH on the router

1. Open the GL.iNet admin panel: **http://192.168.8.1**
2. Go to **System → Advanced Settings** (or **SSH** in newer firmware)
3. Enable SSH access
4. From your computer:
   ```bash
   ssh root@192.168.8.1
   ```
   Use the same admin password you set when first configuring the router.

> **Note:** The default GL.iNet LAN address is `192.168.8.1`. If you've changed
> it, substitute your actual address throughout this guide.

---

## Step 3 – Install Gooey

With the SSH session open, run the one-line installer:

```sh
wget -qO /tmp/install.sh \
  https://github.com/halfsohappy/TheaterGWD/raw/main/glinet/setup/install.sh \
  && sh /tmp/install.sh
```

This will:
1. Install Python 3 and `kmod-usb-acm` (the USB serial driver for the Teensy)
2. Clone the TheaterGWD repository
3. Set up a Python virtual environment and install Flask + dependencies
4. Register and start a `gooey` service that survives reboots

When it finishes you will see:

```
  ✓ Gooey is running!

  Open in browser:  http://192.168.8.1:5000
```

---

## Step 4 – Plug in the Teensy

Plug the Teensy into the router's USB-A port. Verify it is detected:

```bash
ls /dev/ttyACM*
# Should print: /dev/ttyACM0
```

If nothing appears, check that the module loaded:

```bash
lsmod | grep cdc_acm
# If empty:
modprobe cdc_acm
```

---

## Step 5 – Connect in Gooey

1. Open **http://192.168.8.1:5000** in any browser on your network
2. In the Gooey interface, find the serial port section
3. Select `/dev/ttyACM0` and set the baud rate to match your firmware
   (default is `115200`)
4. Click Connect

The Teensy's sensor data will now flow through to Gooey.

---

## Managing the service

```bash
# Status
/etc/init.d/gooey status

# Logs
logread -f | grep gooey

# Restart
/etc/init.d/gooey restart

# Stop
/etc/init.d/gooey stop
```

---

## Updating Gooey

```bash
git -C /opt/theatergwd pull --ff-only
/etc/init.d/gooey restart
```

---

## Troubleshooting

### `opkg update` fails
The router needs internet access for opkg. Check that the WAN is connected in
the GL.iNet admin panel, then retry.

### Teensy not appearing as `/dev/ttyACM0`
- Try a different USB cable (use a data cable, not a charge-only one)
- Manually load the driver: `modprobe cdc_acm`
- Check the kernel log: `dmesg | tail -20`
- Confirm the Teensy has firmware on it and its LED is on

### Gooey URL doesn't load
- Confirm the service is running: `/etc/init.d/gooey status`
- Check the port: `netstat -tlnp | grep 5000`
- Check logs: `logread | grep -i gooey`
- Make sure you're on the same LAN as the router

### Router runs out of memory during install
The Python + pip installation is the memory peak. If the router OOMs:
```bash
# Add a swap file on a USB drive plugged into the router
dd if=/dev/zero of=/tmp/swapfile bs=1M count=128
mkswap /tmp/swapfile
swapon /tmp/swapfile
# Then retry the installer
sh /tmp/install.sh
```

### Not enough flash storage
If `/overlay` is full, point the install to a USB drive:
```bash
opkg install block-mount kmod-fs-ext4 kmod-usb-storage e2fsprogs
# Format and mount a USB drive to /opt, then re-run install.sh
```

---

## Compared to the Ox64 setup

| | GL.iNet + Teensy | Ox64 |
|---|---|---|
| Image flashing | Not needed | Required |
| WiFi setup | Already done via router UI | First-boot serial step |
| Serial console | Not needed | Required for initial setup |
| Sensor hardware | Teensy via USB | Direct GPIO or WiFi |
| Always-on networking | Yes (it's a router) | Needs separate power |
| Cost | Router you may already own | ~$8 board + accessories |
