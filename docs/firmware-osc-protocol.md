# TheaterGWD Firmware — OSC Protocol Reference

> **This file is the canonical source of truth for the OSC protocol.**
> The standalone Gooey repo embeds this content via a GitHub Actions sync
> workflow. Update this file when the firmware's command set changes, then
> re-run the sync to propagate the changes.

---

## 1. Address Format

All commands use the pattern:

```
/annieData{device_adr}/{rest…}
```

`{device_adr}` is the device's provisioned name with a leading slash
(stored in NVS key `device_adr`, e.g. `/bart`, `/ab7`). Together this
forms `/annieData/bart/…`.

All reply messages mirror the incoming address with `/reply` prepended:

```
/reply{device_adr}/{rest…}
```

e.g. `/annieData/bart/list/msgs` → reply on `/reply/bart/list/msgs`.

**Case handling:** every command segment is normalised to lowercase with
underscores stripped before matching, so `addMsg`, `add_msg`, and
`addmsg` are all equivalent. User-defined names (message names, patch
names, ori names) preserve their original case.

---

## 2. Config String Format

Most create/update commands accept a comma-separated key:value config
string as their single OSC string argument:

```
key:value, key:value, …
```

Keys are case-insensitive. Whitespace around keys and values is trimmed.
The **reference operator** (`-` instead of `:`) copies a field from
another registry object instead of specifying a literal value:

```
ip-mixer1, port-mixer1, value:accelX
```

`default-refName` / `all-refName` copies every set field from the named
reference (message or patch).

---

## 3. Message Commands — `/annieData{dev}/msg/{name}/…`

### 3.1 `assign` (create / update)

Address: `/annieData{dev}/msg/{name}` or `/annieData{dev}/msg/{name}/assign`  
Payload: config string

Valid config keys:

| Key | Aliases | Description |
|-----|---------|-------------|
| `name` | | Rename this message |
| `ip` | | Destination IP address |
| `port` | | Destination UDP port (1–65535) |
| `adr` | `addr`, `address` | OSC address path (e.g. `/sensor/x`) |
| `patch` | | Parent patch name |
| `value` | `val` | Sensor data stream name (see §8) |
| `low` | `min`, `lo` | Output range minimum (float) |
| `high` | `max`, `hi` | Output range maximum (float) |
| `enabled` | | `true`/`1`/`yes`/`on` or `false`/`0`/`no`/`off` |
| `ori_only` | | (AB7 only) Send only when this ori is active |
| `ori_not` | | (AB7 only) Send only when this ori is NOT active |

Reply: status string to the sender's IP/port.

### 3.2 `delete` / `remove`

Address: `/annieData{dev}/msg/{name}/delete`  
Payload: none  
Action: remove the message from the registry and from any patch it belongs to.

### 3.3 `enable` / `unmute`

Address: `/annieData{dev}/msg/{name}/enable`  
Payload: none

### 3.4 `disable` / `mute`

Address: `/annieData{dev}/msg/{name}/disable`  
Payload: none

### 3.5 `info`

Address: `/annieData{dev}/msg/{name}/info`  
Payload: none  
Reply address: `/reply{dev}/msg/{name}/info`  
Reply payload: verbose info string (see §7.1)

---

## 4. Patch Commands — `/annieData{dev}/patch/{name}/…`

### 4.1 `assign` (create / update)

Address: `/annieData{dev}/patch/{name}` or `/annieData{dev}/patch/{name}/assign`  
Payload: config string

Valid config keys (same reference operator rules apply):

| Key | Aliases | Description |
|-----|---------|-------------|
| `name` | | Rename this patch |
| `ip` | | Destination IP |
| `port` | | Destination UDP port |
| `adr` | `addr`, `address` | OSC address |
| `low` | `min`, `lo` | Output range minimum |
| `high` | `max`, `hi` | Output range maximum |
| `period` | | Send period in ms (20–60000) |

### 4.2 `delete` / `remove`

Address: `/annieData{dev}/patch/{name}/delete`  
Payload: none  
Action: stop the send task, clear patch pointer from all messages, remove patch.

### 4.3 `start` / `enable` / `go`

Address: `/annieData{dev}/patch/{name}/start`  
Payload: none  
Action: create FreeRTOS send task; begins sending all enabled messages at the configured period.

### 4.4 `stop` / `disable` / `mute`

Address: `/annieData{dev}/patch/{name}/stop`  
Payload: none  
Action: stop the send task (patch config is preserved).

### 4.5 `addmsg` / `add`

