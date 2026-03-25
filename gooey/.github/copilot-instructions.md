# Gooey — AI Coding Agent Instructions

Gooey is the web-based control center for TheaterGWD. It lets operators
configure, query, and monitor ESP32-S3 sensor devices over a local WiFi
network via the OSC (Open Sound Control) protocol.

**Stack:** Python ≥ 3.8 · Flask · Flask-SocketIO · python-osc · Vanilla JS · No build step

---

## 1. Build & Run

```bash
pip install -r requirements.txt
python run.py                  # http://127.0.0.1:5000
python run.py --port 8080      # custom port
python run.py --host 0.0.0.0   # listen on all interfaces
python run.py --no-browser     # skip auto-open
```

Or install as a package:
```bash
pip install .
gooey
```

---

## 2. Repository Layout

```
app/
  __init__.py          Flask app factory; registers routes and SocketIO
  main.py              HTTP routes and SocketIO event handlers
  osc_handler.py       OSCEngine: UDP send/receive/bridge + message log
  templates/
    index.html         Single-page application shell
  static/
    js/app.js          All frontend logic (IIFE, vanilla JS)
    css/style.css      All styles (no preprocessor)
run.py                 CLI entry point
pyproject.toml
requirements.txt
```

---

## 3. Python Style Conventions

- Python ≥ 3.8. Use type hints where practical.
- Classes: `PascalCase`. Functions/methods: `snake_case`.
- Private members: leading `_` (e.g. `_receivers`, `_lock`).
- Thread safety via `threading.Lock()`.
- **OSC string payloads MUST be sent as a single-element list** — wrap in
  `[payload]` before passing to `client.send_message()`. A bare string is
  space-split by python-osc, which corrupts config strings containing IPs
  or spaces.

---

## 4. JavaScript Style Conventions

- Vanilla JS — no frameworks, no build step, no npm.
- Wrap all module code in an IIFE: `(function () { "use strict"; … })()`.
- DOM helpers: `$()` for `document.querySelector`, `$$()` for
  `document.querySelectorAll`.
- Section markers: `/* ── Section name ── */`.
- When cloning cards for the star tab, strip all `id` attributes from the
  clone and its descendants to prevent duplicate IDs.
- Payloads sent to the backend MUST be wrapped in a single-element array:
  `data.args = [payload]`. A bare string value will be space-split by the
  Python backend, breaking multi-token config values.

---

## 5. CSS / Design Conventions

- Light theme. Header: lavender `#DAC7FF`. Accent: `#90849c`.
- Fonts: Playwrite IE (title), Playwrite DE Grund (nav tabs), Martian Mono (body).
- Body font-size: 18 px.
- Draggable card order persists in `localStorage` key `gooey_card_order`.
  Starred cards use `gooey_starred_cards`.
- Indentation: 4 spaces everywhere.

---

## 6. OSC Transport Architecture

```
Browser  ←—— WebSocket (SocketIO) ——→  Flask/OSCEngine  ←—— UDP ——→  Device
```

`OSCEngine` (in `osc_handler.py`) owns:
- **Senders** — fire-and-forget `SimpleUDPClient` per send call.
- **Receivers** — `ThreadingOSCUDPServer` threads that emit `osc_message`
  SocketIO events to the browser.
- **Bridges** — forward OSC messages from one port to another host/port.
- **Message log** — ring buffer of the last 500 messages, each with
  direction (`send`/`recv`/`bridge`), address, serialised args, timestamp.

### Sending from JavaScript

```javascript
function sendCmd(address, payload) {
    var data = { host: devHost(), port: devPort(), address: address };
    if (payload) { data.args = [payload]; }   // single-element array — critical
    return api("send", data);
}
```

Config strings are always passed as the sole array element so python-osc
delivers them intact as a single OSC string argument.

### Receiving in JavaScript

```javascript
socket.on("osc_message", function (entry) {
    appendToFeed(entry);
    parseReplyIntoRegistry(entry);
});
```

`entry` shape: `{ time, direction, address, args: [{type, value}, …], source, dest }`.

---

## 7. Client-Side Device Registry

Gooey maintains a fully client-side registry:

```javascript
var devices = {};        // { id: { host, port, name, messages:{}, patches:{} } }
var activeDeviceId = "";
```

