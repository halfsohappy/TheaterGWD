# bc127 DMX Controller — OSC Guide

This guide documents every OSC command accepted by the **bc127** DMX
controller — an M5Stack CoreS3 with the DMX Base that receives OSC over
WiFi and outputs a single DMX-512 universe.

No programming required. Send these messages from QLab, TouchDesigner,
a lighting console, Max/MSP, or any other OSC-capable software.

---

## Table of Contents

- [Device Setup (Provisioning)](#device-setup-provisioning)
- [OSC Address Format](#osc-address-format)
- [Direct Channel Control](#direct-channel-control)
- [Fixture Control](#fixture-control)
- [Group Control](#group-control)
- [Colour by Name (XKCD)](#colour-by-name-xkcd)
- [Colour by Hex RGB](#colour-by-hex-rgb)
- [Blackout / Restore](#blackout--restore)
- [Fixture Map](#fixture-map)
- [Display](#display)
- [Quick Reference Card](#quick-reference-card)
- [Practical Examples](#practical-examples)

---

## Device Setup (Provisioning)

Power on the controller. If it has never been configured (or has been
factory-reset):

1. It creates a WiFi hotspot called **"annieData DMX Setup"**.
2. Connect from your phone or laptop.
3. A captive-portal page opens (or navigate to `192.168.4.1`).
4. Fill in:
   - **WiFi name (SSID)** — your production network.
   - **WiFi password**
   - **Static IP** — enter an address like `192.168.1.50`, or type `dhcp`
     for automatic assignment.
   - **OSC Port** — the UDP port the controller listens on (default `8000`).
5. Submit. The controller reboots and joins the network.

After provisioning, the device is ready to receive OSC commands on the
configured port.

---

## OSC Address Format

Every command starts with:

```
/annieData/dmx/{command...}
```

All command segments are **case-insensitive** and **underscore-insensitive**
(handled by `normalise_cmd`). So `blackOut`, `black_out`, and `blackout`
all match.

Payloads are a **single argument** — either a string, an integer, or a
float. Floats are truncated to integers internally.

---

## Direct Channel Control

Set a single DMX channel (1–512) to a value (0–255):

| Address | Payload | Effect |
|---|---|---|
| `/annieData/dmx/1` | `"255"` | Channel 1 → full |
| `/annieData/dmx/42` | `"128"` | Channel 42 → 50 % |
| `/annieData/dmx/12` | `"0"` | Channel 12 → off |

The channel number is taken from the address path — no extra address
segments needed.

---

## Fixture Control

Address a fixture by its **head number** (1–22 in the default patch) and
an **attribute name**:

```
/annieData/dmx/fix/{head}/{attribute}   payload: "0"–"255"
```

`fix` can also be written as `fixture`.

### Attributes

| Attribute | Aliases | Dimmer | ColorSourcePar |
|---|---|---|---|
| `dimmer` | `dim`, `intensity` | Sets the single channel | Sets dimmer offset (+0) |
| `red` | `r` | — | Sets red offset (+1) |
| `green` | `g` | — | Sets green offset (+2) |
| `blue` | `b` | — | Sets blue offset (+3) |
| `shutter` | `strobe` | — | Sets shutter offset (+4) |
| `color` | `colour` | Sets perceived brightness | Sets RGB + dimmer=255 (see [XKCD colours](#colour-by-name-xkcd)) |
| `rgb` | `hex` | Sets perceived brightness | Sets RGB + dimmer=255 (see [hex RGB](#colour-by-hex-rgb)) |

### Examples

| Address | Payload | Effect |
|---|---|---|
| `/annieData/dmx/fix/1/dimmer` | `"200"` | Head 1 (dimmer) → 200 |
| `/annieData/dmx/fix/13/red` | `"255"` | Head 13 (par) red → full |
| `/annieData/dmx/fix/15/color` | `"teal"` | Head 15 → XKCD "teal" colour |
| `/annieData/dmx/fix/20/rgb` | `"ff8800"` | Head 20 → orange via hex |

---

## Group Control

Apply a command to every fixture in a named group:

```
/annieData/dmx/group/{name}/{attribute}   payload: "0"–"255"
```

`group` can also be written as `grp`.

### Default Groups

| Group Name | Heads |
|---|---|
| `dimmers` | 1–12 (generic dimmers) |
| `dimmer` | 13–17 (first five pars) |
| `colorsourcepar` | 18–22 (last five pars) |
| `pars` | 13–22 (all ten pars) |
| `all` | 1–22 (every fixture) |

Group names are case-insensitive.

### Examples

| Address | Payload | Effect |
|---|---|---|
| `/annieData/dmx/group/all/dimmer` | `"0"` | Every fixture → off |
| `/annieData/dmx/group/pars/color` | `"lavender"` | All pars → XKCD lavender |
| `/annieData/dmx/group/dimmers/dimmer` | `"128"` | Dimmers 1–12 → 50 % |
| `/annieData/dmx/grp/colorsourcepar/rgb` | `"00ff88"` | Pars 18–22 → green-cyan |

---

## Colour by Name (XKCD)

Use the `color` (or `colour`) attribute with a colour name from the
[XKCD colour survey](https://xkcd.com/color/rgb/). The lookup is
case-insensitive and includes hundreds of entries (reds, pinks, oranges,
yellows, greens, blues, purples, browns, greys, whites, and more).

For a **ColorSourcePar** fixture, the named colour sets R, G, B channels
and forces dimmer to 255. For a **dimmer** fixture, the perceived
brightness of the colour is applied.

If the name is not found, the command is silently ignored.

**Examples:** `"dark pink"`, `"teal"`, `"burnt orange"`, `"lavender"`,
`"seafoam green"`, `"rust red"`, `"sky blue"`.

---

## Colour by Hex RGB

Use the `rgb` (or `hex`) attribute with a 6-digit hex string
(no `#` prefix):

```
/annieData/dmx/fix/13/rgb   "c79fef"
```

Behaviour is the same as named colours — RGB channels are set and dimmer
is forced to 255 on par fixtures. Dimmer fixtures receive the perceived
brightness.

---

## Blackout / Restore

| Address | Payload | Effect |
|---|---|---|
| `/annieData/dmx/blackout` | *(any)* | Output all-zero universe. Stored values are **preserved** internally. |
| `/annieData/dmx/restore` | *(any)* | Resume sending the stored channel values. |

During blackout the display header shows **BLACKOUT** in red. After
restore it shows **LIVE** in green.

---

## Fixture Map

The default patch (from the ChamSys QuickQ show file `bc127.shw`):

| Head | Type | DMX Start | Channels | Notes |
|---|---|---|---|---|
| 1–12 | Generic Dimmer | 1–12 | 1 each | One channel per dimmer |
| 13 | ETC ColorSourcePar | 13 | 5 | Dim, R, G, B, Shutter |
| 14 | ETC ColorSourcePar | 18 | 5 | |
| 15 | ETC ColorSourcePar | 23 | 5 | |
| 16 | ETC ColorSourcePar | 29 | 5 | Gap at DMX 28 |
| 17 | ETC ColorSourcePar | 34 | 5 | |
| 18 | ETC ColorSourcePar | 39 | 5 | |
| 19 | ETC ColorSourcePar | 44 | 5 | |
| 20 | ETC ColorSourcePar | 49 | 5 | |
| 21 | ETC ColorSourcePar | 54 | 5 | |
| 22 | ETC ColorSourcePar | 60 | 5 | Gap at DMX 59 |

**ColorSourcePar channel order** (offset from DMX start):

| Offset | Attribute |
|---|---|
| +0 | Dimmer |
| +1 | Red |
| +2 | Green |
| +3 | Blue |
| +4 | Shutter |

---

## Display

The CoreS3 LCD shows two views, toggled by **touching the screen**:

1. **OSC Feed** — a scrolling log of recent incoming OSC messages.
2. **DMX Monitor** — an 8 × 8 grid showing channels 1–64 with live
   values. Cell backgrounds light up proportionally to the channel value.

---

## Quick Reference Card

```
DIRECT CHANNEL
  /annieData/dmx/{ch}                          "0"–"255"

FIXTURE
  /annieData/dmx/fix/{head}/dimmer             "0"–"255"
  /annieData/dmx/fix/{head}/red                "0"–"255"
  /annieData/dmx/fix/{head}/green              "0"–"255"
  /annieData/dmx/fix/{head}/blue               "0"–"255"
  /annieData/dmx/fix/{head}/shutter            "0"–"255"
  /annieData/dmx/fix/{head}/color              "dark pink"
  /annieData/dmx/fix/{head}/rgb                "c79fef"

GROUP
  /annieData/dmx/group/{name}/dimmer           "0"–"255"
  /annieData/dmx/group/{name}/color            "teal"
  /annieData/dmx/group/{name}/rgb              "aabbcc"

BLACKOUT / RESTORE
  /annieData/dmx/blackout                      (any)
  /annieData/dmx/restore                       (any)

GROUPS: all, dimmers, pars, dimmer, colorsourcepar
HEADS:  1–12 dimmers, 13–22 ColorSourcePar
```

---

## Practical Examples

### Fade all dimmers to 50 %

```
/annieData/dmx/group/dimmers/dimmer  "128"
```

### Set par 13 to a warm amber

```
/annieData/dmx/fix/13/color  "amber"
```

### Set par 18 to a specific hex colour

```
/annieData/dmx/fix/18/rgb  "ff6600"
```

### Blackout, wait, restore

```
/annieData/dmx/blackout  "1"
  (pause)
/annieData/dmx/restore   "1"
```

### Set a single DMX channel directly

```
/annieData/dmx/44  "200"
```

This sets DMX channel 44 (which happens to be the dimmer of head 19)
to value 200.

### Kill all lights

```
/annieData/dmx/group/all/dimmer  "0"
```