Address: `/annieData{dev}/patch/{name}/addmsg`  
Payload: comma-separated message names — `"msg1, msg2, msg3"`

### 4.6 `removemsg` / `rmmsg`

Address: `/annieData{dev}/patch/{name}/removemsg`  
Payload: single message name

### 4.7 `period` / `rate`

Address: `/annieData{dev}/patch/{name}/period`  
Payload: integer or quoted string — `"50"` (milliseconds, clamped to 20–60000)

### 4.8 `override`

Address: `/annieData{dev}/patch/{name}/override`  
Payload: comma-separated field names

When a field is overridden the patch's value replaces the message's value at send time.

| Value | Effect |
|-------|--------|
| `ip`, `port`, `adr`, `low`, `high` | Override that field |
| `scale` / `bounds` | Shorthand for `low, high` |
| `all` | Override every field |
| `none` / `clear` | Override nothing |
| `-ip`, `-port`, etc. | Disable override for that field |

### 4.9 `adrmode` / `addressmode`

Address: `/annieData{dev}/patch/{name}/adrmode`  
Payload: mode name

| Mode | Aliases | Behaviour |
|------|---------|-----------|
| `fallback` | `default`, `0` | Use message address; fall back to patch address if message has none (**default**) |
| `override` | `replace`, `1` | Patch address completely replaces message address |
| `prepend` | `pre`, `2` | `patch.adr + "/" + msg.adr` |
| `append` | `post`, `3` | `msg.adr + "/" + patch.adr` |

If either side is empty the mode degrades gracefully. Trailing `/` is stripped to avoid `//`.

### 4.10 `setall`

Address: `/annieData{dev}/patch/{name}/setall`  
Payload: config string (same format as message assign)  
Action: apply the config to every message in the patch.

### 4.11 `solo`

Address: `/annieData{dev}/patch/{name}/solo`  
Payload: message name  
Action: enable the named message; disable all others in the patch.

### 4.12 `unsolo` / `unmute` / `enableall`

Address: `/annieData{dev}/patch/{name}/unsolo`  
Payload: none  
Action: re-enable all messages in the patch.

### 4.13 `info`

Address: `/annieData{dev}/patch/{name}/info`  
Payload: none  
Reply address: `/reply{dev}/patch/{name}/info`  
Reply payload: verbose info string (see §7.2)

---

## 5. Structural Commands

### 5.1 Clone — `/annieData{dev}/clone/…`

| Address | Payload | Action |
|---------|---------|--------|
| `/clone/msg` | `"srcName, destName"` | Duplicate a message |
| `/clone/patch` | `"srcName, destName"` | Duplicate a patch (config + message list, not task state) |

### 5.2 Rename — `/annieData{dev}/rename/…`

| Address | Payload |
|---------|---------|
| `/rename/msg` | `"oldName, newName"` |
| `/rename/patch` | `"oldName, newName"` |

### 5.3 Move — `/annieData{dev}/move`

Payload: `"msgName, patchName"`  
Action: move a message from its current patch to a different patch.

---

## 6. Query Commands

### 6.1 List — `/annieData{dev}/list/…`

Optional verbose flag: pass string `"verbose"`, `"v"`, `"1"`, or `"true"` as the payload.

| Address | Reply address | Reply content |
|---------|---------------|---------------|
| `/list/msgs` or `/list/messages` | `/reply{dev}/list/msgs` | All message names (verbose: with params) |
| `/list/patches` | `/reply{dev}/list/patches` | All patch names (verbose: with params) |
| `/list/all` or `/list` | `/reply{dev}/list/all` | Patches then messages |

**Non-verbose list reply format:**

```
Messages (3):
  accelX
  accelY
  gyroZ
Patches (1):
  sensors
```

When count is zero: `Messages (0): none`.

**Verbose list reply format** (one space-separated line per item):

```
Messages (2):
  accelX [ON] ip:192.168.1.50 port:9000 adr:/sensor/x val:accelX low:0.00 high:1.00 patch:sensors
  gyroZ [OFF] ip:192.168.1.50 port:9000 adr:/sensor/z val:gyroZ low:0.00 high:1.00 patch:sensors
Patches (1):
  sensors [RUNNING, 50ms, 2 msgs] ip:192.168.1.50 port:9000 adr: low:0.00 high:1.00 adr_mode:fallback
```

The list reply is sent to the sender's IP/port. If the sender port is 0
the reply falls back to the configured status destination.

### 6.2 Direct — `/annieData{dev}/direct/{name}`

