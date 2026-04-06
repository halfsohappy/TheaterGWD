# Symon

OSC-controlled audio player for **Raspberry Pi 3**.  
Drop audio files in a folder, send OSC messages over the network, Symon plays them.

---

## Flashing the Pi

1. Download **Raspberry Pi OS Lite (64-bit, Bookworm)** from  
   <https://www.raspberrypi.com/software/operating-systems/>

2. Flash the image to a microSD card using  
   [Raspberry Pi Imager](https://www.raspberrypi.com/software/) or `dd`.

3. In Raspberry Pi Imager's **OS Customisation** panel (⚙ gear icon):
   - Set hostname (e.g. `symon`)
   - Enable SSH
   - Set username `pi` and a password
   - Configure your WiFi network

4. Boot the Pi and SSH in:

    ```bash
    ssh pi@symon.local
    ```

---

## Installation

Clone or copy the `Symon/` folder to the Pi, then run the setup script:

```bash
git clone https://github.com/halfsohappy/TheaterGWD.git
cd TheaterGWD/Symon
sudo bash setup.sh
```

The script:
- Installs `python3`, `python3-pygame`, `alsa-utils`, and `python-osc`
- Creates `~/audio` (put your audio files here)
- Copies `symon.py` to `~/symon/`
- Installs and enables the `symon` systemd service (starts on boot)

### Add audio files

```bash
scp my_cue.wav pi@symon.local:~/audio/
```

Supported formats: `.wav`, `.mp3`, `.ogg`, `.flac`, `.aiff`

### Start / stop

```bash
sudo systemctl start symon
sudo systemctl stop symon
journalctl -u symon -f          # live log
```

---

## OSC Reference

Default listen port: **8000 UDP**

| Address | Argument | Description |
|---|---|---|
| `/symon/play` | `<filename \| index>` | Play a file by name (e.g. `cue1.wav`) or 1-based list index |
| `/symon/stop` | — | Stop playback immediately |
| `/symon/pause` | — | Pause playback |
| `/symon/resume` | — | Resume paused playback |
| `/symon/volume` | `<float 0.0–1.0>` | Set master volume |
| `/symon/fade` | `[seconds]` | Fade out over N seconds (default `2.0`), then stop |
| `/symon/list` | — | Print file list to log; reply with newline-separated names |
| `/symon/status` | — | Reply with current state, filename, and volume |

### OSC replies

When `--reply-host` is set, Symon sends status replies back:

| Address | Arguments | When |
|---|---|---|
| `/symon/playing` | `filename` | Playback started |
| `/symon/stopped` | `1` | Playback stopped or fade complete |
| `/symon/paused` | `1` | Playback paused |
| `/symon/resumed` | `1` | Playback resumed |
| `/symon/volume` | `float` | Volume acknowledged |
| `/symon/list` | `string` | Newline-separated file list |
| `/symon/status` | `state file vol` | Current status |
| `/symon/error` | `message` | Error description |

---

## Configuration

Edit `/etc/systemd/system/symon.service` to change options, then:

```bash
sudo systemctl daemon-reload
sudo systemctl restart symon
```

### Available flags

```
--port        UDP port to listen on          (default: 8000)
--audio-dir   Path to audio files            (default: ~/audio)
--reply-host  IP to send OSC replies to      (default: disabled)
--reply-port  Port for OSC replies           (default: 9000)
```

### Example — reply to annieData Control Center

```ini
ExecStart=/usr/bin/python3 /home/pi/symon/symon.py \
    --audio-dir /home/pi/audio \
    --port 8000 \
    --reply-host 192.168.1.50 \
    --reply-port 9000
```

---

## Running manually

```bash
python3 symon.py --audio-dir ~/audio --port 8000
```

---

## Example usage with annieData

From the **annieData Control Center** (or any OSC client):

```
/symon/play  intro.wav
/symon/volume  0.8
/symon/fade  3.0
/symon/play  2          # plays the 2nd file in the list
```

---

## Audio output

By default, Raspberry Pi OS routes audio to the 3.5 mm jack or HDMI depending
on your `raspi-config` setting.  To force the headphone jack:

```bash
sudo raspi-config
# Advanced Options → Audio → Force 3.5mm jack
```

For USB audio interfaces, check the device index with `aplay -l` and create
`~/.asoundrc`:

```
defaults.pcm.card 1
defaults.ctl.card 1
```
