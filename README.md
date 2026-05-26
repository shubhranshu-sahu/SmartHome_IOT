# 🏠 SmartHome IoT — Complete Build Documentation

> A full-stack IoT Smart Home controller powered by ESP32 (MicroPython), a FastAPI cloud backend, and a responsive web dashboard. Features live radar sweeping, room LED control, flame/gate detection, and MongoDB-backed analytics.

**Live Demo:** [https://svvv-iot.vercel.app](https://svvv-iot.vercel.app)
**Backend API:** Deployed on Render (free tier)

---

## 📖 Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Hardware Components](#3-hardware-components)
4. [Wiring & Pin Assignments](#4-wiring--pin-assignments)
5. [ESP32 Firmware (MicroPython)](#5-esp32-firmware-micropython)
   - [WiFi Connection — wifi.py](#51-wifi-connection--wifipy)
   - [WiFi Manager (Captive Portal) — wifi_manager.py](#52-wifi-manager-captive-portal--wifi_managerpy)
   - [Hardware LED Status — hardware.py](#53-hardware-led-status--hardwarepy)
   - [Configuration — config.py & config.json](#54-configuration--configpy--configjson)
   - [API Communication — api.py](#55-api-communication--apipy)
   - [Sensors — sensors.py](#56-sensors--sensorspy)
   - [LEDs — leds.py](#57-leds--ledspy)
   - [Buzzer — buzzer.py](#58-buzzer--buzzerpy)
   - [Radar — radar.py](#59-radar--radarpy)
   - [Orchestrator — main.py](#510-orchestrator--mainpy)
6. [Backend (FastAPI + Python)](#6-backend-fastapi--python)
   - [Entry Point — main.py](#61-entry-point--mainpy)
   - [In-Memory State — state.py](#62-in-memory-state--statepy)
   - [WebSocket Manager — ws_manager.py](#63-websocket-manager--ws_managerpy)
   - [MongoDB Connection — db.py](#64-mongodb-connection--dbpy)
   - [Route: /health](#65-route-health)
   - [Route: /sensor-data](#66-route-sensor-data)
   - [Route: /command](#67-route-command)
   - [Route: /ws (WebSocket)](#68-route-ws-websocket)
   - [Route: /auth/*](#69-route-auth)
   - [Route: /stats/*](#610-route-stats)
7. [Frontend (Vanilla JS + Bootstrap 5)](#7-frontend-vanilla-js--bootstrap-5)
   - [Landing Page — index.html](#71-landing-page--indexhtml)
   - [Dashboard — dashboard.html](#72-dashboard--dashboardhtml)
   - [Stats Page — stats.html](#73-stats-page--statshtml)
   - [Configuration — config.js](#74-configuration--configjs)
   - [WebSocket Client — ws.js](#75-websocket-client--wsjs)
   - [Radar Canvas — radar.js](#76-radar-canvas--radarjs)
   - [LED Controls — leds.js](#77-led-controls--ledsjs)
   - [Sensors Display — sensors.js](#78-sensors-display--sensorsjs)
   - [Stats Data — stats.js](#79-stats-data--statsjs)
   - [Authentication — auth.js](#710-authentication--authjs)
8. [MongoDB Schema & Analytics](#8-mongodb-schema--analytics)
9. [Deployment](#9-deployment)
   - [Backend on Render](#91-backend-on-render)
   - [Frontend on Vercel](#92-frontend-on-vercel)
10. [Local Development Setup](#10-local-development-setup)
11. [Complete Data Flow Walkthrough](#11-complete-data-flow-walkthrough)
12. [Key Design Decisions & Problems Solved](#12-key-design-decisions--problems-solved)
13. [Folder Structure](#13-folder-structure)
14. [Environment Variables Reference](#14-environment-variables-reference)

---

## 1. Project Overview

SmartHome IoT is a **complete end-to-end IoT project** that connects a physical ESP32 microcontroller to a cloud-hosted dashboard via the internet. The ESP32 controls physical hardware (LEDs, buzzer, servo motor) and reads physical sensors (ultrasonic, IR, flame). The dashboard allows you to control and monitor everything in real-time from any browser, anywhere in the world.

### What It Does

| Feature | Description |
|---------|-------------|
| **Live Radar** | A servo motor rotates an HC-SR04 ultrasonic sensor 15°→165°→15° continuously, streaming the angle and distance data to the browser. The browser renders a real-time radar canvas at 60fps. |
| **Room LED Control** | 4 individually controllable LEDs (simulating rooms). Toggle from the dashboard. Changes reflected on ESP32 within ~500ms. |
| **Flame Detection** | KY-026 IR flame sensor. When flame is detected, the ESP32 buzzer activates immediately (zero network latency), and an event is logged to MongoDB. |
| **Gate Sensor** | FC-51 IR obstacle sensor monitors a gate. State changes (open/closed) are logged to MongoDB. |
| **Protect Mode** | When enabled, the buzzer beeps at variable rates based on proximity — very rapid when something is within 25 cm, slowing as the object moves away. |
| **Manual Alarm** | "Beep" button on the dashboard queues a timed buzzer beep on the ESP32. |
| **Analytics** | `stats.html` shows today's LED on-time per room, estimated energy consumption (mAh), flame event history, and gate open/close timeline. Powered by MongoDB. |

### Technology Choices

| Layer | Technology | Why |
|-------|-----------|-----|
| Microcontroller | ESP32 (MicroPython) | Dual-core, built-in WiFi, affordable, rich ecosystem |
| Firmware language | MicroPython | Python syntax, easy to iterate, good hardware library support |
| Backend | FastAPI (Python) | Async, built-in WebSocket support, fast, auto-generates API docs |
| Database | MongoDB Atlas | Flexible schema for IoT events, free tier, async Motor driver |
| Frontend | Vanilla JS + Bootstrap 5 | No build tools needed, simple to deploy as static files |
| Backend hosting | Render (free tier) | Free persistent WebSocket support |
| Frontend hosting | Vercel | Instant global CDN for static files, automatic HTTPS |

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        ESP32 (MicroPython)                      │
│                                                                 │
│  Thread 1: radar.py thread                                      │
│    └── servo sweep + HC-SR04 reading (continuous)               │
│    └── writes to rolling buffer (MAX 60 items)                  │
│                                                                 │
│  Thread 2: _sensor_thread                                       │
│    └── drains radar buffer + reads flame/gate/LEDs              │
│    └── POST /sensor-data to FastAPI every ~400ms                │
│    └── GET  /health every 250s (keeps Render awake)             │
│                                                                 │
│  Thread 3: _cmd_thread                                          │
│    └── GET /command/pending every 300ms                         │
│    └── executes: set_led, set_all, beep, protect_mode           │
│                                                                 │
│  Main Loop (Core 0)                                             │
│    └── _update_buzzer() state machine at ~15ms tick             │
│    └── WiFi watchdog (auto-reconnect on drop)                   │
│    └── update_led() hardware PWM updates                        │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP over WiFi
                               │ POST /sensor-data (400ms)
                               │ GET  /command/pending (300ms)
                               │ GET  /health (250s)
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (Render.com)                  │
│                                                                 │
│  POST /sensor-data                                              │
│    └── updates in-memory state                                  │
│    └── edge-detects flame/gate changes → writes to MongoDB      │
│    └── broadcasts full payload to all WebSocket clients         │
│                                                                 │
│  POST /command  (from browser)                                  │
│    └── updates state.led_states IMMEDIATELY                     │
│    └── appends command to pending_commands queue                │
│    └── broadcasts state change to browser via WS                │
│    └── tracks LED on→off sessions → writes to MongoDB           │
│                                                                 │
│  GET /command/pending  (polled by ESP32)                        │
│    └── returns + CLEARS pending_commands queue                  │
│                                                                 │
│  WS  /ws  (browser connection)                                  │
│    └── pushes sensor_update on every /sensor-data POST          │
│    └── pushes state_update on every /command POST               │
│    └── sends ping heartbeat every 20s (keep-alive)              │
│                                                                 │
│  GET /stats/today, /stats/recent                                │
│    └── queries MongoDB Atlas for analytics                      │
│                                                                 │
│  GET /auth/verify, POST /auth/login, etc.                       │
│    └── session token authentication backed by MongoDB           │
│                                                                 │
│  ESP32 Watchdog (every 3s)                                      │
│    └── if no /sensor-data in >5s → mark ESP32 offline           │
│    └── broadcasts esp32_status event to browsers                │
└──────────────────────────────┬──────────────────────────────────┘
                               │ WebSocket (persistent)
                               │ HTTP REST (commands, auth, stats)
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Browser Dashboard (Vercel CDN)                │
│                                                                 │
│  index.html  (Landing Page)                                     │
│    └── 3D component models via <model-viewer>                   │
│    └── Project overview, tech stack, connection status          │
│                                                                 │
│  dashboard.html + JS modules                                    │
│    ├── ws.js      — persistent WebSocket, auto-reconnect        │
│    ├── radar.js   — 60fps canvas, ping-pong extrapolation        │
│    ├── leds.js    — optimistic toggle, WS confirmation          │
│    ├── sensors.js — flame/gate/protect-mode UI                  │
│    └── main.js    — init, ESP32 watchdog, layout                │
│                                                                 │
│  stats.html + stats.js                                          │
│    └── queries /stats/today + /stats/recent via REST            │
│    └── bar charts, battery gauge, flame/gate timelines          │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                   MongoDB Atlas (Cloud)                         │
│                                                                 │
│  Database: smart_home                                           │
│                                                                 │
│  Collection: users                                              │
│    └── {username, password_hash, role, created_at}             │
│                                                                 │
│  Collection: led_sessions                                       │
│    └── {room, turned_on, turned_off, duration_sec, battery_mah} │
│                                                                 │
│  Collection: flame_events                                       │
│    └── {detected_at, cleared_at, duration_sec}                  │
│                                                                 │
│  Collection: gate_events                                        │
│    └── {timestamp, state: "open"|"closed"}                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Hardware Components

### Core Components

| # | Component | Qty | Role in Project |
|---|-----------|-----|-----------------|
| 1 | **ESP32 DevKit V1** (30-pin, CP2102 USB-UART) | 1 | Main microcontroller. Runs all 3 threads. Built-in WiFi 802.11 b/g/n. |
| 2 | **5mm LED** (any colour) | 4 | Simulate 4 room lights. Each individually controllable via GPIO. |
| 3 | **HC-SR04 Ultrasonic Sensor** | 1 | Measures distance by emitting 40kHz sound pulses. Powers the radar system. |
| 4 | **SG90 Micro Servo Motor** | 1 | Rotates the HC-SR04 from 15° to 165° continuously for the radar sweep. |
| 5 | **Active Buzzer (5V compatible)** | 1 | Audible alarm for proximity alerts (protect mode) and flame detection. |
| 6 | **KY-026 Flame Sensor** | 1 | IR photodetector + comparator. Detects open flames via 760–1100nm wavelength IR. |
| 7 | **FC-51 IR Obstacle Sensor** | 1 | IR emitter/receiver pair. Used as a gate sensor — beam break = gate closed. |
| 8 | **Breadboard** | 2 | Prototyping platform for all connections. |
| 9 | **Jumper Wires** (M-M, M-F, F-F) | 1 set | Connections between ESP32, breadboard, and components. |

### Support / Protection Components

| # | Component | Value | Purpose |
|---|-----------|-------|---------|
| 10 | Resistor | **220 Ω × 4** | Current limiting for the 4 room LEDs (limits to ~6mA per LED at 3.3V, safe for ESP32 GPIO pins rated 12mA max) |
| 11 | Resistor | **1 kΩ × 1** | Upper leg of the HC-SR04 ECHO voltage divider |
| 12 | Resistor | **2 kΩ × 1** | Lower leg of the HC-SR04 ECHO voltage divider |
| 13 | Capacitor | **100 µF, 1000 µF electrolytic** | Decouples servo power supply spikes (servo draws 250–500 mA peak) |

### Sensor Specifications

#### HC-SR04 Ultrasonic Sensor
- **Operating Voltage:** 5V (MUST use 5V — unreliable at 3.3V)
- **Frequency:** 40 kHz ultrasonic burst
- **Range:** 2 cm – 400 cm (we limit to 400 cm in software)
- **Accuracy:** ±3 mm at close range
- **ECHO pin voltage:** 5V logic (requires voltage divider before connecting to ESP32!)
- **Trigger pulse:** 10 µs HIGH pulse on TRIG pin
- **Distance formula:** `distance_cm = (echo_pulse_duration_µs × 0.0343) / 2`
- **Used for:** Radar distance measurement at each servo angle

#### SG90 Micro Servo Motor
- **Operating Voltage:** 5V (MUST use 5V from VIN pin)
- **Control:** 50 Hz PWM signal, pulse width 500 µs (0°) to 2400 µs (180°)
- **Torque:** 2.5 kg·cm at 5V
- **Speed:** ~0.1 s per 60° rotation
- **Sweep range used:** 15° – 165° (avoids physical hard stops at 0° and 180°)
- **Step size:** 3° per move, 22 ms settle time between steps
- **Current draw:** 250–500 mA when moving (requires decoupling capacitor)

#### KY-026 Flame Sensor (used as general IR sensor)
- **Operating Voltage:** 3.3V – 5V
- **Detection:** Infrared wavelength 760 nm – 1100 nm
- **Output:** Digital (active LOW — pulls D0 low when flame detected)
- **Sensing angle:** ~60°
- **Pin used:** GPIO 34 (ESP32 input-only ADC pin, no drive capability)
- **Logic:** `read_flame() = True` when `GPIO34.value() == 0`

#### FC-51 IR Obstacle Sensor (used as gate sensor)
- **Operating Voltage:** 3.3V – 5V
- **Type:** Active IR emitter + receiver pair
- **Output:** Digital (active LOW — pulls OUT low when beam is broken)
- **Range:** 2 cm – 30 cm (adjustable via onboard potentiometer)
- **Pin used:** GPIO 21
- **Logic:** `read_gate() = True` (gate closed) when `GPIO21.value() == 0`

#### Active Buzzer
- **Type:** Active piezoelectric (self-oscillating — just apply DC voltage to make it beep)
- **Operating Voltage:** 3.3V – 5V (works directly from ESP32 GPIO at 3.3V)
- **Sound level:** ~85 dB at 10 cm
- **Pin used:** GPIO 26
- **Driven directly:** No transistor needed for 3.3V GPIO signal

---

## 4. Wiring & Pin Assignments

### Finalized Pin Table

```
ESP32 GPIO    Component                Notes
──────────────────────────────────────────────────────────────────────
GPIO  2       D2 Onboard LED           WiFi status indicator (built-in blue LED)
GPIO 16       Room 1 LED               via 220 Ω resistor → LED anode → cathode → GND
GPIO 17       Room 2 LED               via 220 Ω resistor → LED anode → cathode → GND
GPIO 18       Room 3 LED               via 220 Ω resistor → LED anode → cathode → GND
GPIO 19       Room 4 LED               via 220 Ω resistor → LED anode → cathode → GND
GPIO 32       HC-SR04 TRIG             Direct (3.3V output is sufficient to trigger)
GPIO 27       HC-SR04 ECHO             via 1 kΩ / 2 kΩ voltage divider ⚠️ MANDATORY
GPIO 25       SG90 Servo Signal        Direct (3.3V PWM signal works for SG90)
GPIO 26       Active Buzzer (+)        Direct (3.3V GPIO drives it)
GPIO 34       KY-026 Flame Sensor D0   Input-only pin — never set as output
GPIO 21       FC-51 IR Sensor OUT      Standard GPIO pin — input mode

5V  (VIN)     HC-SR04 VCC              ⚠️ MUST be 5V, NOT 3.3V
5V  (VIN)     SG90 VCC (Red wire)      ⚠️ MUST be 5V + 100µF cap across VCC-GND
3.3V          KY-026 VCC               3.3V is fine for this sensor
3.3V          FC-51 VCC                3.3V is fine for this sensor
GND           All component GNDs       All components share common ground
```

> **Critical Notes on GPIO 34:** This is an **ADC input-only** pin on the ESP32. It has no internal pull-up/pull-down resistor and cannot source or sink current. Always use it as `Pin.IN` only.

### LED Wiring (all 4 identical)

```
ESP32 GPIO (3.3V)
     │
   [220 Ω]         ← current limiting resistor
     │
  LED Anode (+)    ← long leg
  LED Cathode (-)  ← short leg
     │
    GND

Calculation:
  R = (Vcc − Vf) / I = (3.3V − 2.0V) / 0.010A = 130 Ω minimum
  220 Ω gives ~6 mA — well within ESP32's 12 mA safe limit per pin
  At 20mA rated current: 220 Ω × 20mA = 4.4V drop → LED barely lights
  At ~6mA: perfectly bright, no ESP32 damage risk
```

### HC-SR04 Voltage Divider (MANDATORY — prevents GPIO damage)

```
The HC-SR04 ECHO pin outputs 5V logic. ESP32 GPIO maximum input is 3.3V.
Connecting 5V directly WILL permanently damage the GPIO pin.

Solution: Resistor voltage divider

HC-SR04 ECHO (5V)
     │
   [1 kΩ]          ← upper resistor
     ├──────────────→ GPIO 27 (ESP32) — reads ~3.33V ✓
   [2 kΩ]          ← lower resistor
     │
    GND

Voltage at GPIO 27 = 5V × (2kΩ / (1kΩ + 2kΩ)) = 5V × 0.667 = 3.33V ✓ Safe
```

### SG90 Servo Wiring

```
SG90 Red Wire   (VCC)    → 5V rail (VIN pin on ESP32)
SG90 Brown Wire (GND)    → GND rail
SG90 Orange Wire(Signal) → GPIO 25

⚠️ CRITICAL: Add 100 µF electrolytic capacitor:
   (+) leg → 5V rail (close to servo connector)
   (-) leg → GND rail
   
Why: Servo draws 250-500mA when moving, causing voltage spikes that
     can reset/crash the ESP32 or corrupt memory writes.
     The capacitor absorbs these transient spikes.
```

### D2 Status LED Behaviour

| ESP32 State | LED Behaviour | Blink Rate |
|-------------|---------------|------------|
| Searching for WiFi | Slow blink | 500 ms |
| Captive portal (AP mode) | Fast blink | 100 ms |
| Connected to WiFi | Solid ON | — |

---

## 5. ESP32 Firmware (MicroPython)

All firmware files live in the `esp32/` directory and are uploaded directly to the ESP32's flash filesystem.

### File Overview

```
esp32/
├── main.py          # Boot entry point + 3-thread orchestrator
├── config.py        # All constants (pins, intervals, defaults)
├── config.json      # Runtime config (WiFi credentials, API URL) — written by captive portal
├── wifi.py          # WiFi STA connection + config.json read/write
├── wifi_manager.py  # Captive portal (AP mode setup page)
├── hardware.py      # D2 WiFi status LED (non-blocking blink)
├── api.py           # HTTP client: POST /sensor-data, GET /command/pending, GET /health
├── sensors.py       # Reads KY-026 flame sensor + FC-51 IR gate sensor
├── leds.py          # Controls the 4 room LEDs (GPIO 16/17/18/19)
├── buzzer.py        # Active buzzer on/off (GPIO 26)
└── radar.py         # SG90 sweep + HC-SR04 distance in background thread
```

### 5.1 WiFi Connection — wifi.py

**Purpose:** Connect to a saved WiFi network using credentials from `config.json`.

**How it works:**
1. `connect_wifi()` is called at boot from `main.py`
2. Reads `config.json` to get SSID and password. If the file doesn't exist, uses hardcoded defaults from `config.py`.
3. Activates the ESP32's STA (Station) interface and calls `wlan.connect(ssid, pwd)`
4. Polls `wlan.isconnected()` every 250ms, up to 10 seconds (40 attempts × 250ms)
5. Calls `update_led()` on every poll so the D2 LED blinks during the attempt
6. Returns `True` if connected, `False` if failed after 10 seconds

**WiFi watchdog in main loop:**
The main loop also monitors `wifi_is_connected()`. If WiFi drops during operation, it calls `set_mode(MODE_DISCONNECTED)`, tries to reconnect, and continues. This prevents the ESP32 from getting stuck.

```python
# From main.py — WiFi watchdog in main loop
if not wifi_is_connected():
    set_mode(MODE_DISCONNECTED)
    if connect_wifi():
        print("[MAIN] Reconnected!")
    time.sleep_ms(100)
    continue
```

### 5.2 WiFi Manager (Captive Portal) — wifi_manager.py

**Purpose:** First-time setup. When WiFi connection fails (no saved credentials, wrong password), the ESP32 starts a WiFi access point and serves a configuration web page.

**How it works:**

1. `start_portal()` is called from `main.py` when `connect_wifi()` returns `False`
2. Disables the STA (station) WiFi interface to free ~20KB RAM
3. Starts an access point (AP) with SSID `SmartHome-Setup`, password `12345678`
4. Opens a raw TCP socket on port 80, binds to `0.0.0.0`, listens for connections
5. Serves an HTML form at `http://192.168.4.1` that asks for:
   - WiFi SSID
   - WiFi Password  
   - API Server URL (the Render.com backend URL)
6. When the form is submitted (GET request to `/save?ssid=...&password=...&api=...`):
   - Parses URL-encoded parameters
   - URL-decodes special characters (spaces, `%20`, `+`, etc.)
   - Saves to `config.json` via `wifi.save_config()`
   - Sends a "Saved! Restarting..." page
   - Calls `machine.reset()` after 2 seconds

**Non-blocking design:** The server uses `s.settimeout(0.1)` so `accept()` times out every 100ms, allowing the main loop to call `update_led()` in between, keeping the D2 LED blinking during AP mode.

**To use the captive portal:**
1. Power on the ESP32 with no valid `config.json`
2. Connect your phone/laptop to WiFi `SmartHome-Setup` (password: `12345678`)
3. Open a browser and navigate to `http://192.168.4.1`
4. Fill in your WiFi credentials and the backend API URL
5. Submit → ESP32 saves and reboots

### 5.3 Hardware LED Status — hardware.py

**Purpose:** Non-blocking D2 LED blink to indicate WiFi connection state.

**Key design:** Standard `time.sleep()` blocks the CPU. Instead, `update_led()` checks if enough time has elapsed since the last toggle using `time.ticks_diff()`, then toggles if needed. This means it can be called at any frequency and will only blink at the correct rate.

```python
def update_led():
    """Call this as often as possible inside loops."""
    if _mode == MODE_CONNECTED:
        return  # Already forced solid ON in set_mode()
    
    interval = 20 if _mode == MODE_AP else 500
    now = time.ticks_ms()
    if time.ticks_diff(now, _last_ms) >= interval:
        _led_state = not _led_state
        _led.value(_led_state)
        _last_ms = now
```

**Modes:**
- `MODE_DISCONNECTED (0)`: 500ms blink — slow, "looking for WiFi"
- `MODE_AP (1)`: 20ms blink (very fast) — "configuration needed"
- `MODE_CONNECTED (2)`: Solid ON — "connected and running"

### 5.4 Configuration — config.py & config.json

**`config.py`** stores compile-time constants that never change:

```python
# GPIO pin assignments
WIFI_LED_PIN = 2
LED_PINS     = [16, 17, 18, 19]  # Room 1-4
SERVO_PIN    = 25
TRIG_PIN     = 32
ECHO_PIN     = 27
BUZZER_PIN   = 26
FLAME_PIN    = 34
IR_PIN       = 21

# API timing
API_HEALTH_INTERVAL_MS   = 250000  # 250s — keeps Render.com free tier awake
SENSOR_POST_INTERVAL_MS  =    400  # 400ms between sensor POSTs
COMMAND_POLL_INTERVAL_MS =    300  # 300ms command poll cycle

# Fallback defaults (used if config.json missing)
DEFAULT_WIFI_SSID     = "test"
DEFAULT_WIFI_PASSWORD = "12345678"
DEFAULT_API_BASE      = "http://192.168.1.5:8000"
AP_SSID               = "SmartHome-Setup"
AP_PASSWORD           = "12345678"
```

**`config.json`** is written by the captive portal and read at boot. It stores runtime configuration:

```json
{
    "wifi_ssid": "YourNetworkName",
    "wifi_password": "YourPassword",
    "api_base": "https://your-backend.onrender.com"
}
```

The `api.py` module reads `api_base` from this file and validates it starts with `http` to prevent crashes from empty or malformed URLs.

### 5.5 API Communication — api.py

**Purpose:** All HTTP communication between the ESP32 and the FastAPI backend.

**Design rules:**
- Every function catches all exceptions and returns a safe default — never crashes the calling thread
- Closes every response object with `r.close()` immediately after reading to free RAM (MicroPython has very limited heap)
- Prints `[API]` prefixed status for debugging over serial
- Uses a 2-second timeout on all requests (reduces worst-case blocking from 10s to 2s)

**Functions:**

```python
def ping_health():
    """GET /health — verifies full pipeline, keeps Render.com alive"""
    # Called every 250 seconds from _sensor_thread

def send_sensor_data(payload):
    """POST /sensor-data — sends radar sweep + flame + gate + LED states"""
    # Called every 400ms from _sensor_thread
    # payload = {"sweep": [...], "flame": bool, "gate": bool, "leds": {...}}

def get_pending_commands():
    """GET /command/pending — fetches + clears command queue"""
    # Called every 300ms from _cmd_thread
    # Returns {"commands": [...]} or {"commands": []} on failure
```

**API base URL caching:** The first call to any API function reads `config.json` to get the backend URL and caches it in `_base_url`. Subsequent calls use the cached value — no file I/O on every request.

### 5.6 Sensors — sensors.py

**Purpose:** Read the two passive sensors.

**Flame sensor (KY-026):**
- Both sensors use **active LOW logic**: output is 0 (LOW) when triggered, 1 (HIGH) when not triggered
- `read_flame()` returns `True` when `GPIO34.value() == 0` (flame detected)
- Read directly in `_update_buzzer()` in the main loop — zero latency, no network round trip needed

```python
def read_flame():
    """Returns True if flame detected. Active LOW logic."""
    return _flame.value() == 0
```

**Gate sensor (FC-51 IR):**
- `read_gate()` returns `True` (gate closed/object blocking IR beam) when `GPIO21.value() == 0`
- Read in `_sensor_thread` and included in the sensor payload

```python
def read_gate():
    """Returns True if gate is closed (beam broken). Active LOW logic."""
    return _ir.value() == 0
```

### 5.7 LEDs — leds.py

**Purpose:** Control the 4 room LEDs via GPIO.

**Internal state:** Maintains a `_states = [0, 0, 0, 0]` list that tracks the on/off state of each LED.

**Functions:**
- `set_room(room, state)` — sets a single LED (room = 1-4, state = 0 or 1)
- `set_all(state)` — sets all 4 LEDs to the same state
- `get_states()` — returns `{"room1": 0, "room2": 0, ...}` for inclusion in sensor payload

LEDs are driven directly from ESP32 GPIO pins through 220 Ω resistors. No PWM — simple on/off.

### 5.8 Buzzer — buzzer.py

**Purpose:** Simple active buzzer control.

```python
def on():  _buzz.value(1)   # Apply 3.3V → buzzer beeps
def off(): _buzz.value(0)   # Remove voltage → silence
```

The buzzer state machine (`_update_buzzer`) in `main.py` calls `on()` and `off()` based on priority logic — it never sleeps, it just toggles at the right time.

### 5.9 Radar — radar.py

**Purpose:** Sweep the SG90 servo 15°→165°→15° continuously, take an HC-SR04 distance reading at each step, and buffer the results for the sensor POST thread to drain.

**Internal architecture:**

```
_sweep_thread() runs in background via _thread.start_new_thread()

  At each step (every ~22ms per step × 50 steps = ~1.1s per half-sweep):
  1. set_angle(_angle)        — move servo to current angle
  2. time.sleep_ms(22)        — settle time (let servo reach position)
  3. dist = get_distance()    — fire HC-SR04, read echo
  4. _latest = {angle, dist}  — update atomic snapshot for buzzer
  5. _buf.append({seq, angle, distance, dir, ts})  — add to rolling buffer
  6. _angle += _direction     — advance angle
  7. if at limit: reverse     — bounce at 15° and 165°
```

**Rolling buffer:** `_buf` holds up to 60 measurements. Protected by a `_thread.allocate_lock()` mutex since both the radar thread (writes) and sensor thread (reads/clears) access it.

**`get_and_drain()`:** Called by `_sensor_thread` every 400ms. Acquires the lock, copies the buffer, clears it, releases the lock. Adds `rel_ms` to each item (negative milliseconds relative to the drain time). Returns the drained list for inclusion in the sensor payload.

**Why 3° steps?** At 3° per step with 22ms settle time, the servo completes one half-sweep (150°) in about 1.1 seconds. This gives ~50 data points per sweep direction, which is enough resolution for meaningful radar visualization without sacrificing sweep speed.

**`get_latest()`:** Returns just the most recent `{angle, distance}` snapshot, used by `_update_buzzer()` in the main loop for real-time proximity detection without needing to acquire the buffer lock.

**HC-SR04 distance calculation:**
```python
duration = time_pulse_us(_echo, 1, 11600)  # wait for ECHO HIGH, max 11.6ms
# 11.6ms timeout = ~200cm range (practical indoor limit)
dist_cm = (duration * 0.0343) / 2
# 0.0343 = speed of sound in cm/µs
# Divide by 2 because sound travels to object AND back
return round(dist_cm, 2) if 2 < dist_cm <= 400 else None
```

Returns `None` when:
- No object in range (timeout)
- Object closer than 2cm (sensor dead zone)
- Object surface absorbs/deflects sound (soft surfaces, angled hard surfaces)

**Servo duty cycle:**
```python
def _duty(angle):
    """Convert 0-180° to SG90 duty cycle (ESP32 50Hz, 0-1023 range)."""
    return int((angle / 180) * 75 + 40)
```

### 5.10 Orchestrator — main.py

**Purpose:** Boot sequence, thread management, buzzer state machine, and WiFi watchdog.

**Boot sequence:**
```python
connected = connect_wifi()      # Try to connect with saved credentials
if not connected:
    start_portal()              # If failed, start setup captive portal

radar.start()                   # Start radar sweep thread
_thread.start_new_thread(_cmd_thread, ())     # Start command poll thread
_thread.start_new_thread(_sensor_thread, ())  # Start sensor POST thread

while True:                     # Main loop — local hardware only
    update_led()
    _update_buzzer(now, radar.get_latest()["distance"])
    # WiFi watchdog...
    time.sleep_ms(15)
```

**3-thread architecture — why it was necessary:**

Originally the ESP32 used a single-threaded main loop doing everything sequentially. The problem: `urequests.post()` (the HTTP call to the backend) takes 200ms–3000ms depending on server response time (Render.com free tier spins up). While one HTTP call was blocking, the servo couldn't move and the buzzer couldn't react. This caused:
- Choppy servo movement (visible pauses every 400ms)
- Buzzer lag (couldn't react to proximity within 15ms)
- Command lag (stacked HTTP calls could delay a command by 5-10 seconds)

The fix was moving HTTP calls to dedicated background threads so the main loop ONLY handles local hardware with no I/O.

**Buzzer state machine (`_update_buzzer`):**

The buzzer operates on a 4-level priority system, evaluated every ~15ms in the main loop:

| Priority | Condition | Buzzer Behaviour |
|----------|-----------|-----------------|
| P1 (highest) | `read_flame() == True` | Solid ON (immediate, zero latency — reads sensor directly) |
| P2 | Manual beep timer active | ON until `_manual_beep_end` timestamp expires |
| P3 | Protect mode + object detected | Variable rate based on `radar.get_latest()["distance"]` |
| P4 (lowest) | None of the above | OFF |

**P3 proximity beep rates:**
| Distance | Buzz-off interval | Description |
|----------|-------------------|-------------|
| < 25 cm | 40 ms | Very rapid — danger zone |
| < 50 cm | 130 ms | Fast |
| < 80 cm | 320 ms | Moderate |
| < 110 cm | 620 ms | Slow warning |
| ≥ 110 cm | Silent | Out of range |

The buzz-ON interval is fixed at 50ms. The buzz-OFF interval changes based on distance. The state machine tracks whether the buzzer is currently ON or OFF and flips it when the appropriate interval has elapsed — no `time.sleep()` is ever called.

---

## 6. Backend (FastAPI + Python)

The backend is a Python FastAPI application that acts as the **central hub** connecting the ESP32 and the browser dashboard.

### File Overview

```
backend/
├── main.py                    # FastAPI app entry point + startup/shutdown + CORS
├── requirements.txt           # Python dependencies
├── render.yaml                # Render.com deployment configuration
├── .env                       # Local environment variables (NOT committed to git)
├── .env.example               # Template for .env
└── app/
    ├── __init__.py
    ├── state.py               # In-memory shared state (single source of truth)
    ├── db.py                  # MongoDB Atlas connection (Motor async driver)
    ├── ws_manager.py          # WebSocket connection manager (broadcast to all clients)
    └── routes/
        ├── __init__.py
        ├── health.py          # GET /health
        ├── sensor.py          # POST /sensor-data, GET /sensor-data/latest
        ├── commands.py        # POST /command, GET /command/pending, GET /command/queue
        ├── ws.py              # WS /ws (WebSocket endpoint)
        ├── auth.py            # POST /auth/login, GET /auth/verify, etc.
        └── stats.py           # GET /stats/today, GET /stats/recent
```

### 6.1 Entry Point — main.py

**Responsibilities:**
1. Loads `.env` file via `python-dotenv`
2. Creates the FastAPI app with CORS middleware (`allow_origins=["*"]` — all origins allowed since this is a personal IoT project)
3. Registers all route routers
4. Defines the `lifespan` context manager:
   - **Startup:** Connects to MongoDB Atlas, starts the ESP32 watchdog background task
   - **Shutdown:** Disconnects from MongoDB cleanly

**ESP32 Watchdog:**
```python
async def _esp32_watchdog():
    while True:
        await asyncio.sleep(3)
        if app_state.esp32_online and (time.time() - app_state.last_sensor_post_ts) > 5:
            app_state.esp32_online = False
            await ws_manager.broadcast({"type": "esp32_status", "data": {"online": False}})
```
Runs every 3 seconds. If no `/sensor-data` POST has arrived in more than 5 seconds, marks the ESP32 as offline and broadcasts to all browsers. This handles network drops, ESP32 reboots, or free-tier Render cold starts.

**CORS Configuration:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```
Allows the Vercel-hosted frontend to make HTTP and WebSocket requests to the Render-hosted backend without CORS errors.

### 6.2 In-Memory State — state.py

**Purpose:** Single source of truth for all runtime data. All routes read from and write to this module.

```python
# Command queue — commands the ESP32 hasn't collected yet
pending_commands: list[dict] = []

# Latest sensor snapshot from ESP32 (HTTP fallback)
latest_sensor: dict = {}

# Authoritative LED states — backend is the authority, NOT the ESP32
led_states: dict = {"room1": 0, "room2": 0, "room3": 0, "room4": 0}

# Protect mode flag
protect_mode: bool = False

# Flame edge detection (previous state, to detect rising/falling edge)
last_flame_state: bool = False

# Gate edge detection
last_gate_state: bool = False

# ESP32 liveness tracking
last_sensor_post_ts: float = 0.0
esp32_online: bool = False

# LED session tracking (for MongoDB writes on turn-off)
led_on_since: dict = {"room1": None, "room2": None, "room3": None, "room4": None}
```

**Key design decision:** The backend is the authority for `led_states`, NOT the ESP32. When the dashboard sends a command to turn on a light, the backend immediately updates `state.led_states` and broadcasts to all browsers. The ESP32 will execute the command within 300ms, but the browser UI updates instantly without waiting.

### 6.3 WebSocket Manager — ws_manager.py

**Purpose:** Manages all active WebSocket connections and broadcasts to them.

```python
class ConnectionManager:
    def __init__(self):
        self._connections: list[WebSocket] = []
    
    async def connect(self, ws):
        await ws.accept()
        self._connections.append(ws)
    
    def disconnect(self, ws):
        self._connections.remove(ws)
    
    async def broadcast(self, data: dict):
        dead = []
        for ws in self._connections:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections.remove(ws)
    
    @property
    def count(self):
        return len(self._connections)

manager = ConnectionManager()
```

All routes that need to push data to browsers call `await manager.broadcast(payload)`. The manager handles dead connections gracefully.

### 6.4 MongoDB Connection — db.py

**Purpose:** Async MongoDB connection using Motor (the async Motor driver for MongoDB).

**Connection flow:**
1. Reads `MONGODB_URI` from environment variable
2. If not set, prints a warning and runs without persistence (local dev mode — stats simply won't be saved)
3. Creates a `AsyncIOMotorClient` with a 5-second server selection timeout
4. Pings `admin.command("ping")` to verify the connection
5. Selects the `smart_home` database
6. Creates indexes for efficient date-based queries:
   - `led_sessions`: indexed on `turned_on` and `room`
   - `flame_events`: indexed on `detected_at`
   - `gate_events`: indexed on `timestamp`

**Graceful degradation:** If MongoDB is unavailable, `db.is_connected()` returns `False` and all route handlers check this before writing. The application runs fully without MongoDB — it just won't persist analytics data.

### 6.5 Route: /health

```
GET /health
```

Returns `{"status": "ok"}`. 

Called by the ESP32 every 250 seconds to keep Render.com's free tier from spinning down (Render free tier sleeps after 15 minutes of inactivity). The 250s interval ensures the backend never sleeps.

### 6.6 Route: /sensor-data

```
POST /sensor-data    — ESP32 sends every 400ms
GET  /sensor-data/latest  — HTTP fallback for browsers without WS
```

**POST handler flow:**
1. Receives JSON payload: `{sweep, flame, gate, leds}`
2. Updates `state.last_sensor_post_ts = time.time()` and marks `state.esp32_online = True`
3. If ESP32 was previously offline, broadcasts `esp32_status {online: True}` to all browsers
4. Extracts the last item from the sweep array for the latest angle/distance snapshot
5. **Flame edge detection:**
   - If `flame == True` and `state.last_flame_state == False` → **rising edge** → writes flame event to MongoDB with `detected_at = now, cleared_at = None`
   - If `flame == False` and `state.last_flame_state == True` → **falling edge** → updates the open flame event with `cleared_at = now, duration_sec = elapsed`
6. **Gate edge detection:**
   - If `gate != state.last_gate_state` → writes gate event `{timestamp: now, state: "open"|"closed"}`
7. **Broadcasts to all WebSocket clients:**
   ```json
   {
     "type": "sensor_update",
     "data": {
       "sweep": [...],
       "angle": 90,
       "distance": 45.3,
       "flame": false,
       "gate": false,
       "leds": {"room1": 1, "room2": 0, ...},
       "protect_mode": false,
       "esp32_online": true
     }
   }
   ```
8. Returns `{"success": True}`

**Note on flame detection:** The ESP32's buzzer activates on flame detection directly in its main loop (zero network latency). The backend does NOT queue a beep command when flame is detected, because that would cause double/stacked beeps (ESP32 already beeping + a delayed backend command also triggering a beep).

### 6.7 Route: /command

```
POST /command         — dashboard sends commands
GET  /command/pending — ESP32 polls every 300ms (reads + clears queue)
GET  /command/queue   — debug: inspect without consuming
```

**Command types:**

| Action | Parameters | Effect |
|--------|-----------|--------|
| `set_led` | `{room: 1-4, state: 0\|1}` | Toggles one room LED |
| `set_all` | `{state: 0\|1}` | Sets all 4 LEDs simultaneously |
| `beep` | `{duration_ms: 500}` | One-shot buzzer beep for N milliseconds |
| `protect_mode` | `{state: true\|false}` | Enables/disables proximity alarm mode |
| `all_off` | — | Turns off all LEDs and buzzer |

**Command flow:**
1. Dashboard sends `POST /command` with command JSON
2. Backend immediately updates `state.led_states` or `state.protect_mode`
3. Backend appends command to `state.pending_commands` list
4. Backend broadcasts `state_update` to ALL browsers via WebSocket
5. Browser sees the state change in <50ms (one WS round trip)
6. ESP32 polls `GET /command/pending` next cycle (within 300ms)
7. Backend returns + clears the queue on that poll
8. ESP32 executes the command (LED toggles, buzzer beeps, etc.)
9. Physical hardware changes within ~500ms total from button click

**LED session tracking:**
When `set_led` or `set_all` changes a room LED from OFF→ON, the timestamp is stored in `state.led_on_since[room]`. When it changes from ON→OFF, the duration is calculated and a session document is written to MongoDB:

```json
{
  "room": "room1",
  "turned_on": "2026-05-26T10:30:00Z",
  "turned_off": "2026-05-26T11:30:00Z",
  "duration_sec": 3600,
  "battery_mah": 0.02
}
```
`battery_mah` = `(duration_sec / 3600) × 20mA` (LED draws 20mA at 3.3V from GPIO)

### 6.8 Route: /ws (WebSocket)

```
WS /ws   — browsers connect here for real-time updates
```

**Connection flow:**
1. Browser connects → `manager.connect(ws)` adds it to the active set
2. Server immediately sends full state snapshot:
   ```json
   {"type": "init", "data": {"leds": {...}, "protect_mode": false, "sensor": {...}, "esp32_online": true}}
   ```
3. Server enters heartbeat loop: waits up to 20 seconds for client messages
4. If no message in 20s, sends `{"type": "ping"}` to keep the connection alive through proxies and Render.com's load balancer
5. On disconnect, removes from active connection set

**Message types the browser receives:**

| Type | When Sent | Payload |
|------|-----------|---------|
| `init` | On WebSocket connect | Full state snapshot |
| `sensor_update` | Every ESP32 POST (~400ms) | Radar sweep + flame + gate + leds + protect_mode |
| `state_update` | Every dashboard command | Updated led_states + protect_mode + esp32_online |
| `esp32_status` | On connect/disconnect detection | `{online: true/false}` |
| `ping` | Every 20s (heartbeat) | — |

### 6.9 Route: /auth/*

```
POST /auth/login      — verify credentials, return session token
GET  /auth/verify     — validate token (called on every protected page load)
POST /auth/logout     — invalidate session token
POST /auth/setup      — one-time first admin user creation (locked after first use)
```

**Authentication model:**
- Credentials stored in MongoDB `users` collection: `{username, password_hash, role, created_at}`
- Password hashed with SHA-256 (sufficient for a personal project)
- On successful login: generates a 32-byte URL-safe random token (`secrets.token_urlsafe(32)`)
- Token stored in `_sessions` dict (in-memory): `{token: username}`
- Sessions reset on server restart (acceptable for a personal IoT project)

**Token flow:**
1. User submits login form → `POST /auth/login`
2. Backend verifies credentials against MongoDB `users` collection
3. On success: returns token in response body
4. Browser stores token in `sessionStorage` (not localStorage — clears on tab close)
5. Every protected page load: `GET /auth/verify` with `X-Auth-Token: <token>` header
6. If token invalid: browser redirects to login page
7. Logout: `POST /auth/logout` invalidates token in `_sessions`

**First-time setup:**
```bash
curl -X POST https://your-backend.onrender.com/auth/setup \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "yourpassword"}'
```
After the first user exists, this endpoint returns 403 Forbidden.

### 6.10 Route: /stats/*

```
GET /stats/today          — today's LED usage, flame/gate events
GET /stats/recent?days=7  — last N days LED usage for charts
```

**`/stats/today` response structure:**
```json
{
  "date": "2026-05-26",
  "hours_today": 14.5,
  "db_connected": true,
  "led": {
    "room1": {"on_min": 45.2, "sessions": 3, "avg_session_min": 15.1, "pct_of_day": 5.2, "energy_wh": 0.05},
    "room2": {"on_min": 120.0, "sessions": 5, ...},
    "room3": {...},
    "room4": {...}
  },
  "energy": {
    "led_wh": 0.18,
    "led_mah": 54.5,
    "note": "LED energy only. ESP32/servo draw not measured."
  },
  "flame_events": [
    {"id": "abc123", "detected_at": "2026-05-26T08:30:00Z", "cleared_at": "2026-05-26T08:30:05Z", "duration_sec": 5.0}
  ],
  "gate_events": [
    {"id": "xyz789", "timestamp": "2026-05-26T09:00:00Z", "state": "open"},
    {"id": "xyz790", "timestamp": "2026-05-26T09:01:00Z", "state": "closed"}
  ],
  "gate_opens": 1,
  "gate_closes": 1
}
```

**LED energy calculation:**
- Each LED draws 20 mA at 3.3V (from GPIO through 220 Ω resistor)
- Power per LED: `P = I × V = 0.020A × 3.3V = 0.066W = 66mW`
- Energy: `E = P × t = 0.066W × (on_minutes / 60) Wh`

**Important limitation:** Only LED energy is calculated from actual measurement data. The ESP32 microcontroller (~80mA), servo motor (~120mA peak), HC-SR04, and sensors also consume power, but we have no current sensor to measure them.

**"Today" calculation:** Uses the server's local timezone to define midnight. If the server is in UTC (as Render.com is), "today" starts at UTC midnight. The `_today_start()` function converts local midnight to UTC for the MongoDB query.

---

## 7. Frontend (Vanilla JS + Bootstrap 5)

The frontend is a collection of static HTML, CSS, and JavaScript files served from Vercel's CDN.

### File Overview

```
frontend/
├── index.html          # Landing page (served at root URL)
├── dashboard.html      # Main IoT dashboard (protected — requires login)
├── stats.html          # Analytics page (protected — requires login)
├── css/
│   ├── home.css        # Landing page styles (self-contained)
│   ├── style.css       # Dashboard styles
│   └── stats.css       # Stats page styles
├── js/
│   ├── config.js       # API base URL + WebSocket URL (reads from config.json or hardcoded)
│   ├── auth.js         # Shared auth utilities (token storage, redirect, verify)
│   ├── ws.js           # WebSocket client (persistent, auto-reconnect)
│   ├── radar.js        # Radar canvas renderer (60fps, ping-pong, EMA smoothing)
│   ├── leds.js         # LED toggle buttons (optimistic UI)
│   ├── sensors.js      # Flame/gate/protect-mode display
│   ├── main.js         # Dashboard init + ESP32 online/offline watchdog
│   ├── home.js         # Landing page logic (login form, animations)
│   ├── stats.js        # Stats page data fetching and chart rendering
│   └── api.js          # Shared HTTP API wrapper (fetch with auth headers)
└── assets/
    ├── 01 esp32_wroom_32_-_low_poly_photorealistic.glb
    ├── IR_sensor/
    │   └── source/ir sensor.glb
    ├── new_hc-sr04.glb
    ├── servomotor_sg90.glb
    ├── buzzer.glb
    ├── breadboard.glb
    └── rechargeable_lithium_ion_battery_-_18650.glb
```

### 7.1 Landing Page — index.html

The landing page (`index.html`) is served when you visit the root URL of the Vercel deployment. It is a public marketing/information page — no authentication required.

**Sections:**
1. **Hero** — Project title, animated tagline, live backend status pill, CTA button
2. **Components** — Interactive 3D model cards for each hardware component
3. **Tech Stack** — Animated cards for each technology used
4. **Connection / Login** — Login form to authenticate and reach the dashboard

**3D Component Models:** Uses Google's `<model-viewer>` custom element (loaded from a CDN). Each component card has a flip animation:
- **Front:** Interactive 3D model (drag to rotate, pinch to zoom)
- **Back:** Technical specifications for the component

Models are stored as `.glb` (GL Transmission Format Binary) files in the `assets/` directory. `.glb` is a self-contained binary format that includes geometry, materials, and textures in a single file — perfect for web delivery without texture loading issues.

The "Inspect 3D" button (⤢) opens a full-screen modal with a larger model viewer for detailed inspection.

### 7.2 Dashboard — dashboard.html

The main control interface, protected by authentication. Loaded after a successful login.

**Layout:**
- **Connection status bar** — WebSocket connection status + ESP32 online/offline indicator
- **Radar panel** — `<canvas>` element rendering the live radar sweep
- **LED controls** — 4 room toggle buttons with optimistic UI
- **Sensor status** — Flame detection, gate status, distance reading
- **Protect mode toggle** — Enable/disable proximity alarm
- **Alarm button** — Triggers a manual buzzer beep

**Script loading order:**
```html
<script src="js/config.js"></script>     <!-- Must be first — defines CONFIG -->
<script src="js/auth.js"></script>       <!-- Authentication utilities -->
<script src="js/api.js"></script>        <!-- HTTP wrapper -->
<script src="js/ws.js"></script>         <!-- WebSocket client -->
<script src="js/radar.js"></script>      <!-- Radar renderer -->
<script src="js/leds.js"></script>       <!-- LED controls -->
<script src="js/sensors.js"></script>    <!-- Sensor display -->
<script src="js/main.js"></script>       <!-- Initialization + auth guard -->
```

### 7.3 Stats Page — stats.html

The analytics page, also protected by authentication. Shows historical data from MongoDB.

**Sections:**
1. **Today's Overview** — Hours elapsed today, DB connection status, gate open/close count
2. **LED Usage Bars** — Horizontal bar chart showing minutes-on per room today
3. **Battery / Energy** — Total mAh and Wh consumed by LEDs today
4. **7-Day Chart** — Stacked bar chart (one bar per day, stacked by room LED on-time)
5. **Flame Events** — List of today's flame detections with timestamps and duration
6. **Gate Activity** — Timeline of gate open/close events today

### 7.4 Configuration — config.js

**Purpose:** Centralizes the backend URL so it only needs to be changed in one place when the backend URL changes.

```javascript
const CONFIG = {
    API_BASE: "https://your-backend.onrender.com",
    WS_URL:   "wss://your-backend.onrender.com/ws",
};
```

All other JS files reference `CONFIG.API_BASE` and `CONFIG.WS_URL`. To point the frontend at a local backend for development, change these two strings.

### 7.5 WebSocket Client — ws.js

**Purpose:** Maintains a persistent WebSocket connection to the backend with automatic reconnection.

**Key features:**
- Connects to `CONFIG.WS_URL` on page load
- On disconnect, waits 2 seconds and reconnects automatically
- Dispatches a custom DOM event `ws-message` for each received message, allowing other JS modules to subscribe independently
- Tracks `wsConnected` state and updates the connection status indicator

**Message dispatching:**
```javascript
ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    document.dispatchEvent(new CustomEvent("ws-message", { detail: msg }));
};
```

Each module (`radar.js`, `leds.js`, `sensors.js`) listens for `ws-message` events and filters by `msg.type`.

### 7.6 Radar Canvas — radar.js

**Purpose:** Renders a real-time radar display on a `<canvas>` element at 60fps.

This is the most technically complex part of the frontend.

**Core concepts:**

**`scanHistory` map:**
A `Map<angleBucket, {distance, timestamp}>` that persists detected objects. Every incoming radar data point updates the corresponding angle bucket. Buckets fade out after 9 seconds without a new reading. Adjacent buckets with similar distances are drawn as arcs to show object outlines rather than isolated dots.

```javascript
// EMA smoothing prevents jitter from ultrasonic sensor noise
const EMA_ALPHA = 0.65;
if (existing) {
    newDistance = existing.distance * (1 - EMA_ALPHA) + distance * EMA_ALPHA;
}
scanHistory.set(angleBucket, { distance: newDistance, timestamp: now });
```

**Ping-pong extrapolation:**
Between WebSocket messages (~400ms gap), the radar sweep line continues moving in the correct direction, bouncing at the limits, to simulate the physical servo position in real-time.

```javascript
_pingPong(startAngle, startDir, speedDegSec, elapsedSec) {
    // Simulates physical servo bouncing at MIN_ANGLE (15°) and MAX_ANGLE (165°)
    // Handles multiple bounces during a long gap correctly
    let span = MAX_ANGLE - MIN_ANGLE;  // 150°
    let dist = speedDegSec * elapsedSec;
    // ... modulo arithmetic to simulate bounce ...
}
```

**Explicit `dir` field:**
Each radar data point from the ESP32 includes `dir: 1` (sweeping toward 165°) or `dir: -1` (sweeping back toward 15°). The frontend uses `lastItem.dir` directly — no guessing from angle deltas. This was necessary because direction inference from angle changes fails when a sweep batch spans a servo bounce point.

**60fps render loop:**
```javascript
// Started once on init — runs every ~16ms
function _renderLoop() {
    const now = Date.now();
    _drawBackground();       // Dark grid with range rings
    _drawScanHistory();      // All stored angle blips (fading)
    _drawSweepLine();        // Current sweep position (extrapolated)
    requestAnimationFrame(_renderLoop);
}
```

**Grid rendering:**
- Range rings at 50cm, 100cm, 150cm, 200cm (labeled in cm)
- Angle gridlines every 30°
- Center crosshair
- Dark green neon colour scheme (`rgba(0, 255, 136, *)`)

### 7.7 LED Controls — leds.js

**Purpose:** Renders 4 room LED toggle buttons and handles user clicks.

**Optimistic UI:** When a user clicks a room button, the UI updates immediately (button toggles visually) without waiting for the ESP32 to confirm. The actual command is sent to the backend (`POST /command`), which broadcasts a `state_update` via WebSocket. If the command fails, the WS update would not arrive and the button would remain in the toggled state — acceptable for a personal project.

**Command sent on click:**
```javascript
async function toggleRoom(room) {
    const newState = 1 - currentStates[room];  // flip
    await sendCommand({ action: "set_led", room: room, state: newState });
}
```

**Incoming WS updates:** When `ws-message` with `type: "sensor_update"` or `type: "state_update"` arrives, the LED states are updated to match `msg.data.leds`.

### 7.8 Sensors Display — sensors.js

**Purpose:** Updates the flame, gate, and distance displays on the dashboard.

Listens for `ws-message` events and updates DOM elements:
- `#flame-status` — shows 🔥 and turns red when `data.flame == true`
- `#gate-status` — shows OPEN/CLOSED based on `data.gate`
- `#distance-value` — shows latest distance reading from radar
- `#protect-toggle` — reflect current protect mode state
- `#alarm-btn` — sends `{action: "beep", duration_ms: 500}` on click

### 7.9 Stats Data — stats.js

**Purpose:** Fetches analytics from `/stats/today` and `/stats/recent` and renders charts.

**Data fetching:** Uses `fetch()` with the auth token in the `X-Auth-Token` header. Both endpoints are polled once on page load, with a manual refresh button.

**Chart rendering:** Uses vanilla JS `<canvas>` drawing (no chart library dependency):
- LED usage bars: horizontal bars scaled to max daily on-time
- 7-day chart: grouped vertical bars, one per day, coloured by room
- Flame events list: rendered as styled table rows
- Gate timeline: time-sorted list of state change events

### 7.10 Authentication — auth.js

**Purpose:** Shared authentication utilities used by all protected pages.

```javascript
const _AUTH_KEY = 'iot_auth_token';

function getAuthToken()       { return sessionStorage.getItem(_AUTH_KEY); }
function setAuthToken(token)  { sessionStorage.setItem(_AUTH_KEY, token); }
function clearAuthToken()     { sessionStorage.removeItem(_AUTH_KEY); }

async function verifyAuthToken() {
    const token = getAuthToken();
    if (!token) return false;
    const r = await fetch(CONFIG.API_BASE + '/auth/verify', {
        headers: { 'X-Auth-Token': token }
    });
    return r.ok;
}

async function requireAuth() {
    const valid = await verifyAuthToken();
    if (!valid) {
        clearAuthToken();
        window.location.replace('index.html');  // Redirect to landing page
        throw new Error('AUTH_REDIRECT');       // Stop further JS execution
    }
}

async function logoutAndRedirect() {
    // Invalidate server-side session
    await fetch(CONFIG.API_BASE + '/auth/logout', {
        method: 'POST', headers: { 'X-Auth-Token': getAuthToken() }
    });
    clearAuthToken();
    window.location.replace('index.html');
}
```

**Token storage:** `sessionStorage` (not `localStorage`) so the session clears when the browser tab is closed — appropriate for a shared device like a home control panel.

**`requireAuth()`** is called at the top of `main.js` (dashboard) and the stats page init. If it fails (token expired, server restarted), it redirects to the login page immediately.

---

## 8. MongoDB Schema & Analytics

### Database: `smart_home`

#### Collection: `users`

Stores admin user accounts for dashboard authentication.

```json
{
  "_id": ObjectId("..."),
  "username": "admin",
  "password_hash": "sha256_hex_string...",
  "role": "admin",
  "created_at": ISODate("2026-05-01T00:00:00Z")
}
```

#### Collection: `led_sessions`

One document per LED on→off cycle per room. Written when a room LED is turned OFF.

```json
{
  "_id": ObjectId("..."),
  "room": "room1",
  "turned_on":    ISODate("2026-05-26T10:30:00Z"),
  "turned_off":   ISODate("2026-05-26T11:30:00Z"),
  "duration_sec": 3600,
  "battery_mah":  0.02
}
```

**Indexes:** `turned_on` (for date-range queries), `room` (for per-room queries)

**If a LED is still ON when the stats are queried**, the backend adds the in-progress session (from `state.led_on_since[room]`) to the totals without writing to MongoDB yet — the write happens when the LED is eventually turned off.

#### Collection: `flame_events`

One document per flame detection burst. Created on rising edge, updated on falling edge.

```json
{
  "_id": ObjectId("..."),
  "detected_at":  ISODate("2026-05-26T08:30:00Z"),
  "cleared_at":   ISODate("2026-05-26T08:30:05Z"),
  "duration_sec": 5.0
}
```

If the server restarts while a flame event is open (flame still active at restart), `cleared_at` and `duration_sec` will remain `null`. This is an acceptable edge case for a personal project.

**Index:** `detected_at` (for today's date-range query)

#### Collection: `gate_events`

One document per gate state transition (open or closed).

```json
{
  "_id": ObjectId("..."),
  "timestamp": ISODate("2026-05-26T09:00:00Z"),
  "state":     "open"
}
```

**Index:** `timestamp` (for today's date-range query)

### Analytics Calculations

| Metric | Formula |
|--------|---------|
| LED on-time today | Sum of `duration_sec` from `led_sessions` where `turned_on >= midnight_utc` |
| LED energy (Wh) | `(on_min / 60) × 0.020A × 3.3V` per room |
| LED energy (mAh) | `energy_wh / 3.3V × 1000` |
| Avg session length | `total_on_min / session_count` per room |
| % of day | `(on_min / 60) / hours_since_midnight × 100` |
| Gate opens today | Count of gate_events with state="open" and timestamp >= midnight |
| Gate closes today | Count of gate_events with state="closed" and timestamp >= midnight |

---

## 9. Deployment

### 9.1 Backend on Render

The FastAPI backend is deployed to Render.com as a web service.

**render.yaml** (Infrastructure as Code):
```yaml
services:
  - type: web
    name: smart-home-backend
    env: python
    rootDir: backend
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: PYTHON_VERSION
        value: "3.11"
```

**Deployment steps:**
1. Push the project to a GitHub repository
2. Create a Render.com account
3. New → Web Service → Connect your GitHub repo
4. Render detects `render.yaml` and uses its configuration automatically
5. Add environment variables in Render dashboard:
   - `MONGODB_URI`: Your MongoDB Atlas connection string
6. Deploy — Render provides a URL like `https://smart-home-backend.onrender.com`
7. Update `backend/config.js` with this URL
8. Copy this URL into the ESP32's `config.json` `api_base` field (via captive portal)

**Free tier caveats:**
- Render free tier spins down after 15 minutes of inactivity (no requests)
- The ESP32 health ping every 250 seconds (4.2 minutes) prevents this spin-down
- First request after spin-down takes ~30 seconds (cold start) — subsequents are fast
- Free tier WebSockets work but may have higher latency than paid plans

**CORS:** The backend allows all origins (`*`) so any frontend (local or Vercel) can make requests without CORS errors.

### 9.2 Frontend on Vercel

The frontend is deployed to Vercel as a static site.

**Deployment steps:**
1. Ensure `frontend/js/config.js` has the correct Render backend URL
2. Create a Vercel account and connect your GitHub repository
3. Vercel auto-detects the frontend as a static site
4. Set the **root directory** to `frontend` in Vercel project settings
5. Deploy — Vercel provides a URL like `https://your-project.vercel.app`
6. The root URL automatically serves `index.html` (the landing page)
7. `dashboard.html` and `stats.html` are accessible at their direct paths

**URL routing:**
- `https://your-project.vercel.app/` → serves `frontend/index.html` (landing page)
- `https://your-project.vercel.app/dashboard.html` → dashboard
- `https://your-project.vercel.app/stats.html` → analytics

**Important:** `index.html` MUST be the landing/login page. Vercel serves the file named `index.html` for the root URL. If the dashboard is named `index.html`, it will show to unauthenticated users and the auth redirect causes a flash of the "Backend Offline" error before redirecting.

---

## 10. Local Development Setup

### Prerequisites

- **Python 3.11+** for the backend
- **Node.js** (optional — only needed if using a local HTTP server for the frontend)
- **MicroPython firmware** flashed to the ESP32
- **Thonny IDE** or **mpremote** for uploading files to the ESP32
- A **MongoDB Atlas** account (free tier is sufficient) or a local MongoDB instance

### MongoDB Atlas Setup

1. Go to [cloud.mongodb.com](https://cloud.mongodb.com)
2. Create a free cluster (M0 free tier)
3. Create a database user with read/write access
4. Whitelist your IP address (or `0.0.0.0/0` for anywhere)
5. Click "Connect" → "Connect your application" → copy the connection string
6. It looks like: `mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority`

### Backend Setup

```bash
# 1. Navigate to backend directory
cd backend

# 2. Create a virtual environment
python -m venv venv
venv\Scripts\activate     # Windows
# source venv/bin/activate  # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file from template
copy .env.example .env    # Windows
# cp .env.example .env    # macOS/Linux

# 5. Edit .env with your MongoDB URI
# MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority

# 6. Run the backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Backend is now running at: http://localhost:8000
# API docs at:               http://localhost:8000/docs
```

### Create First Admin User

```bash
curl -X POST http://localhost:8000/auth/setup \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "yourpassword"}'
```

This can only be done once. After a user exists, the endpoint returns 403.

### Frontend Setup

The frontend is plain static files — no build step needed.

```bash
# Option 1: Open directly in browser (some features may not work due to CORS)
# Just open frontend/index.html in a browser

# Option 2: Serve with Python's built-in server (recommended)
cd frontend
python -m http.server 3000
# Open: http://localhost:3000

# Option 3: Use a VS Code extension like "Live Server"
```

Update `frontend/js/config.js` to point to your local backend:
```javascript
const CONFIG = {
    API_BASE: "http://localhost:8000",
    WS_URL:   "ws://localhost:8000/ws",
};
```

### ESP32 Firmware Setup

**Prerequisites:**
1. Flash MicroPython firmware to your ESP32 ([download from micropython.org](https://micropython.org/download/ESP32_GENERIC/))
2. Install Thonny IDE from [thonny.org](https://thonny.org)

**Upload files:**
1. Open Thonny
2. Go to Tools → Options → Interpreter → MicroPython (ESP32) → Port (your COM port)
3. Upload all files from `esp32/` to the ESP32 root filesystem
4. Reboot the ESP32

**First boot with no config.json:**
1. ESP32 will fail to connect to WiFi (no credentials saved)
2. It starts the captive portal
3. D2 LED blinks very fast
4. Connect your phone/laptop to WiFi `SmartHome-Setup` (password: `12345678`)
5. Open browser → `http://192.168.4.1`
6. Enter your WiFi credentials and backend URL
7. Click Save & Restart
8. ESP32 reboots, connects to WiFi, D2 LED goes solid

**If config.json already exists:**
Edit it directly in Thonny:
```json
{
    "wifi_ssid": "YourNetworkName",
    "wifi_password": "YourPassword",
    "api_base": "https://your-backend.onrender.com"
}
```

### Verifying Everything Works

```bash
# 1. Check ESP32 is posting data (in Thonny shell / serial console):
[API] Base URL: https://your-backend.onrender.com
[RADAR] Sweep thread started
[SENSOR] Sensor POST thread started
[CMD] Command poll thread started
[API] Sensor data sent ✓

# 2. Check backend is receiving (in Render logs or terminal):
[SENSOR] ✓ ESP32 came online
INFO: POST /sensor-data 200 OK

# 3. Check the dashboard:
# Open https://your-project.vercel.app
# Log in
# Radar should be sweeping, status should show "Online"
```

---

## 11. Complete Data Flow Walkthrough

### Scenario: User turns on Room 1 LED

```
1. User clicks "Room 1" button on dashboard.html

2. leds.js (browser):
   - Button toggles visually immediately (optimistic UI)
   - Sends POST /command with {action: "set_led", room: 1, state: 1}

3. commands.py (backend):
   - Receives command
   - state.led_states["room1"] = 1        ← updates immediately
   - state.led_on_since["room1"] = now    ← starts session timer
   - state.pending_commands.append(cmd)   ← queues for ESP32
   - await manager.broadcast(state_update) ← pushes to all browsers
   - Returns {queued: True}

4. ws.js (browser):
   - Receives state_update via WebSocket
   - leds.js updates button to reflect confirmed state
   - (In practice looks instant — same as optimistic update)

5. _cmd_thread (ESP32), ~300ms later:
   - GET /command/pending
   - Backend returns [{action: "set_led", room: 1, state: 1}]
   - Backend clears pending_commands list
   - _handle_command() calls leds.set_room(1, 1)
   - GPIO 16 goes HIGH → Room 1 LED lights up

Total time from click to LED on: ~300-800ms (depending on network latency)
```

### Scenario: Flame detected

```
1. _sweep_thread (ESP32, radar.py):
   - Continuously sweeping — no flame involvement

2. _update_buzzer() (ESP32, main loop, every ~15ms):
   - Calls sensors.read_flame()
   - GPIO34 reads LOW (flame sensor active)
   - read_flame() returns True
   - P1 priority: buzzer.on() immediately
   - Buzzer starts beeping with ZERO network latency

3. _sensor_thread (ESP32):
   - Next POST includes {flame: True, ...}
   - Sends to POST /sensor-data

4. sensor.py (backend):
   - new_flame=True, state.last_flame_state=False → RISING EDGE
   - Writes to MongoDB: flame_events.insert_one({detected_at: now, cleared_at: None})
   - Broadcasts sensor_update to all browsers (flame: True)

5. sensors.js (browser):
   - Receives sensor_update
   - Updates #flame-status to show 🔥 FLAME DETECTED in red

6. When flame is cleared:
   - ESP32 buzzer immediately stops (next 15ms loop iteration)
   - Next sensor POST includes {flame: False}
   - Backend detects FALLING EDGE
   - Updates flame event: {cleared_at: now, duration_sec: elapsed}
   - Broadcasts sensor_update (flame: False) to browsers
```

### Scenario: Radar data flowing to browser

```
1. _sweep_thread (ESP32, radar.py), every ~22ms:
   - set_angle(angle)
   - time.sleep_ms(22)
   - dist = get_distance()  (HC-SR04: 10µs trigger, read echo pulse)
   - _buf.append({seq: N, angle: 90, distance: 45.3, dir: 1, ts: ticks_ms()})

2. _sensor_thread (ESP32), every 400ms:
   - sweep_buf = radar.get_and_drain()
   - Drains ~15-20 measurements accumulated since last drain
   - Adds rel_ms to each (e.g., -380, -350, ..., -20, 0)
   - POSTs {sweep: [...15 items...], flame: False, gate: False, leds: {...}}

3. sensor.py (backend):
   - Receives sweep array
   - Immediately broadcasts sensor_update with full sweep array

4. ws.js (browser):
   - Receives message, dispatches ws-message event

5. radar.js (browser):
   - processSweep(arr): sorts by seq, extracts dir from last item
   - For each item: updateScanHistory(angle, distance)
     - angle bucket = Math.round(angle / 3) * 3  (rounds to 3° grid)
     - EMA smoothing if existing reading at this bucket
     - scanHistory.set(bucket, {distance: smoothed, timestamp: now})
   - Updates lastAngle, lastDir, lastUpdateTime for extrapolation

6. radar.js _renderLoop() (60fps):
   - Calculates ping-pong extrapolated angle for sweep line:
     elapsed = Date.now() - lastUpdateTime
     displayAngle = _pingPong(lastAngle, lastDir, sweepSpeed, elapsed/1000)
   - Draws scanHistory blips (fading circles, connected by arcs for nearby detections)
   - Draws sweep line at extrapolated angle
   - requestAnimationFrame(self)
```

---

## 12. Key Design Decisions & Problems Solved

### Problem 1: Choppy Servo Movement & Command Lag

**Root cause:** Single-threaded ESP32 main loop. `urequests.post()` blocks for 200ms–3000ms on Render's free tier. While blocking, the servo couldn't move and the command poll couldn't run.

**Worst case (before fix):**
```
t=0:    sensor POST fires  → blocks 2s (slow WiFi to Render)
t=2000: command poll fires → blocks 2s (another slow call)
t=4000: next loop iteration begins
Command queued at t=500 → not executed until t=4000+ → 3.5s delay
```

**Solution:** 3-thread architecture
- Radar thread: servo + distance, never touches HTTP
- Sensor thread: POST every 400ms (independent of main loop)
- Command thread: poll every 300ms (independent of both)
- Main loop: only local hardware, never blocks

### Problem 2: Scattered Radar Dots

**Root cause:** Single snapshot per POST. With only 2 data points per second from a sweep that covers 120°/second, dots appeared at random angles and then faded.

**Solution:** Rolling buffer in radar.py. Every POST sends 12-20 measurements accumulated since the last POST. Frontend stores all measurements in `scanHistory` with 9-second lifetime. Connected as arcs to show object outlines.

### Problem 3: Sweep Line Freezes at Edges

**Root cause:** Linear extrapolation: `displayAngle = lastAngle + dir × speed × elapsed`. After servo bounces at 165°, `dir` was still +1, so extrapolation flew past 165° (clamped to 165°) and froze.

**Solution:** Ping-pong extrapolation — correctly simulates physical servo bouncing at limits, handles multiple bounces during long network gaps.

### Problem 4: Ultrasonic Distance Jitter

**Root cause:** HC-SR04 gives ±2-5cm variation per reading for the same static object.

**Solution:** Exponential Moving Average (EMA) per angle bucket: `smoothed = old × 0.35 + new × 0.65`. Fast enough to track real movement, stable enough to show a clean display for static objects.

### Problem 5: Left-Right Mirror on Radar

**Root cause:** Servo's 15° physically faced right side of room. Math formula `π - (angle × π/180)` put small angles on left of canvas, inverting the physical layout.

**Solution:** Changed to `angle × π/180` — small angles now on left of canvas, matching physical reality.

### Problem 6: Direction Inference Failure

**Root cause:** Frontend tried to infer sweep direction from `angleDelta = current - previous`. Fails when a batch spans a servo bounce point.

**Solution:** Added explicit `dir: 1|-1` field to every radar buffer item on the ESP32. Frontend reads `lastItem.dir` directly — no inference.

### Problem 7: Root URL Shows Backend Offline Flash

**Root cause:** `index.html` was the dashboard. Vercel serves it at root URL. Dashboard JS immediately tries to WebSocket-connect to backend. Connection fails briefly → shows "Backend Offline" overlay. Auth script kicks in and redirects to login page. User sees a flash of the error.

**Solution:** Renamed `home.html` (landing page) to `index.html` and `index.html` (dashboard) to `dashboard.html`. Updated all redirect paths. Root URL now correctly serves the public landing page with no auth or WebSocket requirements.

### Problem 8: Double Buzzer on Flame Detection

**Root cause:** Original design had both the ESP32 checking the flame sensor directly AND the backend queueing a beep command on flame detection. This caused the buzzer to be activated twice with a ~400ms delay between the direct read and the command arriving.

**Solution:** Removed the backend-queued beep on flame detection. ESP32 reads the flame sensor directly in its 15ms main loop and activates the buzzer immediately. Backend only logs the event to MongoDB — no command sent.

---

## 13. Folder Structure

```
my iot project/
├── README.md                        # This file
├── .gitignore                       # Ignores .env, __pycache__, config.json, etc.
│
├── esp32/                           # MicroPython firmware for ESP32
│   ├── main.py                      # Boot entry point + 3-thread orchestrator
│   ├── config.py                    # Pin assignments + timing constants
│   ├── config.json                  # Runtime config (WiFi + API URL) — NOT in git
│   ├── wifi.py                      # WiFi STA connect + config.json R/W
│   ├── wifi_manager.py              # Captive portal (AP mode setup)
│   ├── hardware.py                  # D2 WiFi status LED (non-blocking blink)
│   ├── api.py                       # HTTP client for backend communication
│   ├── sensors.py                   # Flame sensor + IR gate sensor reads
│   ├── leds.py                      # Room LED on/off control
│   ├── buzzer.py                    # Active buzzer control
│   └── radar.py                     # Servo sweep + HC-SR04 in background thread
│
├── backend/                         # Python FastAPI backend
│   ├── main.py                      # FastAPI app + startup/shutdown + watchdog
│   ├── requirements.txt             # motor, pymongo, fastapi, uvicorn, websockets, python-dotenv
│   ├── render.yaml                  # Render.com deployment config
│   ├── .env                         # NOT in git — contains MONGODB_URI
│   ├── .env.example                 # Template for .env
│   └── app/
│       ├── __init__.py
│       ├── state.py                 # Shared in-memory state (single source of truth)
│       ├── db.py                    # MongoDB Atlas connection (Motor async)
│       ├── ws_manager.py            # WebSocket broadcast manager
│       └── routes/
│           ├── __init__.py
│           ├── health.py            # GET /health
│           ├── sensor.py            # POST /sensor-data (ESP32 → backend → WS)
│           ├── commands.py          # POST /command + GET /command/pending
│           ├── ws.py                # WS /ws endpoint
│           ├── auth.py              # Login, verify, logout, setup
│           └── stats.py             # /stats/today + /stats/recent
│
├── frontend/                        # Static web dashboard
│   ├── index.html                   # Landing page (public, served at root URL)
│   ├── dashboard.html               # IoT control dashboard (requires login)
│   ├── stats.html                   # Analytics page (requires login)
│   ├── css/
│   │   ├── home.css                 # Landing page styles
│   │   ├── style.css                # Dashboard styles
│   │   └── stats.css                # Stats page styles
│   ├── js/
│   │   ├── config.js                # API_BASE + WS_URL (update when deploying)
│   │   ├── auth.js                  # Token storage + requireAuth() + redirect
│   │   ├── api.js                   # fetch() wrapper with auth headers
│   │   ├── ws.js                    # Persistent WebSocket + auto-reconnect
│   │   ├── radar.js                 # 60fps canvas, scanHistory, ping-pong, EMA
│   │   ├── leds.js                  # LED toggle buttons + optimistic UI
│   │   ├── sensors.js               # Flame/gate/protect-mode display
│   │   ├── main.js                  # Dashboard init + auth guard + layout
│   │   ├── home.js                  # Landing page animations + login form
│   │   └── stats.js                 # Stats fetch + chart rendering
│   └── assets/
│       ├── 01 esp32_wroom_32_-_low_poly_photorealistic.glb
│       ├── new_hc-sr04.glb
│       ├── servomotor_sg90.glb
│       ├── buzzer.glb
│       ├── breadboard.glb
│       ├── rechargeable_lithium_ion_battery_-_18650.glb
│       └── IR_sensor/
│           └── source/ir sensor.glb
│
└── docs/                            # Project documentation
    └── complete_build_info.md       # Detailed build log with phase history
```

---

## 14. Environment Variables Reference

### Backend (.env)

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `MONGODB_URI` | Yes (for stats) | MongoDB Atlas connection string | `mongodb+srv://user:pass@cluster.mongodb.net/` |
| `APP_ENV` | No | Environment name | `development` or `production` |

If `MONGODB_URI` is not set, the backend starts normally but all MongoDB operations are silently skipped. LED sessions, flame events, and gate events will not persist. The stats page will show empty data.

### ESP32 (config.json)

| Key | Description | Example |
|-----|-------------|---------|
| `wifi_ssid` | WiFi network name | `"MyHomeNetwork"` |
| `wifi_password` | WiFi password | `"MyPassword123"` |
| `api_base` | FastAPI backend URL | `"https://smart-home-backend.onrender.com"` |

Written by the captive portal (`wifi_manager.py`) and read by `wifi.py` and `api.py`.

### Frontend (js/config.js)

| Variable | Description | Example |
|----------|-------------|---------|
| `CONFIG.API_BASE` | Backend HTTP URL | `"https://smart-home-backend.onrender.com"` |
| `CONFIG.WS_URL` | Backend WebSocket URL | `"wss://smart-home-backend.onrender.com/ws"` |

Note: Use `wss://` (secure WebSocket) for HTTPS-served frontends and `ws://` for HTTP local development. Browsers block `ws://` connections from `https://` pages.

---

## Quick Reference: API Endpoints

| Method | Path | Who Calls It | Purpose |
|--------|------|-------------|---------|
| GET | `/health` | ESP32 (every 250s) | Keep-alive + pipeline verification |
| POST | `/sensor-data` | ESP32 (every 400ms) | Push radar sweep + sensor states |
| GET | `/sensor-data/latest` | Browser (fallback) | HTTP fallback for latest state |
| POST | `/command` | Browser dashboard | Queue a command for ESP32 |
| GET | `/command/pending` | ESP32 (every 300ms) | Fetch + clear pending commands |
| GET | `/command/queue` | Developers | Debug: inspect queue without consuming |
| WS | `/ws` | Browser | Real-time bidirectional updates |
| POST | `/auth/login` | Browser | Authenticate, get session token |
| GET | `/auth/verify` | Browser (each page load) | Validate session token |
| POST | `/auth/logout` | Browser | Invalidate session |
| POST | `/auth/setup` | One-time setup | Create first admin user |
| GET | `/stats/today` | Stats page | Today's LED + flame + gate data |
| GET | `/stats/recent` | Stats page | Last N days LED usage for charts |

---

## Quick Reference: WebSocket Message Types

| Type | Direction | When | Payload |
|------|-----------|------|---------|
| `init` | Server → Browser | On WS connect | Full state snapshot |
| `sensor_update` | Server → Browser | Every ESP32 POST (~400ms) | Radar sweep + all sensor states |
| `state_update` | Server → Browser | Every dashboard command | Updated LED + protect_mode states |
| `esp32_status` | Server → Browser | ESP32 online/offline edge | `{online: true/false}` |
| `ping` | Server → Browser | Every 20s (heartbeat) | (empty) |

---

*Built with 💚 by Shubhranshu using MicroPython, FastAPI, MongoDB,Vanilla JS. and with a great interest in AI and Robotics.*
*Documentation updated at latest : 2026-05-26 | By -Shubhranshu Sahu*