Payload: full config string (all message + patch fields including `period`)

One command that:
1. Creates/updates message `{name}` with the given sensor value and destination fields
2. Creates/updates patch `{name}` with destination and period fields
3. Adds the message to the patch
4. Starts the patch

Example:
```
/annieData/bart/direct/quickSend
Payload: "value:accelX, ip:192.168.1.50, port:9000, adr:/sensor/x, period:50, low:0, high:255"
```

---

## 7. Reply Formats

### 7.1 Message verbose info string

```
{name} [{ON|OFF}] [ip:{ip}] [port:{port}] [adr:{adr}] [val:{stream}] [low:{f}] [high:{f}] [patch:{patch}] [ori_only:{name}] [ori_not:{name}]
```

Fields appear only when they have been explicitly set. Floats are
formatted with 2 decimal places.

### 7.2 Patch verbose info string

```
{name} [{RUNNING|STOPPED}, {period}ms, {N} msgs] [ip:{ip}] [port:{port}] [adr:{adr}] [low:{f}] [high:{f}] adr_mode:{mode} [override:{fields}]
```

`adr_mode` is always present. `override` only appears when at least one
field is overridden; the value is a comma-separated list of field names
(e.g. `ip,port`).

### 7.3 Global command replies

| Command | Reply address | Reply payload |
|---------|---------------|---------------|
| `blackout` | `/reply{dev}/blackout` | `"BLACKOUT"` |
| `restore` | `/reply{dev}/restore` | `"RESTORE"` |
| `dedup on` | `/reply{dev}/dedup` | `"DEDUP ON"` |
| `dedup off` | `/reply{dev}/dedup` | `"DEDUP OFF"` |
| `save` | `/reply{dev}/save` | `"Saved N objects"` |
| `load` | `/reply{dev}/load` | `"Loaded N objects"` |

---

## 8. Data Streams (Sensor Values)

Both builds share the same 12-element `data_streams[]` array. All values
are normalised to `[0, 1]`.

| Name | Aliases | Index | Description |
|------|---------|-------|-------------|
| `accelX` | `accelx` | 0 | X-axis accelerometer |
| `accelY` | `accely` | 1 | Y-axis accelerometer |
| `accelZ` | `accelz` | 2 | Z-axis accelerometer |
| `accelLength` | `accellen`, `alen` | 3 | Acceleration magnitude |
| `gyroX` | `gyrox` | 4 | X-axis gyroscope |
| `gyroY` | `gyroy` | 5 | Y-axis gyroscope |
| `gyroZ` | `gyroz` | 6 | Z-axis gyroscope |
| `gyroLength` | `gyrolen`, `glen` | 7 | Gyroscope magnitude |
| `baro` | | 8 | Barometric pressure |
| `eulerX` | `eulerx` | 9 | Roll (Euler angle) |
| `eulerY` | `eulery` | 10 | Pitch (Euler angle) |
| `eulerZ` | `eulerz` | 11 | Yaw (Euler angle) |

On the **Bart** build these are filled with simulated sine waves at
various frequencies. On **AB7** they are live sensor readings from the
BNO085 IMU.

---

## 9. Global Commands

### 9.1 `blackout`

Address: `/annieData{dev}/blackout` — stop all patch send tasks immediately.

### 9.2 `restore`

Address: `/annieData{dev}/restore` — restart all patches that have messages.

### 9.3 `dedup`

Address: `/annieData{dev}/dedup`  
Payload: `"on"` / `"off"` (omit to toggle or query)  
Action: enable/disable duplicate-value suppression (skip OSC sends when value has not changed since last send).

---

## 10. Persistence Commands

### 10.1 Save

| Address | Payload | Action |
|---------|---------|--------|
| `/save` or `/save/all` | none | Save all messages and patches to NVS |
| `/save/msg` | message name | Save one message |
| `/save/patch` | patch name | Save one patch |

### 10.2 Load

| Address | Payload | Action |
|---------|---------|--------|
| `/load` or `/load/all` | none | Load all messages and patches from NVS |

### 10.3 NVS clear

Address: `/annieData{dev}/nvs/clear` — erase all OSC data from NVS (does not clear WiFi credentials).

---

## 11. Status Configuration

### 11.1 `status/config`

Address: `/annieData{dev}/status/config`  
Payload: config string with `ip`, `port`, `adr` keys  
Action: configure where the device sends status/info/warning/error messages.

### 11.2 `status/level`

Address: `/annieData{dev}/status/level`  
Payload: `debug` / `info` / `warning` / `error`