Device ID: `"{name}@{host}:{port}"` (e.g. `"bart@192.168.1.100:8000"`).

**Auto-population:** `parseReplyIntoRegistry(entry)` reads every incoming
OSC message. It detects list and verbose-list replies and merges the
parsed data into the registry. Tables re-render whenever the registry is
mutated.

### Config string parser

```javascript
function parseConfigString(str) {
    // Returns flat object: { key: "value", … }
    // Accepts both comma and space as delimiters; lookahead stops at next key:
}
```

### Accepted field aliases when reading replies

| Canonical | Also accepted |
|-----------|---------------|
| `adr` | `addr`, `address` |
| `low` | `min` |
| `high` | `max` |
| `ori_only` | `orionly` |
| `ori_not` | `orinot` |
| `adrMode` | `adrmode`, `adr_mode` |

Override lists in patch replies may be split on either `+` or `,`.
Message lists in patch replies use `+` as separator (e.g. `msg1+msg2`);
display as comma-separated.

---

<!-- FIRMWARE_PROTOCOL_START -->
## 8. Firmware OSC Protocol

> This section is auto-synced from `docs/firmware-osc-protocol.md` in the
> [TheaterGWD](https://github.com/halfsohappy/TheaterGWD) repository.
> Do not edit it here directly — run the **Sync Firmware Protocol** workflow
> to pull the latest version.

### 8.1 Address Format

All commands use the pattern:

```
/annieData{device_adr}/{rest…}
```

`{device_adr}` is the device's provisioned name with a leading slash
(e.g. `/bart`, `/ab7`), so the full path is `/annieData/bart/…`.

All reply messages mirror the incoming address with `/reply` prepended:
`/reply{device_adr}/{rest…}`.

**Case handling:** every command segment is normalised to lowercase with
underscores stripped, so `addMsg`, `add_msg`, and `addmsg` are equivalent.
User-defined names preserve their original case.

### 8.2 Config String Format

Most create/update commands accept a comma-separated key:value string as
their single OSC string argument:

```
key:value, key:value, …
```

The **reference operator** (`-` instead of `:`) copies a field value from
another registry object:

```
ip-mixer1, port-mixer1, value:accelX
```

`default-refName` copies every set field from the named reference.

### 8.3 Message Commands — `/annieData{dev}/msg/{name}/…`

**assign** (create / update):

```
Address:  /annieData{dev}/msg/{name}  [or /…/assign]
Payload:  config string
```

Config keys:

| Key | Aliases | Description |
|-----|---------|-------------|
| `name` | | Rename the message |
| `ip` | | Destination IP |
| `port` | | Destination UDP port (1–65535) |
| `adr` | `addr`, `address` | OSC address path |
| `patch` | | Parent patch name |
| `value` | `val` | Sensor data stream (see §8.9) |
| `low` | `min`, `lo` | Output range minimum |
| `high` | `max`, `hi` | Output range maximum |
| `enabled` | | `true`/`1`/`yes`/`on` or `false`/`0`/`no`/`off` |
| `ori_only` | | AB7: send only when this ori is active |
| `ori_not` | | AB7: send only when this ori is NOT active |

Other message commands:

| Command | Aliases | Payload | Action |
|---------|---------|---------|--------|
| `delete` | `remove` | none | Remove message from registry and all patches |
| `enable` | `unmute` | none | Enable message |
| `disable` | `mute` | none | Disable message |
| `info` | | none | Reply with verbose info (→ `/reply{dev}/msg/{name}/info`) |

### 8.4 Patch Commands — `/annieData{dev}/patch/{name}/…`

**assign** (create / update):

```
Address:  /annieData{dev}/patch/{name}  [or /…/assign]
Payload:  config string
```

Config keys: `name`, `ip`, `port`, `adr`/`addr`/`address`, `low`/`min`/`lo`,
`high`/`max`/`hi`, `period` (ms, 20–60000).

Other patch commands:

| Command | Aliases | Payload | Action |
|---------|---------|---------|--------|
| `delete` | `remove` | none | Stop task, remove patch |
| `start` | `enable`, `go` | none | Start send task |
| `stop` | `disable`, `mute` | none | Stop send task |
| `addmsg` | `add` | `"msg1, msg2"` | Add messages to patch |
| `removemsg` | `rmmsg` | message name | Remove message from patch |
| `period` | `rate` | `"50"` (ms string) | Set send period (clamped 20–60000) |
| `override` | | field list | Control which patch fields override message fields |
| `adrmode` | `addressmode` | mode name | Address composition mode |
| `setall` | | config string | Apply config to every message in patch |
| `solo` | | message name | Enable named msg, disable all others |
| `unsolo` | `unmute`, `enableall` | none | Re-enable all messages |
| `info` | | none | Reply with verbose patch info |

**override** payload values:
- `ip`, `port`, `adr`, `low`, `high` — override individual field
- `scale` / `bounds` — shorthand for `low, high`
- `all` — override everything; `none` / `clear` — override nothing
- `-ip` etc. — disable that override

**adrmode** values:

| Mode | Aliases | Behaviour |
|------|---------|-----------|
| `fallback` | `default`, `0` | Message address; patch as fallback (**default**) |
| `override` | `replace`, `1` | Patch address replaces message address |
| `prepend` | `pre`, `2` | `patch.adr + "/" + msg.adr` |
| `append` | `post`, `3` | `msg.adr + "/" + patch.adr` |

### 8.5 Structural Commands

```
/annieData{dev}/clone/msg    payload: "src, dst"   — duplicate message
/annieData{dev}/clone/patch  payload: "src, dst"   — duplicate patch
/annieData{dev}/rename/msg   payload: "old, new"   — rename message
/annieData{dev}/rename/patch payload: "old, new"   — rename patch
/annieData{dev}/move         payload: "msgName, patchName"  — move msg to patch
```

### 8.6 List Commands — `/annieData{dev}/list/…`

Optional verbose flag: `"verbose"`, `"v"`, `"1"`, or `"true"`.

| Address | Reply address | Content |
|---------|---------------|---------|
| `/list/msgs` or `/list/messages` | `/reply{dev}/list/msgs` | Message names |
| `/list/patches` | `/reply{dev}/list/patches` | Patch names |
| `/list/all` or `/list` | `/reply{dev}/list/all` | Patches then messages |

Non-verbose reply format (zero items → `… (0): none`):
```
Messages (2):
  accelX
  gyroZ
Patches (1):
  sensors
```

Verbose reply format (one line per item, fields present only when set):
```
Messages (2):
  accelX [ON] ip:192.168.1.50 port:9000 adr:/sensor/x val:accelX low:0.00 high:1.00 patch:sensors
  gyroZ [OFF] ip:192.168.1.50 port:9000 adr:/sensor/z val:gyroZ low:0.00 high:1.00 patch:sensors
Patches (1):
  sensors [RUNNING, 50ms, 2 msgs] ip:192.168.1.50 port:9000 adr_mode:fallback
```

### 8.7 Direct Command

```
/annieData{dev}/direct/{name}
Payload: "value:accelX, ip:192.168.1.50, port:9000, adr:/x, period:50"
```

One command creates/updates a message + patch with the same name, adds
the message to the patch, and starts it.

### 8.8 Global Commands

| Address | Payload | Reply | Action |
|---------|---------|-------|--------|
| `/blackout` | none | `"BLACKOUT"` on `/reply{dev}/blackout` | Stop all patch tasks |
| `/restore` | none | `"RESTORE"` on `/reply{dev}/restore` | Restart all patches |
| `/dedup` | `"on"` / `"off"` / omit | `"DEDUP ON/OFF"` | Toggle duplicate suppression |
| `/save` or `/save/all` | none | `"Saved N objects"` | Save all to NVS |
| `/save/msg` | msg name | — | Save one message |
| `/save/patch` | patch name | — | Save one patch |
| `/load` or `/load/all` | none | `"Loaded N objects"` | Load from NVS |
| `/nvs/clear` | none | — | Erase all OSC data from NVS |
| `/status/config` | `"ip:…, port:…, adr:…"` | — | Configure status destination |
| `/status/level` | `debug`/`info`/`warning`/`error` | — | Set status log level |

### 8.9 Data Streams (Sensor Values)

All values normalised to `[0, 1]`. Use the canonical name in `value:` config.

| Name | Aliases | Description |
|------|---------|-------------|
| `accelX` | `accelx` | X-axis accelerometer |
| `accelY` | `accely` | Y-axis accelerometer |
| `accelZ` | `accelz` | Z-axis accelerometer |
| `accelLength` | `accellen`, `alen` | Acceleration magnitude |
| `gyroX` | `gyrox` | X-axis gyroscope |
| `gyroY` | `gyroy` | Y-axis gyroscope |
| `gyroZ` | `gyroz` | Z-axis gyroscope |
| `gyroLength` | `gyrolen`, `glen` | Gyroscope magnitude |
| `baro` | | Barometric pressure |
| `eulerX` | `eulerx` | Roll |
| `eulerY` | `eulery` | Pitch |
| `eulerZ` | `eulerz` | Yaw |

### 8.10 Ori Commands — AB7 Only

Gate all ori UI on the `body.ori-enabled` CSS class. Only send ori
commands to devices identified as AB7.

| Address | Payload | Reply | Action |
|---------|---------|-------|--------|
| `/ori/save` or `/ori/save/{name}` | opt. name | `"Saved: name"` | Save current orientation |
| `/ori/delete/{name}` | opt. name | `"Deleted: name"` | Delete saved ori |
| `/ori/clear` | none | `"All oris cleared"` | Delete all oris |
| `/ori/list` | none | comma-sep names; active marked `(*)` | List all oris |
| `/ori/threshold` | float (rad/s) | `"threshold: X.XX"` | Set motion-gate threshold |
| `/ori/active` | none | active ori name or `"(none)"` | Query active ori |

Messages on AB7 can include ori conditions:
```
ori_only:light1    — skip unless light1 is currently active
ori_not:dark       — skip if dark is currently active
```

### 8.11 Reply Encoding Rules

| Data | Encoding |
|------|----------|
| Config payload | Single OSC string argument |
| Float in reply | 2 decimal places: `0.00`, `255.50` |
| Enabled state | `[ON]` / `[OFF]` in verbose strings |
| Patch run state | `[RUNNING]` / `[STOPPED, …]` |
| Override list | Comma-separated, no spaces: `ip,port,adr` |
| Address mode | Lowercase: `fallback`, `override`, `prepend`, `append` |
| Message list in patch | `+`-separated: `msg1+msg2+msg3` |
| Period payload | Quoted string: `"50"` (see §4.7) |

> **Period must be a string.** Send period as `'"' + ms + '"'` in JS so the firmware
> receives it via `nextAsString()`. Sending a bare integer causes the period to be
> silently ignored and clamped to 1 ms.

### 8.12 Bart vs AB7 Differences

| Feature | Bart | AB7 |
|---------|------|-----|
| IMU data | Simulated sine waves | BNO085 live readings |
| Ori system | Not present | Full save/match/gate pipeline |
| `ori_only` / `ori_not` | Parsed but always pass | Actively evaluated |
| Button GPIO 0 | Not used | Hold 3 s clears provisioning; tap saves ori |
| Build envs | `pio run -e bart` | `pio run -e ab7` or `ab7-bno085` |
| Compile flag | (none) | `-DAB7_BUILD` (BNO variant also `-DAB7_IMU_BNO085`) |

<!-- FIRMWARE_PROTOCOL_END -->

---

## 9. Adding Features — Checklist

When adding a new Gooey feature that sends or parses OSC commands, verify:

1. **Address format** — follows `/annieData{dev}/{category}/{name}/{cmd}`.
2. **Payload wrapping** — config string passed as `data.args = [payload]`
   (single-element array), never as a bare string.
3. **Period as string** — patch period sent as `'"' + ms + '"'` so the
   firmware receives it via `nextAsString()`.
4. **Reply parsing** — `parseReplyIntoRegistry` updated to handle new
   reply addresses / payload formats.
5. **AB7 gating** — any ori-related UI shown only when `body.ori-enabled`
   is set; ori commands sent only to AB7 devices.
6. **Field aliases** — parse both `adr`/`addr`/`address`, `low`/`min`,
   `high`/`max`, `adrMode`/`adrmode`/`adr_mode` when reading device replies.
7. **Registry safety** — all updates go through `Object.assign` so
   unrelated fields are preserved.
8. **Thread safety (Python)** — any shared state in `OSCEngine` or new
   handlers must be protected by `threading.Lock()`.
