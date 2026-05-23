# Smart Home IoT — Complete Build Info & Progress Report

> **Stack:** ESP32 (MicroPython) · FastAPI (Python) · HTML/CSS/JS Dashboard
> **Last updated:** 2026-05-23

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Components & Sensors](#2-components--sensors)
3. [Finalized Pin Assignments](#3-finalized-pin-assignments)
4. [Wiring & Voltage Rules](#4-wiring--voltage-rules)
5. [Software Architecture](#5-software-architecture)
6. [Phase 1 — WiFi System](#6-phase-1--wifi-system)
7. [Known Behavioural Limitations](#7-known-behavioural-limitations)
8. [Phase 2 — Network Pipeline](#8-phase-2--network-pipeline)
9. [Remaining Phases](#9-remaining-phases)

---

## 1. Project Overview

A **local Smart Home controller** with a live web dashboard:

```
Phone / Browser Dashboard (HTML + JS)
           ↕  WebSocket (live radar) + HTTP REST (commands)
FastAPI Backend (running on Laptop)
           ↕  HTTP POST (sensor data) + HTTP GET polling (commands)
ESP32 Dev Board (MicroPython firmware)
           ↕  GPIO
Hardware: 4× LEDs, HC-SR04 + SG90 Servo (Radar), Buzzer,
          KY-026 Flame Sensor, FC-51 IR Sensor
```

**Features (planned):**
- Control 4 room LEDs from phone
- Live rotating radar (servo + ultrasonic) displayed as canvas sweep
- Proximity alarm via buzzer
- Flame / fire detection alert
- IR gate open/close detection
- WiFi provisioning via captive portal (no hardcoded credentials needed)
- Track room on-time and estimated electricity cost

**Power:** USB from laptop (500–900 mA available). No battery for demo.

---

## 2. Components & Sensors

### Core Components

| # | Component | Qty | Purpose |
|---|-----------|-----|---------|
| 1 | **ESP32 Dev Board** (38-pin) | 1 | Main microcontroller. Runs MicroPython. WiFi built-in. |
| 2 | **LED 5mm** (any colour) | 4 | Simulate room lights. Individually controllable. |
| 3 | **HC-SR04 Ultrasonic Sensor** | 1 | Distance measurement for radar sweep. |
| 4 | **SG90 Micro Servo Motor** | 1 | Rotates HC-SR04 0°–180° for radar sweep. |
| 5 | **Active Buzzer (5V)** | 1 | Alarm when object too close or fire detected. |
| 6 | **KY-026 Flame Sensor** | 1 | Detects IR wavelength from flames. Digital output. |
| 7 | **FC-51 IR Obstacle Sensor** | 1 | Gate open/close detection (IR beam break). |
| 8 | **Half-size Breadboard** | 1 | Prototyping. |
| 9 | **Jumper wires** (M-M, M-F, F-F) | 1 set | Connections. |

### Protection / Support Components

| # | Component | Value | Purpose |
|---|-----------|-------|---------|
| 10 | Resistors | **220 Ω** × 4 | Current limiting for LEDs |
| 11 | Resistors | **1 kΩ** × 1 | HC-SR04 Echo voltage divider (upper leg) |
| 12 | Resistors | **2 kΩ** × 1 | HC-SR04 Echo voltage divider (lower leg) |
| 13 | Capacitor | **100 µF** electrolytic | Decouple servo power spikes |
| 14 | Micro USB cable | — | Data cable (not charge-only!) |

---

## 3. Finalized Pin Assignments

> **Source:** ChatGPT session (latest iteration). These override the original Claude roadmap.

```
ESP32 GPIO    Component               Notes
──────────────────────────────────────────────────────────────────
GPIO  2       D2 Onboard LED          WiFi status indicator (built-in)
GPIO 16       Room 1 LED              via 220 Ω resistor
GPIO 17       Room 2 LED              via 220 Ω resistor
GPIO 18       Room 3 LED              via 220 Ω resistor
GPIO 19       Room 4 LED              via 220 Ω resistor
GPIO  5       HC-SR04 TRIG            Direct (3.3 V output is fine)
GPIO 27       HC-SR04 ECHO            via 1 kΩ / 2 kΩ voltage divider  ⚠️
GPIO 25       SG90 Servo Signal       Direct (3.3 V signal is fine for SG90)
GPIO 26       Active Buzzer (+)       Direct or via 100 Ω
GPIO 34       KY-026 Flame Sensor D0  Input-only pin — no drive capability
GPIO 35       FC-51 IR Sensor OUT     Input-only pin — no drive capability

5V  pin       HC-SR04 VCC             Must be 5 V, not 3.3 V
5V  pin       SG90 VCC                Must be 5 V, with 100 µF cap to GND
GND           All components          Common ground — every component shares this
```

> **Note on GPIO 34 & 35:** These are **input-only** pins on ESP32. They have no internal pull-up. Set them as `Pin.IN` only. Do not drive them as output.

---

## 4. Wiring & Voltage Rules

### LED Wiring (all 4 identical)
```
ESP32 GPIO (3.3 V) → [220 Ω] → LED Anode (+, long leg) → LED Cathode (−, short leg) → GND

Why 220 Ω?
  R = (Vcc − Vled) / I = (3.3 − 2.0) / 0.010 = 130 Ω minimum
  220 Ω gives ~6 mA — well within ESP32's 12 mA safe limit per pin.
```

### HC-SR04 Voltage Divider (ECHO pin — MANDATORY)
```
HC-SR04 ECHO outputs 5 V. ESP32 GPIO max is 3.3 V.
Connecting 5 V directly WILL damage the ESP32 pin.

HC-SR04 ECHO
     │
   [1 kΩ]
     ├──────────→ GPIO 27 (ESP32)
   [2 kΩ]
     │
    GND

Voltage at GPIO 27 = 5 V × (2k / (1k + 2k)) = 3.33 V ✓ Safe
```

### SG90 Servo Power
```
Servo draws 250–500 mA when moving — never power from a GPIO pin.

SG90 Red   (VCC)    → 5V rail
SG90 Brown (GND)    → GND rail
SG90 Orange(Signal) → GPIO 25 (3.3 V signal is fine)

Add 100 µF electrolytic capacitor between 5V and GND close to the servo.
This absorbs current spikes that would otherwise reset/crash the ESP32.
```

### HC-SR04 VCC
```
HC-SR04 runs at 5 V — connect VCC to the 5V pin on ESP32, not 3.3V.
At 3.3 V the sensor will behave erratically or not work at all.
```

### Active Buzzer
```
Buzzer (+) → GPIO 26 (direct, or via 100 Ω to reduce volume)
Buzzer (−) → GND
Active buzzer makes sound when voltage applied — no PWM needed.
```

### Safety Checklist Before Every Power-On
```
☐ Multimeter: resistance between 5V rail and GND > 1 kΩ (no short)
☐ Multimeter: resistance between 3.3V and GND > 1 kΩ
☐ HC-SR04 ECHO connected through voltage divider — not direct
☐ Servo powered from 5V pin — not GPIO
☐ 100 µF cap across servo 5V / GND
☐ All components share common GND
☐ USB cable is a DATA cable (not charge-only)
☐ Unplug USB before rewiring anything
```

---

## 5. Software Architecture

### Communication Flow
```
Phone/Browser
    │  WebSocket ws://laptop-ip:8000/ws   (live radar push)
    │  HTTP POST /command                 (LED on/off, radar toggle)
    ▼
FastAPI Backend (Laptop, port 8000)
    │  HTTP POST /sensor-data             (ESP32 pushes sensor readings)
    │  HTTP GET  /command/pending         (ESP32 polls for queued commands)
    ▼
ESP32 (MicroPython)
    │  GPIO OUT → LEDs, Buzzer, Servo
    │  GPIO IN  ← HC-SR04, Flame, IR
```

### Key Architecture Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| ESP32 ↔ Backend protocol | HTTP (REST) | MicroPython WebSocket is fragile; HTTP is reliable and easy to debug |
| Backend ↔ Phone protocol | WebSocket | Radar needs real-time push — polling would look choppy |
| Command delivery to ESP32 | ESP32 polls `/command/pending` every 200 ms | Simpler than running a server on ESP32 |
| No `input()` ever on ESP32 | `uselect.poll()` for serial | `input()` blocks the radar sweep loop |
| Config storage | `config.json` on ESP32 flash | Survives reboots; editable via captive portal |
| WiFi provisioning | Captive portal (AP mode + mini web server) | Professional pattern — same as smart bulbs/plugs |

### ESP32 File Structure (WiFi phase complete)
```
esp32/
├── config.py          # All constants and pin numbers (single source of truth)
├── config.json        # Saved WiFi credentials + API base URL (persisted on flash)
├── hardware.py        # D2 LED WiFi status indicator (non-blocking blink)
├── wifi.py            # WiFi connect logic, config load/save
├── wifi_manager.py    # Captive portal — AP hotspot + config webpage
└── main.py            # Entry point
```

---

## 6. Phase 1 — WiFi System

### Goal
Get the ESP32 to:
1. Connect to saved WiFi on boot
2. Show status on D2 onboard LED (slow blink = connecting, solid = connected, fast blink = hotspot mode)
3. If WiFi fails → create a hotspot and serve a config webpage so the user can set credentials without reflashing

### Features Implemented

| Feature | File | Detail |
|---------|------|--------|
| Load credentials from flash | `wifi.py` `load_config()` | Reads `config.json` from ESP32 filesystem |
| Auto-create config if missing | `wifi.py` `_ensure_config()` | Falls back to defaults in `config.py`, saves file |
| WiFi connect with timeout | `wifi.py` `connect_wifi()` | 40 × 250 ms = 10 s timeout. Calls `update_led()` each iteration for live blink |
| D2 LED status indicator | `hardware.py` `update_led()` | Non-blocking using `time.ticks_ms()` — no `sleep()` in blink |
| AP captive portal | `wifi_manager.py` `start_portal()` | Hotspot `SmartHome-Setup` / `12345678`. Serves config form at `192.168.4.1` |
| Non-blocking portal loop | `wifi_manager.py` | Socket timeout = 100 ms. LED keeps blinking while waiting for client |
| URL decode in portal | `wifi_manager.py` `_url_decode()` | Handles passwords with `+`, `%XX` special characters |
| Save credentials + reboot | `wifi_manager.py` | Saves to `config.json`, `machine.reset()` |
| Runtime reconnect + portal fallback | `main.py` monitor loop | On WiFi drop: tries `connect_wifi()` up to 2×, then calls `start_portal()` |
| WiFi drop printed to console | `main.py` | Prints attempt number on each reconnect try |
| Monitor WiFi after connect | `main.py` loop | Detects disconnect and updates LED mode |
| All pin constants centralised | `config.py` | Every file imports from here — no scattered magic numbers |

### Files Created

| File | Role |
|------|------|
| [`config.py`](../esp32/config.py) | Constants: WiFi defaults, AP settings, all GPIO pin numbers |
| [`config.json`](../esp32/config.json) | Runtime config: `wifi_ssid`, `wifi_password`, `api_base` |
| [`hardware.py`](../esp32/hardware.py) | D2 LED controller — `set_mode()`, `update_led()` |
| [`wifi.py`](../esp32/wifi.py) | `connect_wifi()`, `wifi_is_connected()`, `load/save_config()` |
| [`wifi_manager.py`](../esp32/wifi_manager.py) | `start_portal()` — hotspot + HTTP server + config form |
| [`main.py`](../esp32/main.py) | Entry point — tries WiFi, falls back to portal, monitors loop |

---

### Bugs & Fixes Log

#### Bug 1 — LED not blinking during WiFi connect attempt
**Problem:** Original `wifi.py` used `time.sleep(0.1)` in connect loop with only 20 iterations = 2 s timeout. `update_led()` called once per 100 ms, but 500 ms blink interval means LED barely toggled once before timeout.

**Risk:** User sees no feedback during connection attempt. Looks like board froze.

**Fix:** Changed to 40 iterations × `time.sleep_ms(250)` = 10 s timeout. `update_led()` fires 40 times — gives ~10 complete blink cycles at 500 ms interval. Smooth and visible.

---

#### Bug 2 — LED freezes in AP mode (hotspot)
**Problem:** Original `wifi_manager.py` had a blocking `s.accept()` — execution stops here waiting for a client. `update_led()` was never called during the wait, so the LED stopped blinking in AP mode.

**Risk:** User cannot tell if the hotspot is active or if the ESP32 froze.

**Fix:** `s.settimeout(0.1)` on the socket. Accept now returns after 100 ms if no client. The `while True` loop continues, calls `update_led()`, then tries `accept()` again. LED fast-blinks correctly at 100 ms in AP mode.

---

#### Bug 3 — Hard reset / stale reconnect loop (flagged after first upload)
**Problem:** `connect_wifi()` called `_wlan.active(True)` then immediately `_wlan.connect()` without checking if already connected. MicroPython retains network state across soft resets (Ctrl+D in Thonny). Calling `connect()` on an already-connected interface causes undefined behaviour — sometimes hangs, sometimes triggers a reconnect storm.

**Risk:** ESP32 appears frozen or keeps rebooting. Very hard to debug on hardware.

**Fix:**
```python
_wlan.active(True)

if _wlan.isconnected():       # ← FIX 1: early return if already up
    set_mode(MODE_CONNECTED)
    return True

try:
    _wlan.disconnect()        # ← FIX 2: clear stale association
except:
    pass

_wlan.connect(ssid, pwd)
```

---

#### Bug 4 — STA mode interferes with AP mode (flagged after first upload)
**Problem:** When WiFi fails and the portal starts, the STA (station) interface was left active. Both STA and AP share the ESP32's single radio. Having STA active in AP mode wastes ~20 KB RAM in MicroPython's networking stack and can cause unstable AP beacon timing.

**Risk:** Hotspot may not appear on phone, or web page loads unreliably.

**Fix:** Added before AP starts in `start_portal()`:
```python
network.WLAN(network.STA_IF).active(False)
```

---

#### Bug 5 — Special characters in passwords not decoded
**Problem:** When the config form is submitted, the browser URL-encodes the password (`+` for space, `%21` for `!` etc.). The original code read raw query string without decoding — saved a corrupted password.

**Risk:** WiFi connection fails even with correct password if it contains spaces or special characters.

**Fix:** Added `_url_decode()` function in `wifi_manager.py`:
```python
def _url_decode(s):
    s = s.replace("+", " ")
    # decode %XX hex sequences
    ...
```

---

#### Bug 6 — Runtime WiFi drop: no reconnect and no portal (found during hardware test)
**Problem:** After a successful initial connection, the `main.py` monitor loop only updated the LED mode on disconnect — it never tried to reconnect and never called `start_portal()`. The LED correctly switched to 500ms blink (giving user false hope that something was happening), but the ESP32 just looped forever in that state. The hotspot was never created.

**Risk:** If the router reboots or WiFi drops briefly, the ESP32 is permanently stuck blinking with no recovery. Only a manual reboot recovers it — during a demo this is fatal.

**Fix:** Added reconnect logic to the monitor loop in `main.py`:
```python
_fail_count = 0
_MAX_FAILS  = 2

while True:
    if wifi_is_connected():
        set_mode(MODE_CONNECTED)
        _fail_count = 0
    else:
        _fail_count += 1
        print("WiFi lost — reconnect attempt", _fail_count, "of", _MAX_FAILS)
        if connect_wifi():
            _fail_count = 0
        elif _fail_count >= _MAX_FAILS:
            start_portal()   # blocks until reboot
```
Now: WiFi drop → tries reconnect 2× (each attempt 10s) → if both fail → portal starts automatically.

---

#### Bug 7 — AP mode blink too slow to notice (100ms → 50ms → 20ms)
**Problem:** AP mode blinked at 100ms — looked too similar to the 500ms connecting blink. Changed to 50ms, then further reduced to **20ms** after testing confirmed 50ms still wasn't instantly obvious.

**Fix:** `hardware.py` — `interval = 20 if _mode == MODE_AP else 500`

---

#### Bug 8 — HTTP response not reaching browser (found during hardware test)
**Problem:** The `_PAGE` and `_SAVED` strings embedded the HTTP headers using Python escape sequences inside a triple-quoted string:
```python
_PAGE = """\
HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n
...
"""
```
In a **triple-quoted string**, `\r\n` is literally the four characters `\`, `r`, `\`, `n` — NOT carriage return + newline. The browser received a malformed HTTP header with no valid separator, so it treated the entire response as garbage. The page never loaded — browser showed a blank or error page.

**Risk:** Form submit appears to do nothing. User thinks ESP32 crashed.

**Fix:** Rewrote `_send()` as a proper helper that builds the HTTP headers in Python code (where `\r\n` ARE actual CRLF), encodes everything to bytes, and uses `client.sendall()` to guarantee delivery:
```python
def _send(client, html):
    body   = html.encode("utf-8")
    header = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: text/html; charset=utf-8\r\n"
        "Connection: close\r\n"
        "Content-Length: " + str(len(body)) + "\r\n"
        "\r\n"
    ).encode("utf-8")
    client.sendall(header + body)
```

---

#### Bug 9 — Regex `\s` not supported in MicroPython `ure` (found during hardware test)
**Problem:** The regex patterns used `[^&\s]+` to match query parameter values. MicroPython's `ure` module is a minimal regex engine — `\s` (whitespace character class) is **not reliably supported**. The `ure.search()` call silently returned `None`, causing the `except` block to set `ssid = ""`. With an empty SSID, the form was served again instead of saving — making it appear as if "nothing happened".

**Risk:** Credentials are never saved. WiFi is never configured. Portal loops forever.

**Fix:** Replaced `[^&\s]+` with `[^& ]+` everywhere — explicitly excluding `&` and literal space:
```python
m_ssid = ure.search(r"ssid=([^& ]+)", raw)
m_pwd  = ure.search(r"password=([^& ]+)", raw)
m_api  = ure.search(r"api=([^& ]+)", raw)
```

---

#### Bug 10 — `client.send(string)` instead of `client.sendall(bytes)`
**Problem:** `client.send(_PAGE)` passed a Python string directly. MicroPython's socket `send()` may accept strings but is not guaranteed to send all bytes in one call (it returns the number of bytes actually sent — could be less). `sendall()` with bytes is the correct approach.

**Fix:** All responses now go through `_send()` which calls `client.sendall(header + body)` with both parts pre-encoded to bytes.

---

### LED Status Reference

| D2 LED Behaviour | Meaning |
|-----------------|---------|
| Slow blink — 500 ms on/off | Trying to connect to WiFi (or reconnecting after drop) |
| Rapid strobe — 20 ms on/off | Hotspot active (AP mode), waiting for config at 192.168.4.1 |
| Solid ON | Connected to WiFi successfully |
| OFF at boot | Normal — initializing |

---

### How to Upload (Thonny)

Upload files in this exact order (dependencies load first):

```
1. config.json        ← credentials
2. config.py          ← constants
3. hardware.py        ← LED (depends on config.py)
4. wifi.py            ← WiFi logic (depends on hardware.py, config.py)
5. wifi_manager.py    ← portal (depends on hardware.py, wifi.py, config.py)
6. main.py            ← entry point (depends on everything)
```

In Thonny: **File → Save As → MicroPython Device** for each file.

---

### Test Cases

**Case A — Correct credentials in `config.json`**
```
Expected:
  Boot → D2 slow blink → "Connected! IP: 192.168.x.x" in console
       → D2 solid ON
       → "System Running" printed
```

**Case B — Wrong/missing credentials**
```
Expected:
  Boot → D2 slow blink for 10 s → "WiFi failed"
       → D2 fast blink → "Hotspot: SmartHome-Setup" in console
       → Phone sees WiFi: SmartHome-Setup (password: 12345678)
       → Open browser → 192.168.4.1
       → Dark config page appears
       → Enter real WiFi name, password, API URL → Save
       → "ESP32 is restarting..." page shown
       → ESP32 reboots → connects → D2 solid ON
```

---

## 7. Known Behavioural Limitations

### Limitation 1 — ESP32 disconnects when phone hotspot host switches to WiFi

**Observed behaviour:**
The ESP32 connects successfully to a phone's mobile hotspot. Then, on that same phone, the user turns on WiFi (to get internet from a router). The ESP32 immediately loses its connection and the main loop starts the reconnect cycle. Even after the phone's WiFi is back on alongside the hotspot, the ESP32 cannot reconnect to the hotspot.

**Why this happens — technical explanation:**

A mobile hotspot is not a real router. It is a software NAT layer sitting on top of the phone's radio hardware. Android and iOS devices have a single radio chip that handles WiFi, and the hotspot and WiFi client mode share this chip.

When the phone connects to a WiFi network while hotspot is active:

1. **Android (most common behaviour):** The OS may keep both WiFi and hotspot active simultaneously, but it **reassigns the radio** from cellular-backed hotspot to WiFi-backed hotspot. During this radio reassignment, all connected clients (like the ESP32) are **temporarily or permanently disconnected**. The DHCP server on the hotspot may also restart, issuing new IP leases. The ESP32's existing TCP state is invalidated. Even if the hotspot comes back, the ESP32's old IP lease is gone and the reconnect attempt often fails because the phone's DHCP allocator doesn't recognise the existing connection.

2. **Android (some versions / battery saver mode):** Connecting to WiFi **automatically disables the hotspot entirely** to save battery. The ESP32's network disappears completely.

3. **iOS / iPhone:** iPhone does not support running hotspot and WiFi client mode simultaneously on the same radio. Connecting the phone to a WiFi network **kills the hotspot**. All connected devices are instantly dropped.

**Root cause in one sentence:**
> The phone's hotspot is backed by its cellular radio (SIM data). The moment the phone switches its internet source from cellular to WiFi, the hotspot's radio context changes — disconnecting all clients.

**Current workaround (in use):**
- Use a phone with a **SIM card and active mobile data** as the hotspot
- Do **not** connect that phone to any WiFi while the ESP32 is using its hotspot
- The phone provides internet via SIM → hotspot → ESP32 reliably

**Future solutions (to implement later):**

| Option | How | Effort |
|--------|-----|--------|
| **Use a router** | Connect ESP32 to a proper WiFi router or home network instead of a phone hotspot | Easy — just update `config.json` with router credentials |
| **ESP32 static IP** | Assign a fixed IP to ESP32 on the router's DHCP reservation list (bind MAC → IP). Even after reconnects, ESP32 gets the same IP. | Low effort on router admin panel |
| **Laptop hotspot** | Windows / macOS can share internet via a hotspot. Much more stable than phone — the radio doesn't switch when you use the laptop's own WiFi | Easy workaround for demo |
| **Reconnect with backoff** | Improve `main.py` to keep retrying indefinitely with exponential backoff instead of giving up after 2 attempts and starting the portal | Medium — code change in `main.py` |

**Status:** Not a code bug. This is a hardware/OS-level constraint of phone hotspots. **No fix planned for Phase 1.** Using SIM-only phone hotspot as workaround for now.

---

## 8. Phase 2 — Network Pipeline ✅

### Goal
Establish reliable **ESP32 ↔ FastAPI** communication over WiFi before building any frontend, database, or radar logic.

Verify every layer of the stack:
- WiFi reachability ✅
- HTTP request/response ✅
- JSON serialisation/deserialisation ✅
- API base URL resolution from `config.json` ✅
- Sensor data flowing to backend ✅
- Command queue polling working ✅

---

### Project Folder Structure (after Phase 2)

```
my iot project/
├── docs/
│   └── complete_build_info.md
├── esp32/
│   ├── config.json          ← WiFi credentials + API base URL
│   ├── config.py            ← All constants and pin numbers
│   ├── hardware.py          ← D2 WiFi status LED
│   ├── wifi.py              ← WiFi connect / reconnect logic
│   ├── wifi_manager.py      ← Captive portal (AP mode)
│   ├── main.py              ← Orchestrator — Phase 2
│   ├── api.py               ← All HTTP calls to backend     [NEW]
│   ├── leds.py              ← Room LED control (4 LEDs)     [NEW]
│   ├── buzzer.py            ← Active buzzer control         [NEW]
│   ├── sensors.py           ← Flame + IR sensor reads       [NEW]
│   └── radar.py             ← Servo sweep + HC-SR04         [NEW]
└── backend/
    ├── main.py              ← FastAPI app + router includes  [NEW]
    ├── requirements.txt     ← fastapi, uvicorn               [NEW]
    ├── render.yaml          ← Render.com deploy config       [NEW]
    └── app/
        ├── __init__.py
        ├── state.py         ← Shared in-memory state        [NEW]
        └── routes/
            ├── __init__.py
            ├── health.py    ← GET /health                   [NEW]
            ├── sensor.py    ← POST /sensor-data             [NEW]
            └── commands.py  ← GET/POST /command             [NEW]
```

---

### New ESP32 Files

| File | Purpose |
|------|---------|
| `api.py` | HTTP communication layer. All backend calls go here. Wraps every request in try/except, returns safe defaults on failure. Caches API base URL from `config.json`. |
| `leds.py` | Room LED control. `set_room(n, state)`, `set_all(state)`, `get_states()`. Initialises all 4 LEDs off at import. |
| `buzzer.py` | Active buzzer. `on()`, `off()`, `beep(ms)`, `double_beep()`. Blocking during beep duration (kept ≤200ms). |
| `sensors.py` | KY-026 flame + FC-51 IR reads. Both are active-low — returns `True` when triggered. GPIO 34 & 35 are input-only pins. |
| `radar.py` | SG90 sweep + HC-SR04 distance. `sweep_step()` advances one angle step and returns `{"angle", "distance"}`. Not yet called in main.py (Phase 7). |

### Updated ESP32 Files

| File | What Changed |
|------|--------------|
| `config.py` | Added `API_HEALTH_INTERVAL_MS = 15000`, `SENSOR_POST_INTERVAL_MS = 2000`, `COMMAND_POLL_INTERVAL_MS = 500` |
| `api.py` | Fixed `_get_base()` to validate api_base — falls back to `DEFAULT_API_BASE` if empty string or not starting with `http` |
| `main.py` | Full Phase 2 orchestrator. `ticks_ms()` scheduling, no blocking sleeps. Imports all modules. Radar sweep commented out for Phase 7. |

---

### New Backend Files

| File | Purpose |
|------|---------|
| `backend/main.py` | FastAPI `app` instance. Adds CORS middleware. Includes all three routers. No logic here. |
| `backend/app/state.py` | Shared in-memory state: `pending_commands` list and `latest_sensor` dict. All routes import from here. |
| `backend/app/routes/health.py` | `GET /health` → `{"status": "ok"}` |
| `backend/app/routes/sensor.py` | `POST /sensor-data` → stores + prints. `GET /sensor-data/latest` → returns last snapshot. |
| `backend/app/routes/commands.py` | `GET /command/pending` → returns + clears queue. `POST /command` → queues command. `GET /command/queue` → inspects without consuming. |

### Backend API Endpoints Summary

| Method | Endpoint | Who calls it | Purpose |
|--------|----------|--------------|---------|
| GET | `/health` | ESP32 (every 15s) | Pipeline verification |
| POST | `/sensor-data` | ESP32 (every 2s) | Upload sensor readings |
| GET | `/sensor-data/latest` | Debug / browser | See last sensor snapshot |
| GET | `/command/pending` | ESP32 (every 500ms) | Receive + consume commands |
| POST | `/command` | Postman / dashboard | Queue command for ESP32 |
| GET | `/command/queue` | Debug | Inspect queue without consuming |

**Run command:**
```
py -3.11 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
*(Run from `backend/` folder)*

**Auto-docs (no Postman needed):** `http://192.168.1.5:8000/docs`

---

### What Was Verified During Testing

```
✅ ESP32 connects to WiFi → LED solid ON
✅ [API] Base URL: http://192.168.1.5:8000 loaded from config.json
✅ Sensor data POSTed every 2s → backend prints [SENSOR] Received: {...}
✅ Health ping every 15s → backend prints [HEALTH] Ping received
✅ Command poll every 500ms → 200 OK returned
✅ flame: True detected when lighter held near KY-026 sensor
✅ gate: True detected when hand blocked FC-51 IR beam
✅ flame + gate return to False when removed
✅ Both sensors work correctly with active-low logic
✅ Radar sweep active — angles and real distances flowing to backend
```

### Bugs Fixed During Phase 2

#### Bug — api_base empty string crashes urequests
**Problem:** Captive portal's API URL field was left blank during setup. Saved `api_base: ""` to `config.json`. `urequests` received empty string URL and crashed with `need more than 2 values to unpack` and `Unsupported protocol:`.

**Fix:** `api.py` `_get_base()` now validates the loaded URL:
```python
if url and url.startswith("http"):
    _base_url = url
else:
    _base_url = DEFAULT_API_BASE   # safe fallback
```

---

## 9. Phase 3 — Radar (Servo + HC-SR04) ✅

### Goal
Integrate servo sweep + HC-SR04 distance reading into the running system. Real angle+distance data flowing to FastAPI alongside flame/gate/LED state.

### What Was Built
- `radar.py` fully operational: continuous sweep 15°→165°→015°, HC-SR04 reads at each step
- Runs in a **background `_thread`** — completely independent of WiFi/HTTP calls
- `main.py` updated: `radar.start()` at boot, `radar.get_latest()` on each sensor POST

### Bugs Found and Fixed

#### Bug 1 — Placeholder overwrote real radar data
**Problem:** In `main.py`, two consecutive lines:
```python
radar_data = radar.sweep_step()           # ← real data returned here
radar_data = {"angle": 0, "distance": None}  # ← IMMEDIATELY overwritten!
```
The servo moved but all real readings were discarded. Backend always received `angle: 0, distance: None`.

**Fix:** Removed the placeholder line. Real data now stored in `_radar_data`.

#### Bug 2 — HTTP calls blocked servo sweep
**Problem:** `main.py` was single-threaded. Every HTTP call (health ping ≈200ms, sensor POST ≈200ms, command poll ≈100ms) caused the servo to freeze mid-sweep. Movement was choppy and irregular.

**Decision: `_thread`**
Used MicroPython’s `_thread` module to run the radar sweep in a background thread:
```
Background Thread:              Main Thread:
  while True:                     while True:
    set_angle()                       radar.get_latest()  ← instant read
    get_distance()                    HTTP health ping
    update _latest dict               HTTP sensor POST
    (no sleep — runs flat out)        HTTP command poll
```
- `_latest` dict updated continuously by radar thread
- Main thread reads it with `radar.get_latest()` — 0ms cost
- Servo NEVER pauses for network calls

#### Bug 3 — Initial settle delay hurt more than it helped
**Problem:** Added 15ms settle delay after `set_angle()` before `get_distance()`. Reasoning was servo vibration would confuse HC-SR04. Testing showed this was unnecessary and added latency without benefit. Original working code had no delay.

**Fix:** Removed settle delay. Servo can move and read distance at full speed.

### Key Design Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Radar threading | `_thread` | Only way to decouple servo from HTTP in single-core MicroPython |
| Step size | 3° | Original working value; 2° added no visible benefit |
| Sweep range | 15° – 165° | Avoids servo hard stops at 0°/180° |
| Settle delay | None | Not needed; original code had none |
| Max range filter | 2 – 400 cm | < 2cm = sensor dead zone, > 400cm = physically unreachable |

### Understanding `distance: None`

`None` is **not an error**. It means no object detected at that angle. Causes:

| Cause | Explanation |
|-------|-------------|
| Open space | Beam aimed at gap/doorway/open area > 400cm |
| Sensor dead zone | Object closer than 2cm (physical limit of HC-SR04) |
| Soft surface | Curtains/foam absorb sound, no echo returns |
| Angled hard surface | Sound deflects away, echo misses sensor |
| Narrow object | HC-SR04 cone (~15°) passes around it |

On the radar display: `None` = no blip. `float` = draw a blip at (angle, distance).

### What Was Verified
```
✅ Servo sweeps 15° → 165° → 15° continuously
✅ Distance readings: 30.1 cm, 131.9 cm, 124.06 cm (real objects detected)
✅ distance: None at angles pointing at open space (correct behaviour)
✅ Angle changes correctly every POST: 132 → 75 → 21 → 105
✅ Radar sweep unaffected by HTTP call timing
✅ Full payload flowing: {angle, distance, flame, gate, leds}
```

---

## 10. Remaining Phases

| Phase | Status | Goal | Key Files |
|-------|--------|------|-----------|
| **Phase 1** | ✅ Done | WiFi provisioning, captive portal, D2 LED | `wifi.py`, `wifi_manager.py`, `hardware.py` |
| **Phase 2** | ✅ Done | ESP32 ↔ FastAPI pipeline, sensor data flowing | `api.py`, `backend/` |
| **Phase 3** | ✅ Done | Radar — servo sweep + HC-SR04 in `_thread`, angles + distances live | `radar.py`, `main.py` |
| **Phase 4** | ✅ Next | Local Dashboard — HTML/JS connects to FastAPI, shows radar canvas, LED buttons, sensor status | `frontend/` |
| **Phase 5** | ⬜ | Backend WebSocket — push radar data to browser in real-time | `backend/app/routes/ws.py` |
| **Phase 6** | ⬜ | Backend alerts — flame=True auto-queues buzzer beep | `backend/app/routes/sensor.py` update |
| **Phase 7** | ⬜ | MongoDB persistence — sensor history logging | `backend/app/database/` |
| **Phase 8** | ⬜ | Analytics — room on-time, power estimate | Backend + dashboard |
| **Phase 9** | ⬜ | Deploy — FastAPI on Render, frontend on Vercel | `render.yaml`, Vercel config |
| **Phase 10** | ⬜ | Final integration + demo polish | — |

---

*Document maintained alongside code. Update after each phase.*