Status replies use the format `[LEVEL] category: message`.

---

## 12. Ori Commands (AB7 build only)

These commands exist only when the firmware is compiled with `-DAB7_BUILD`.
Gooey must gate ori-related UI on the `ori-enabled` body class and only
send ori commands to AB7 devices.

### 12.1 `ori/save`

Address: `/annieData{dev}/ori/save` or `/annieData{dev}/ori/save/{name}`  
Payload (optional): ori name (takes precedence over address segment)  
Reply: `/reply{dev}/ori/save` → `"Saved: oriName"` or error

Auto-names as `ori_0`, `ori_1`, … if no name given. Overwrites if name exists.

### 12.2 `ori/delete`

Address: `/annieData{dev}/ori/delete/{name}`  
Payload (optional): ori name  
Reply: `/reply{dev}/ori/delete` → `"Deleted: oriName"` or error

### 12.3 `ori/clear`

Address: `/annieData{dev}/ori/clear`  
Reply: `/reply{dev}/ori/clear` → `"All oris cleared"`

### 12.4 `ori/list`

Address: `/annieData{dev}/ori/list`  
Reply: `/reply{dev}/ori/list` → comma-separated names; active ori marked with `(*)`

### 12.5 `ori/threshold`

Address: `/annieData{dev}/ori/threshold`  
Payload: float (rad/s, default 1.5 ≈ 86°/s)  
Reply: `/reply{dev}/ori/threshold` → `"threshold: X.XX"`

### 12.6 `ori/active`

Address: `/annieData{dev}/ori/active`  
Reply: `/reply{dev}/ori/active` → active ori name or `"(none)"`

### 12.7 Ori matching algorithm

Geodesic distance: `angle = 2 · acos(|q_saved · q_current|)` (radians).
The active ori is the saved orientation with the smallest angle to the
current reading. When gyroscope magnitude exceeds `motion_threshold` the
matcher freezes on the last stable match (motion gating).

### 12.8 Conditional message sending (AB7 only)

Messages may carry ori conditions in their config:

```
ori_only:light1   — send only when light1 is active
ori_not:dark      — send only when dark is NOT active
```

Both conditions are checked independently; a message that fails either
condition is skipped for that send cycle.

---

## 13. Build Differences: Bart vs AB7

| Feature | Bart (`pio run -e bart`) | AB7 (`pio run -e ab7` / `ab7-bno085`) |
|---------|--------------------------|----------------------------------------|
| IMU | Simulated sine waves | BNO085 real IMU |
| Sensor task | `data_streams_task` on core 1 | `sensor_task` pinned to core 1 (SPI interrupt on core 1) |
| Euler/accel/gyro | Simulated at fixed Hz | Live readings normalised to `[0, 1]` |
| Ori system | Not present | Full save/match/gate pipeline |
| `ori_only` / `ori_not` | Parsed but always pass | Actively evaluated |
| Button (GPIO 0) | Not used | Hold 3 s clears provisioning; tap saves ori |
| Build flag | (none) | `-DAB7_BUILD`; BNO variant also sets `-DAB7_IMU_BNO085` |

---

## 14. Firmware Encoding Rules

| Data type | Wire representation |
|-----------|---------------------|
| Config payload | Single OSC string argument |
| Float in config | Decimal literal, e.g. `"0.5"` |
| Bool in config | `true`/`1`/`yes`/`on` or `false`/`0`/`no`/`off` |
| Period | Integer milliseconds as string `"50"` |
| Enabled state | `[ON]` / `[OFF]` in verbose strings |
| Patch run state | `[RUNNING]` / `[STOPPED]` in verbose strings |
| Float in reply | 2 decimal places, e.g. `0.00`, `255.50` |
| Override list in reply | Comma-separated with no spaces, e.g. `ip,port,adr` |
| Address mode in reply | Lowercase label: `fallback`, `override`, `prepend`, `append` |
| Message list in patch reply | `+`-separated names, e.g. `msg1+msg2+msg3` |

---

## 15. Registry Limits and Constraints

- Max messages and patches are compile-time constants (`MAX_OSC_MESSAGES`,
  `MAX_OSC_PATCHES`) — creation fails with an error status reply when full.
- Deletion uses swap-with-last (O(1)); registry indices can change after a
  delete.
- All registry mutations and send operations are mutex-protected via two
  FreeRTOS semaphores (one for the registry, one for UDP sends).
- `data_streams[]` values are `volatile float`; sensor task writes, patch
  send tasks read without a mutex (atomic on ESP32).
