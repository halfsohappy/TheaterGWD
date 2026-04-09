# annieData Control Center — Full Stack Overview

> Architecture, technology choices, interactions between layers,
> and alternatives to consider at every level.

---

## Table of Contents

1. [Architecture at a Glance](#1--architecture-at-a-glance)
2. [Layer-by-Layer Breakdown](#2--layer-by-layer-breakdown)
   - [2.1 Python Backend (Flask + Flask-SocketIO)](#21-python-backend)
   - [2.2 Frontend (Vanilla JS + CSS custom properties)](#22-frontend)
   - [2.3 Real-Time Layer (Socket.IO)](#23-real-time-layer)
   - [2.4 OSC Protocol Layer (pythonosc)](#24-osc-protocol-layer)
   - [2.5 Desktop Shell (Tauri 2)](#25-desktop-shell--tauri-2)
   - [2.6 Desktop Shell — Alternative (pywebview)](#26-desktop-shell--pywebview)
   - [2.7 Icons (Bootstrap Icons)](#27-icons--bootstrap-icons)
   - [2.8 Fonts (Google Fonts)](#28-fonts--google-fonts)
   - [2.9 Build & Packaging](#29-build--packaging)
   - [2.10 Deployment (Docker)](#210-deployment--docker)
3. [How the Layers Interact](#3--how-the-layers-interact)
4. [The Tauri "Sidecar" Explained](#4--the-tauri-sidecar-explained)
5. [What "Losing Interactivity" Means with shadcn/ui](#5--what-losing-interactivity-means-with-shadcnui)
6. [Alternatives at Every Level](#6--alternatives-at-every-level)
   - [6.1 Backend Framework](#61-backend-framework)
   - [6.2 Frontend Framework / UI Library](#62-frontend-framework--ui-library)
   - [6.3 CSS / Styling](#63-css--styling)
   - [6.4 Icon Set (Replacing Bootstrap Icons)](#64-icon-set--replacing-bootstrap-icons)
   - [6.5 Real-Time Transport](#65-real-time-transport)
   - [6.6 Desktop Shell](#66-desktop-shell)
   - [6.7 OSC Library](#67-osc-library)
7. [shadcn/ui Alternatives & Other Modernization Paths](#7--shadcnui-alternatives--other-modernization-paths)
8. [Summary — What's Worth Changing?](#8--summary--whats-worth-changing)

---

## 1  Architecture at a Glance

```
┌──────────────────────────────────────────────────────────────────────┐
│  Desktop (Tauri 2)                                                   │
│  ┌────────────────────────────────┐  ┌─────────────────────────────┐ │
│  │ Rust process                   │  │ WebView (system browser)    │ │
│  │  • native menus                │  │  • loading.html (splash)    │ │
│  │  • auto-updater                │  │  • then → localhost:5254    │ │
│  │  • spawns sidecar              │  │                             │ │
│  │  • macOS LAN permission        │  │  ┌─────────────────────┐   │ │
│  │  • kills sidecar on close      │  │  │ Frontend            │   │ │
│  └──────────┬─────────────────────┘  │  │  vanilla JS (IIFE)  │   │ │
│             │ spawn                   │  │  CSS custom props   │   │ │
│             ▼                         │  │  Socket.IO client   │   │ │
│  ┌────────────────────────────────┐  │  │  Bootstrap Icons    │   │ │
│  │ Sidecar: gooey-server          │  │  └─────────┬───────────┘   │ │
│  │  (PyInstaller one-file binary) │  │            │ WebSocket     │ │
│  │  Flask + Flask-SocketIO        │◄─┤────────────┘               │ │
│  │  pythonosc (UDP)               │  │                             │ │
│  │  pyserial                      │  └─────────────────────────────┘ │
│  └──────────┬─────────────────────┘                                  │
│             │ UDP                                                     │
│             ▼                                                         │
│  ┌──────────────────────────┐                                        │
│  │ ESP32-S3 devices (Bart)  │                                        │
│  │  OSC over WiFi           │                                        │
│  └──────────────────────────┘                                        │
└──────────────────────────────────────────────────────────────────────┘
```

**Web-only mode** (no Tauri): `python run.py` starts the same Flask
server on port 5050 and opens a browser tab. Everything works
identically — Tauri is purely an optional native wrapper.

---

## 2  Layer-by-Layer Breakdown

### 2.1 Python Backend

| Property | Value |
|---|---|
| Framework | **Flask 3.0+** with **Flask-SocketIO 5.3+** |
| Entry point (web) | `gooey/run.py` → port 5050 |
| Entry point (sidecar) | `gooey/run_server.py` → port 5254 |
| Core module | `gooey/app/main.py` (1,288 lines) |
| Async mode | `threading` (not eventlet/gevent) |
| Template engine | Jinja2 (ships with Flask) |

**What it does:**

- **28 REST routes** (`/api/*`) — OSC send/receive/bridge, device
  registry, scenes, shows, scripting, presets
- **13 Socket.IO event handlers** — serial port I/O, script execution,
  remote session management, keep-alive pings
- **OSC engine** (`app/osc_handler.py`) — wraps `pythonosc` for
  send, receive, bridge, and repeated-send operations
- **Script runner** (`app/script_runner.py`) — executes user Python
  scripts with stdout/stderr piped to the frontend
- **Thread-safe device registry** — in-memory, protected by
  `threading.Lock()`

**Dependencies** (`requirements.txt`):

| Package | Version | Purpose |
|---|---|---|
| `flask` | ≥ 3.0 | Web framework, routing, Jinja2 templates |
| `flask-socketio` | ≥ 5.3 | WebSocket layer over Flask |
| `python-osc` | ≥ 1.8 | OSC UDP send/receive (`pythonosc`) |
| `pyserial` | ≥ 3.5 | Serial port enumeration & I/O |
| `markdown` | ≥ 3.7 | Server-side Markdown → HTML for docs |
| `qrcode` | ≥ 7.4 | QR code generation for mobile remote |

Total: **6 runtime Python dependencies.** No database, no ORM, no auth.

---

### 2.2 Frontend

| Property | Value |
|---|---|
| Language | Vanilla JavaScript (ES5-ish, IIFE wrapper) |
| Framework | **None** — pure DOM manipulation |
| Main file | `app/static/js/app.js` (5,049 lines) |
| Template | `app/templates/index.html` (1,380 lines, Jinja2) |
| Stylesheet | `app/static/css/style.css` (3,305 lines) |

**Key patterns:**

- **IIFE scope isolation**: `(function () { "use strict"; ... })();`
- **Custom DOM helpers** (not jQuery):
  ```js
  var $  = function (sel) { return document.querySelector(sel); };
  var $$ = function (sel) { return document.querySelectorAll(sel); };
  ```
- **108 `className` / `classList` manipulations** in `app.js`
- **Dark mode** via `html.dark` class toggle + CSS custom properties
  (68 custom properties, light and dark variants)
- **No build step** — no bundler, no transpiler, no minifier.
  HTML references `app.js` and `style.css` directly with a `?v=`
  cache-bust query string.

**Design tokens** (CSS custom properties):

```css
:root {
  --bg: #ffffff;
  --accent: #90849c;
  --header-bg: #DAC7FF;      /* the signature lavender */
  --font: "Martian Mono", monospace;
  --font-title: "Playwrite DE Grund", cursive;
  --font-header: "Playwrite IE", cursive;
  /* …68 total custom properties */
}
.dark { /* overrides for dark mode */ }
```

---

### 2.3 Real-Time Layer

| Property | Value |
|---|---|
| Library | **Socket.IO** (Flask-SocketIO on server, socket.io.min.js on client) |
| Transport | WebSocket primary, HTTP long-polling fallback |
| Client init | `var socket = io({ transports: ["websocket", "polling"] });` |
| Bundled | `socket.io.min.js` shipped as a static file (no CDN) |

**Event categories:**

| Category | Events | Purpose |
|---|---|---|
| OSC traffic | `osc_message` | Log all OSC activity to the live feed |
| Serial | `serial_list_ports`, `serial_connect`, `serial_data`, `serial_send`, `serial_error`, `serial_disconnected` | Direct serial I/O from browser |
| Scripting | `script_run`, `script_stop`, `script_status`, `script_output`, `script_stopped` | User script execution |
| Remote | `remote_configure`, `remote_send`, `remote_reply`, `remote_error` | Mobile remote OSC proxy |
| Lifecycle | `connect`, `disconnect`, `ping_server` | Connection management |

---

### 2.4 OSC Protocol Layer

| Property | Value |
|---|---|
| Library | **`pythonosc`** (`python-osc` on PyPI) |
| Transport | Raw UDP sockets |
| Address format | `/annieData/{device_adr}/{command}` |

**Operations exposed via REST API:**

| Endpoint | What it does |
|---|---|
| `POST /api/send` | Single OSC message to `host:port` |
| `POST /api/send/repeat` | Repeating OSC message at `interval_ms` |
| `POST /api/send/json` | Batch send multiple messages |
| `POST /api/recv/start` | Start a UDP listener on a port |
| `POST /api/bridge/start` | Forward traffic between ports |
| `POST /api/stop-all` | Kill all active senders/receivers (Blackout) |

Each received OSC message is broadcast to the frontend in real time
via the `osc_message` Socket.IO event.

---

### 2.5 Desktop Shell — Tauri 2

| Property | Value |
|---|---|
| Framework | **Tauri 2** (Rust core) |
| Config | `gooey/src-tauri/tauri.conf.json` |
| Backend | `gooey/src-tauri/src/lib.rs` (280 lines) |
| Sidecar | `gooey-server` (PyInstaller binary) |
| Plugins | `tauri-plugin-shell`, `tauri-plugin-updater`, `tauri-plugin-dialog` |
| Window | System WebView (WebKit on macOS, WebView2 on Windows) |
| Build | `npm run tauri build` (Tauri CLI v2) |

**What the Rust code does:**

1. Builds native menus (File, Edit, Help) that call into the web page
   via `window.eval("…")`
2. Spawns the PyInstaller sidecar (`gooey-server`)
3. Polls `http://127.0.0.1:5254` until Flask is ready (30 s timeout)
4. Navigates the WebView from `loading.html` → `http://127.0.0.1:5254`
5. Kills the sidecar process when the window closes
6. Background auto-update check against GitHub Releases
7. macOS: triggers local-network permission dialog

> See [Section 4](#4--the-tauri-sidecar-explained) for a detailed
> explanation of the sidecar pattern.

---

### 2.6 Desktop Shell — pywebview

| Property | Value |
|---|---|
| File | `gooey/app_desktop.py` (~40 lines) |
| Library | **pywebview** |

Lightweight alternative: starts Flask in a daemon thread, waits for
it to respond, then opens a native window pointed at `localhost`.
No native menus, no auto-updater, no sidecar — just a window around
the web app. Useful for quick desktop testing without the full Tauri
build pipeline.

---

### 2.7 Icons — Bootstrap Icons

| Property | Value |
|---|---|
| Version | 1.11.3 |
| Source | CDN (`cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css`) |
| Usage | `<i class="bi bi-plus-lg"></i>` (16 icon references in `index.html`, many more in JS) |
| Framework | **Icon font only** — not the Bootstrap CSS framework or Bootstrap JS |

**Important clarification:** gooey does **not** use Bootstrap the CSS
framework. It uses only the **Bootstrap Icons** icon font, loaded as a
single CSS file from a CDN. The entire layout, theming, and component
styling is custom CSS (3,305 lines in `style.css`).

---

### 2.8 Fonts — Google Fonts

| Font | CSS variable | Usage |
|---|---|---|
| **Martian Mono** | `--font` | Body text, code, tables — monospace |
| **Playwrite DE Grund** | `--font-title` | Navigation tabs |
| **Playwrite IE** | `--font-header` | Page title / branding |

Loaded from Google Fonts CDN. No local font files.

---

### 2.9 Build & Packaging

| Target | Tool | Output |
|---|---|---|
| Web server | `pip install .` or `python run.py` | Running Flask process |
| Desktop sidecar | **PyInstaller** (`GooeyServer.spec`) | `dist/gooey-server` (one-file binary) |
| Desktop app | **Tauri CLI** (`npm run tauri build`) | `.dmg` / `.msi` / `.AppImage` with bundled sidecar |
| Docker image | `Dockerfile` | `python:3.12-slim` container on port 5000 |
| Homebrew | `Formula/gooey.rb` | `pip install` inside brew-managed venv |

**Build pipeline for desktop release:**

```
1. pyinstaller GooeyServer.spec
      → dist/gooey-server

2. cp dist/gooey-server src-tauri/binaries/gooey-server-{triple}
      (e.g. gooey-server-aarch64-apple-darwin)

3. npm run tauri build
      → target/release/bundle/ (dmg, msi, AppImage, deb)
```

---

### 2.10 Deployment — Docker

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "run.py", "--host", "0.0.0.0", "--no-browser"]
```

- Non-root user (`gooey`) for security
- Health check: HTTP ping on port 5000
- Volume: `/app/data/shows` for persistent show library
- Demo mode: `Dockerfile.demo` serves a read-only demo instance

---

## 3  How the Layers Interact

```
 Browser / WebView
      │
      ├── HTTP GET /  ───────────────►  Flask serves index.html (Jinja2)
      │                                      ├── style.css (custom properties)
      │                                      ├── app.js (vanilla JS)
      │                                      └── socket.io.min.js
      │
      ├── WebSocket ─────────────────►  Flask-SocketIO
      │   (socket.io)                        ├── osc_message  ◄── OSC receiver
      │                                      ├── serial_data  ◄── pyserial
      │                                      └── script_output ◄── subprocess
      │
      ├── POST /api/send ────────────►  Flask REST route
      │                                      └── pythonosc → UDP → ESP32
      │
      └── POST /api/recv/start ──────►  Flask REST route
                                             └── pythonosc UDP listener
                                                  └── emit("osc_message") → WebSocket
```

**The key insight**: Flask is both the HTTP server (serving pages and
REST API) *and* the WebSocket server (Flask-SocketIO). The frontend
talks to a single origin using two transports: HTTP for commands,
WebSocket for streaming data.

**In Tauri mode**, the flow adds one layer:

```
 Tauri (Rust)
   │
   ├── spawns gooey-server binary (PyInstaller)
   │       └── Flask on port 5254
   │
   └── WebView navigates to http://127.0.0.1:5254
              └── (same HTTP + WebSocket flow as above)
```

---

## 4  The Tauri "Sidecar" Explained

### What is a sidecar?

In Tauri, a **sidecar** is an external executable that ships *inside*
the app bundle but runs as a **separate process**. Tauri's Rust core
spawns it at startup and manages its lifecycle.

### Why does gooey need one?

Tauri's native frontend is a system WebView. It can render HTML/CSS/JS,
but it **cannot run Python**. gooey's backend is a Python Flask server
that handles OSC, serial I/O, and device management — all things that
must happen server-side.

The sidecar solves this: **package the entire Python backend as a
single standalone binary** (via PyInstaller), and have Tauri launch it
as a child process.

### How it works step by step

```
 1. User launches annieData.app (or .exe)
 2. Tauri shows loading.html (splash screen with spinner)
 3. Tauri's Rust code runs start_sidecar():
    a. Triggers macOS local-network permission dialog (if needed)
    b. Calls app.shell().sidecar("gooey-server").spawn()
       → This finds src-tauri/binaries/gooey-server-{arch}
       → Spawns it as a child process
    c. Forwards stdout/stderr to the host terminal for debugging
 4. Polls http://127.0.0.1:5254 every 200ms for up to 30 seconds
 5. Once Flask responds:
    a. Navigates the WebView from loading.html → http://127.0.0.1:5254
    b. The full web UI appears
 6. When the user closes the window:
    a. Window close event fires
    b. Rust kills the sidecar child process
```

### Why not embed Python in Rust?

Embedding CPython in Rust (via PyO3) would avoid the sidecar but
introduces massive complexity: managing the Python runtime, GIL
interactions, bundling pip packages. The sidecar approach is simpler:
PyInstaller produces a self-contained binary with Python, Flask, and
all dependencies baked in. Tauri just needs to spawn it and wait.

### Sidecar vs. Tauri Commands

Tauri also supports **commands** — Rust functions that the frontend
can call directly via `invoke()`. gooey doesn't use these because the
entire business logic is in Python. The Rust code only handles:
native menus, sidecar lifecycle, auto-updates, and the macOS
local-network permission trick.

---

## 5  What "Losing Interactivity" Means with shadcn/ui

The previous analysis noted that shadcn/ui's "React-centric
interactivity doesn't transfer to vanilla JS." Here's what that means
concretely.

### What shadcn/ui actually is

shadcn/ui is a **collection of copy-paste React component source code**
built on two foundations:

1. **Tailwind CSS** — utility classes for styling
2. **Radix UI** — a React headless component library providing
   accessible, interactive primitives (dropdown menus, dialogs,
   popovers, comboboxes, tabs, toggles, etc.)

When you install a shadcn component (e.g. `npx shadcn@latest add
dropdown-menu`), you get a `.tsx` file that imports Radix primitives
and styles them with Tailwind classes.

### What transfers to vanilla JS

| shadcn layer | Transfers? | Details |
|---|---|---|
| **Tailwind utility classes** | ✅ Yes | `bg-primary`, `rounded-md`, `text-sm` — pure CSS, works in any HTML |
| **CSS variable theming** | ✅ Yes | `--background`, `--primary`, `--muted`, `--ring` — standard CSS custom properties |
| **Dark mode pattern** | ✅ Yes | `dark:bg-background` — Tailwind's `darkMode: 'class'` works the same way gooey already toggles dark |
| **Visual design language** | ✅ Yes | The rounded corners, muted borders, ring focus states, subtle shadows — all reproducible in any CSS |
| **`@apply` component classes** | ✅ Yes | Extract utilities into semantic names (`btn-primary`, `btn-ghost`) — the PoC already demonstrates this |

### What does NOT transfer

| Radix behavior | Why it doesn't transfer |
|---|---|
| **Dropdown Menu** | Radix manages focus trapping, arrow-key navigation, `aria-expanded`, portal rendering, click-outside dismissal, sub-menus. In vanilla JS, you'd write this yourself. |
| **Dialog / Sheet** | Radix handles focus lock, scroll lock, escape-to-close, aria attributes, animated mount/unmount. Without it you need a custom modal manager. |
| **Combobox / Command** | Radix provides typeahead search, highlighted option tracking, keyboard selection, virtual scrolling for large lists. This is complex state management. |
| **Popover positioning** | Radix uses Floating UI internally for auto-flip, auto-shift, collision detection against viewport edges. In vanilla JS you'd import Floating UI directly. |
| **Tooltip** | Radix handles show/hide delay, hover intent, touch-device detection, portal placement. |
| **Tabs** | Radix manages `role="tablist"`, `aria-selected`, roving tabindex, keyboard arrow navigation. |
| **Toggle / Switch** | Radix provides `role="switch"`, `aria-checked`, keyboard toggle. |

### What this means for gooey

gooey already has working versions of most of these interactions
(modals, dropdowns, tab navigation) implemented in `app.js`. They
work, but they're custom-built and may lack some accessibility
features that Radix provides for free.

**The practical impact**: adopting shadcn's *visual styling* (Tailwind
+ CSS variables) is straightforward and the PoC proves it. Adopting
shadcn's *interactive behaviors* would require either:

1. **Adopting React** — fundamental architecture change, full rewrite
2. **Using Radix-equivalent vanilla JS libraries** — see
   [Section 7](#7--shadcnui-alternatives--other-modernization-paths)
3. **Keeping existing JS interactions** — just adopt the CSS layer,
   which is what the PoC does

---

## 6  Alternatives at Every Level

### 6.1 Backend Framework

| Option | Pros | Cons | Effort |
|---|---|---|---|
| **Flask (current)** | Simple, team knows it, 6 deps, works | Not async-native, sync threading | — |
| **FastAPI** | Async-native, auto OpenAPI docs, type-safe | Requires ASGI server (uvicorn), Socket.IO needs `python-socketio[asyncio]`, migration of all routes | High |
| **Django** | Batteries-included (ORM, admin, auth) | Massive overkill — gooey has no database, no users | Very high |
| **Litestar** | Modern async, built-in WebSocket, dependency injection | Newer/smaller community, migration effort | High |
| **Starlette** | Minimal async ASGI, WebSocket built-in | Lower-level than Flask, need to rebuild routing patterns | Medium |

**Recommendation**: Flask is the right fit. The backend is small
(1,288 lines), has 6 dependencies, and the `threading` async mode
works well for the IO-bound OSC/serial operations. Migrating to
FastAPI gains little — the bottleneck is never the web framework.

---

### 6.2 Frontend Framework / UI Library

| Option | Pros | Cons | Effort |
|---|---|---|---|
| **Vanilla JS (current)** | Zero build step, direct DOM control, no framework lock-in, 5,049 lines already working | No component model, manual state management, accessibility gaps | — |
| **Preact** | 3 KB React-compatible, JSX, hooks, component model | Needs build step (Vite), must rewrite all 5K lines of JS into components | Very high |
| **Svelte** | Compile-time, tiny runtime, reactive by default | Needs build step, full rewrite, team unfamiliar | Very high |
| **Vue** | Gentle learning curve, single-file components, good docs | Needs build step, full rewrite | Very high |
| **htmx** | Zero-JS interactivity via HTML attributes, pairs well with Flask/Jinja2 | Socket.IO integration less natural, complex interactions (drag/drop, code editor) still need JS | Medium |
| **Alpine.js** | 15 KB, declarative (`x-data`, `x-show`, `x-on`), no build step | Only handles simple interactions, won't replace the complex card/table/editor logic | Low–Medium |
| **Lit** | Web Components standard, small runtime, no build required for simple cases | Component rewrite, less ecosystem than React/Vue | High |

**Recommendation**: The vanilla JS is working and well-structured
(IIFE, consistent conventions). The highest-value change would be
adding **Alpine.js** or **htmx** incrementally (no rewrite needed)
for simpler interactive patterns, while keeping the existing JS for
complex behaviors.

---

### 6.3 CSS / Styling

| Option | Pros | Cons | Effort |
|---|---|---|---|
| **Vanilla CSS + custom properties (current)** | Zero dependencies, full control, 68 design tokens | 3,305-line monolith, manual dark mode sync, no dead-code elimination | — |
| **Tailwind CSS** | Utility-first, JIT dead-code removal, `dark:` variants, huge ecosystem | Build step required, verbose HTML, learning curve | Medium (see `tailwind_migration.md`) |
| **Tailwind + shadcn/ui tokens** | All Tailwind benefits + accessible design language, HSL theming | Same build step con, React interactivity doesn't transfer | Medium |
| **Open Props** | CSS custom-property design tokens, no build step | Doesn't solve class naming or dead-code removal | Low |
| **UnoCSS** | Atomic CSS like Tailwind but faster builds | Smaller ecosystem, same HTML-verbosity trade-off | Medium |
| **CSS Modules** | Scoped class names, no collisions | Requires bundler (Vite/Webpack), heavy tooling for Flask | High |
| **Panda CSS** | Type-safe utility CSS, build-time extraction | Newer, React/Solid oriented, requires build step | High |

**Recommendation**: Tailwind CSS is the strongest option if a build
step is acceptable. The PoC in `poc/tailwind-header/` proves it works
and compiles to 16 KB vs 88 KB. If avoiding a build step is critical,
Open Props tokens can supplement the existing custom properties.

---

### 6.4 Icon Set — Replacing Bootstrap Icons

gooey currently loads **Bootstrap Icons 1.11.3** from a CDN — just the
icon font CSS (not the Bootstrap framework). Here are alternatives:

| Option | Icons | Size | Format | License | Notes |
|---|---|---|---|---|---|
| **Bootstrap Icons (current)** | 2,000+ | ~170 KB (CSS + woff2) | Icon font (CDN) | MIT | Familiar, no changes needed |
| **Lucide** | 1,500+ | ~20 KB (tree-shaken SVGs) | SVG or icon font | ISC | shadcn/ui's default icon set. Clean, consistent stroke style. Drop-in replacement for most `bi-*` icons |
| **Heroicons** | 300+ | ~15 KB | SVG | MIT | By Tailwind Labs. Beautiful but smaller set — may not cover all 16+ icons gooey uses |
| **Phosphor Icons** | 9,000+ | ~30 KB (tree-shaken) | SVG, icon font, React | MIT | Huge set, 6 weights, consistent design |
| **Tabler Icons** | 5,000+ | ~25 KB (tree-shaken) | SVG or icon font | MIT | Open source, very complete |
| **Iconify** | 200,000+ | On-demand loading | SVG (API or bundled) | Varies per set | Unified API across 150+ icon sets; use any set with one integration |
| **Self-hosted SVG sprites** | Custom | Minimal | SVG `<use>` | — | Maximum control, zero CDN dependency; manual curation required |

**Recommendation**: **Lucide** is the natural companion if moving
toward shadcn's visual language — it's what shadcn uses by default.
It covers all icons gooey currently uses (`plus`, `floppy`, `wrench`,
`folder-open`, `arrow-repeat`, `moon`, `bell`, `broadcast`,
`terminal`, `book`, `stop-circle`, `play-circle`). Switching is a
find-and-replace of `bi bi-*` → Lucide equivalents.

If you want to **drop the CDN dependency entirely** (better for
offline/embedded use), self-host an SVG sprite sheet with just the
~20 icons gooey needs.

---

### 6.5 Real-Time Transport

| Option | Pros | Cons | Effort |
|---|---|---|---|
| **Socket.IO (current)** | Mature, auto-reconnect, rooms, fallback transport, Flask integration | Extra dependency (client + server), abstraction over raw WS | — |
| **Raw WebSocket** | Native browser API, no client library needed, smaller | No auto-reconnect, no rooms, no fallback, manual message framing | Medium |
| **Server-Sent Events (SSE)** | Simpler than WS, auto-reconnect built-in, works through proxies | One-directional (server → client), gooey needs bidirectional for serial/scripting | Low (for feed-only) |
| **WebTransport** | Modern, multiplexed, unreliable datagrams (good for OSC-like data) | Browser support still limited, no Flask integration | High |

**Recommendation**: Socket.IO is the right choice. gooey uses
bidirectional events (serial I/O, script control, remote sessions),
auto-reconnect, and the library is already working. Raw WebSocket
would save ~40 KB of client-side JS but requires reimplementing
reconnection logic.

---

### 6.6 Desktop Shell

| Option | Pros | Cons | Effort |
|---|---|---|---|
| **Tauri 2 (current)** | Small bundle (~10 MB), system WebView, Rust performance, auto-updater, native menus | Rust toolchain required, sidecar complexity, platform-specific WebView quirks | — |
| **Electron** | Full Chromium (consistent rendering), huge ecosystem, easy Python integration | Large bundles (~150+ MB), high memory, Chromium update burden | Medium |
| **Neutralinojs** | Lightweight, system WebView like Tauri, simpler than Rust | Smaller community, fewer plugins, no auto-updater | Medium |
| **pywebview (current alt)** | Pure Python, zero Rust, trivial to set up | No native menus, no auto-updater, no bundling story, platform-specific rendering | — |
| **Wails** | Go-based Tauri alternative, system WebView, good UX | Go toolchain, sidecar for Python still needed | High |
| **PWA** | No shell needed, works on any device, installable | No serial port (WebSerial is Chromium-only), no auto-update control, limited OSC (no raw UDP in browser) | Low |

**Recommendation**: Tauri 2 is the right choice. The sidecar pattern
works well, the bundle is small, and the auto-updater is essential for
distributing updates to theater users. The Rust code is only 280 lines
and rarely needs changes.

---

### 6.7 OSC Library

| Option | Pros | Cons | Effort |
|---|---|---|---|
| **pythonosc (current)** | Mature, well-maintained, handles all OSC types | Synchronous API, threading-based | — |
| **aiosc** | Async OSC, pairs with asyncio event loop | Would need async backend (FastAPI/Starlette) | High |
| **pyliblo** | C-based (liblo), very fast | Requires C library installation, harder to bundle with PyInstaller | Medium |

**Recommendation**: `pythonosc` is fine. OSC message handling is not a
bottleneck.

---

## 7  shadcn/ui Alternatives & Other Modernization Paths

### 7.1 shadcn/ui-like systems (design tokens + component patterns)

| Option | Framework req. | Key idea | Vanilla JS compatible? |
|---|---|---|---|
| **shadcn/ui** | React + Radix | Copy-paste components, HSL CSS vars, Tailwind | Styling only; interactivity needs React |
| **Franken UI** | None (HTML + CSS) | shadcn visual design rebuilt with **UIkit** (plain HTML/CSS/JS). No React needed | ✅ **Yes** — uses HTML attribute API (`uk-dropdown`, `uk-modal`) instead of React |
| **daisyUI** | None (Tailwind plugin) | Pre-built Tailwind component classes (`btn`, `modal`, `dropdown`). Pure CSS, no JS runtime | ✅ **Yes** — add Tailwind plugin, use class names |
| **Preline UI** | None (Tailwind + vanilla JS) | Tailwind components with vanilla JS for interactions (dropdowns, modals, tabs) | ✅ **Yes** — designed for non-React use |
| **Flowbite** | None (Tailwind + vanilla JS) | Open-source Tailwind components with JS behaviors, interactive out of the box | ✅ **Yes** — has a vanilla JS library |
| **Headless UI** | React or Vue | Unstyled accessible primitives (like Radix but also supports Vue) | ❌ No — needs React or Vue |
| **Ark UI** | React, Vue, or Solid | State machine-based accessible components | ❌ No — needs a framework |
| **Park UI** | React, Vue, or Solid | shadcn-style components built on Ark UI | ❌ No — needs a framework |
| **Melt UI** | Svelte | Headless components for Svelte | ❌ No — needs Svelte |

### 7.2 Best options for gooey's vanilla JS stack

Given that gooey is vanilla JS with no framework:

#### Option A: Tailwind + daisyUI (lowest effort)

- Add Tailwind build step (as analyzed in `tailwind_migration.md`)
- Install `daisyui` as a Tailwind plugin
- Use semantic class names: `<button class="btn btn-primary">`,
  `<div class="modal">`, `<div class="dropdown">`
- **No JS changes** for styling; existing `app.js` interactions continue
  to work
- daisyUI provides 29 themes including a customizable dark mode

#### Option B: Tailwind + Preline UI (best interactivity)

- Add Tailwind build step
- Include Preline's vanilla JS file (~30 KB)
- Get accessible dropdowns, modals, tabs, tooltips, collapse
  **without React** — uses `data-hs-*` HTML attributes
- Replace gooey's custom modal/dropdown JS with Preline's built-in
  versions
- Still use `app.js` for domain-specific logic

#### Option C: Tailwind + Flowbite (middle ground)

- Add Tailwind build step
- Include Flowbite's vanilla JS file
- Get interactive dropdowns, modals, tooltips, tabs
- Good documentation, large component library
- Slightly heavier than daisyUI but more interactive

#### Option D: Franken UI (shadcn look without React)

- Uses UIkit under the hood (mature vanilla JS framework)
- Provides shadcn's visual aesthetic with `uk-*` attribute API
- Works without Tailwind (has its own CSS), but can integrate
- Biggest win: looks like shadcn, works like vanilla JS

### 7.3 Other modernization ideas

| Area | Idea | Benefit | Effort |
|---|---|---|---|
| **Code splitting** | Split `app.js` (5,049 lines) into ES modules | Easier to navigate, lazy-loadable, tree-shakeable | Medium |
| **TypeScript** | Add `tsconfig.json`, rename to `.ts`, add type annotations | Catch bugs at build time, better IDE support | Medium–High |
| **CSS → Tailwind** | Migrate `style.css` (3,305 lines) → utility classes | Dead-code elimination, synchronized dark mode | Medium (see `tailwind_migration.md`) |
| **Bundler** | Add Vite as dev server + build tool | Hot module reload, CSS/JS minification, tree-shaking | Low–Medium |
| **Accessibility audit** | Add `aria-*` attributes, keyboard navigation, focus management | Required for professional theater software | Low–Medium |
| **PWA manifest** | Add `manifest.json` + service worker | Installable on mobile/Chromebook, offline support | Low |
| **Self-host fonts/icons** | Download Martian Mono, Playwrite, Lucide to `static/` | Zero CDN dependency, works offline, faster first paint | Low |

---

## 8  Summary — What's Worth Changing?

### High value, low effort

| Change | Why |
|---|---|
| **Replace Bootstrap Icons with Lucide** (self-hosted SVGs) | Drop CDN dependency, better offline support, aligns with shadcn visual language, smaller payload |
| **Self-host fonts** | Eliminate Google Fonts CDN dependency, faster first paint |
| **Add Vite** (dev server only) | Hot reload during development, CSS/JS minification for production |
| **Split `app.js` into ES modules** | Developer experience — 5,049 lines in one file is painful |

### High value, medium effort

| Change | Why |
|---|---|
| **Tailwind CSS migration** | 16 KB vs 88 KB, synchronized dark mode, utility-first consistency (see `tailwind_migration.md`) |
| **Tailwind + daisyUI or Preline** | All Tailwind benefits + pre-built accessible component classes without React |

### Consider carefully

| Change | Why to consider | Why to hesitate |
|---|---|---|
| **Add Alpine.js** | Declarative interactions (`x-show`, `x-on`) for simpler UI patterns | Adds another paradigm alongside existing vanilla JS |
| **Adopt a framework (Preact/Svelte/Vue)** | Component model, reactive state, better testability | Full rewrite of 5,049 lines, build step mandatory, team must learn framework |
| **Switch to FastAPI** | Async-native, type-safe routes, auto-generated API docs | Flask is fine for this scale, migration effort with no visible user benefit |

### Keep as-is

| Layer | Why |
|---|---|
| **Flask** | Right-sized, 6 dependencies, team knows it |
| **Socket.IO** | Working bidirectional real-time, auto-reconnect |
| **pythonosc** | Mature, sufficient for OSC needs |
| **Tauri 2** | Small bundle, auto-updater, native menus, sidecar works |
| **pywebview** | Good lightweight alternative, trivial to maintain |
