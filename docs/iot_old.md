# 🏠 Smart Home IoT Project — Complete College Guide
### ESP32 + FastAPI + WebSockets + Mobile Dashboard

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Complete Components List & Shopping Guide](#2-complete-components-list--shopping-guide)
3. [Resistors & Protection — Don't Fry Your Chip](#3-resistors--protection--dont-fry-your-chip)
4. [Power Supply — Battery vs USB](#4-power-supply--battery-vs-usb)
5. [Optional Sensors — IR & Heat (Fire Alert)](#5-optional-sensors--ir--heat-fire-alert)
6. [Testing Your ESP32 Before Full Assembly](#6-testing-your-esp32-before-full-assembly)
7. [Wiring & Connection Diagrams](#7-wiring--connection-diagrams)
8. [Software Architecture — How It All Talks](#8-software-architecture--how-it-all-talks)
9. [WebSockets vs Polling — What to Use & Why](#9-websockets-vs-polling--what-to-use--why)
10. [FastAPI Backend Structure](#10-fastapi-backend-structure)
11. [ESP32 Firmware Outline (MicroPython)](#11-esp32-firmware-outline-micropython)
12. [Mobile Dashboard — What to Show](#12-mobile-dashboard--what-to-show)
13. [Project Timeline Suggestion](#13-project-timeline-suggestion)
14. [Common Mistakes & Safety Checklist](#14-common-mistakes--safety-checklist)

---

## 1. Project Overview

```
┌─────────────────────────────────────────────────────┐
│                   SMART HOME IOT                     │
│                                                     │
│  [Room 1 LED] [Room 2 LED] [Room 3 LED] [Room 4 LED]│
│       ↕              ↕                              │
│            ESP32 Dev Board                          │
│       ↕              ↕                              │
│  [Radar: HC-SR04 + SG90 Servo] [Buzzer/Beeper]     │
│                    ↕                                │
│              WiFi (ESP32)                           │
│                    ↕                                │
│           FastAPI Server (Laptop)                   │
│                    ↕                                │
│        Mobile Browser Dashboard (Phone)             │
└─────────────────────────────────────────────────────┘
```

**What the system does:**

- 4 LEDs simulate room lights — controllable individually from phone
- Track each room's on-time and calculate estimated electricity cost
- Servo + Ultrasonic = rotating radar that sweeps and measures distance
- Alarm (buzzer) triggers if someone is closer than your threshold
- Live radar display on phone showing sweep angle and distance reading
- Optional: DHT11/MLX90614 for fire/heat alert, IR sensor for gate status

---

## 2. Complete Components List & Shopping Guide

### 🔴 CORE Components (Non-negotiable)

| # | Component | Qty | Approx Cost (India) | Notes |
|---|-----------|-----|---------------------|-------|
| 1 | **ESP32 Dev Board** (38-pin or 30-pin) | 1 | ₹350–450 | Buy from Robu.in, Electronicscomp, or Amazon |
| 2 | **LED (5mm, any color)** | 4 | ₹5–10 each | Red/Green/Blue/Yellow — 1 per room |
| 3 | **HC-SR04 Ultrasonic Sensor** | 1 | ₹35–50 | Distance measurement |
| 4 | **SG90 Micro Servo Motor** | 1 | ₹80–120 | For radar sweep |
| 5 | **Active Buzzer (5V)** | 1 | ₹15–25 | Beeps without needing PWM |
| 6 | **Half-size Breadboard (400 tie)** | 1 | ₹40–60 | You already have this ✓ |
| 7 | **Jumper Wires (M-M, M-F, F-F set)** | 1 set | ₹50–80 | Buy all 3 types |

### 🟡 SUPPORT Components (Essential)

| # | Component | Qty | Approx Cost | Notes |
|---|-----------|-----|-------------|-------|
| 8 | **Resistors 220Ω** | 6 | ₹1 each | For LEDs (buy pack of 20) |
| 9 | **Resistors 1kΩ** | 5 | ₹1 each | For HC-SR04 Echo pin divider |
| 10 | **Resistors 2kΩ** | 3 | ₹1 each | For voltage divider (or use 2× 1kΩ in series) |
| 11 | **100µF Capacitor (electrolytic)** | 2 | ₹5 each | Smooth power spikes from servo |
| 12 | **10µF Capacitor** | 2 | ₹3 each | Decoupling near ESP32 |
| 13 | **Micro USB Cable (data + power)** | 1 | ₹80–150 | Must be DATA cable, not charge-only! |
| 14 | **USB-A Male to USB-A Female extension** | 1 | optional | Easier to plug/unplug during dev |

### 🟢 POWER Components (If you want battery operation)

| # | Component | Qty | Approx Cost | Notes |
|---|-----------|-----|-------------|-------|
| 15 | **3.7V Li-Po / 18650 battery** | 1 | ₹150–300 | 2000mAh is fine |
| 16 | **TP4056 Charging Module** | 1 | ₹20–35 | Charges Li-Po safely via USB |
| 17 | **MT3608 Boost Converter (3.7V→5V)** | 1 | ₹30–50 | Steps battery up to 5V for ESP32 |
| 18 | **SPDT Slide Switch** | 1 | ₹10 | On/off for battery circuit |

> **⚠️ Honest Advice:** For a college demo, just run everything from laptop USB. The ESP32 runs fine from USB 5V. Only add battery if you want wireless mobility. Start without it, add later if needed.

### 🔵 CONVENIENCE / TOOLS

| # | Component | Qty | Notes |
|---|-----------|-----|-------|
| 19 | Solder wire (60/40, rosin core) | 1 roll | You have iron ✓ |
| 20 | Flux paste | 1 small jar | Helps solder flow cleanly |
| 21 | Heat shrink tubes (assorted) | 1 pack | Insulate soldered joints |
| 22 | Male pin headers (2.54mm pitch) | 2 strips | In case ESP32 comes without pins |
| 23 | Female pin headers | 1 strip | For making daughter boards on breadboard |
| 24 | Multimeter (basic) | 1 | ₹200–400 — absolutely must have |
| 25 | Small screwdriver set | 1 | For screw terminals |
| 26 | Tape / Blue tack | — | To stick breadboard/sensor in place for demo |

---

## 3. Resistors & Protection — Don't Fry Your Chip

### ESP32 Pin Limits (Very Important)

```
ESP32 GPIO can supply/sink: MAX 40mA per pin
Safe operating current: 12mA per pin (stay under this!)
Total GPIO current: MAX 1200mA total
Operating voltage: 3.3V logic (NOT 5V tolerant on most pins!)
```

> **Critical:** HC-SR04 runs at 5V and its Echo pin outputs 5V — this WILL damage ESP32 if connected directly. Always use a voltage divider.

---

### LED Current Limiting Resistors

Each LED needs a resistor in series to limit current.

**Formula:**
```
R = (Vcc - Vled) / I_led

For 3.3V GPIO output:
  Red LED   → Vled ≈ 1.8V → R = (3.3 - 1.8) / 0.010 = 150Ω → Use 220Ω (safe side)
  Green LED → Vled ≈ 2.1V → R = (3.3 - 2.1) / 0.010 = 120Ω → Use 220Ω
  Blue LED  → Vled ≈ 3.0V → R = (3.3 - 3.0) / 0.010 = 30Ω  → Use 100Ω (220Ω is fine too)
  Yellow    → like Red → Use 220Ω
```

**Safe pick for all 4 LEDs: Use 220Ω resistors.** They limit current to ~6.8mA, well within limits, and the LED will still be clearly visible.

```
GPIO Pin → [220Ω Resistor] → LED Anode (+, longer leg) → LED Cathode (-, shorter leg) → GND
```

---

### HC-SR04 Voltage Divider (Echo Pin)

HC-SR04 Trigger = 5V input → ESP32 can drive this from 3.3V GPIO (5V devices usually accept 3.3V trigger)
HC-SR04 Echo = outputs 5V → **MUST be divided down to 3.3V before connecting to ESP32**

```
HC-SR04 Echo Pin
      |
    [1kΩ]
      |——————→ To ESP32 GPIO (Echo Input)
    [2kΩ]
      |
     GND

Voltage at ESP32 = 5V × (2k / (1k + 2k)) = 5 × 0.667 = 3.33V ✓ Safe!
```

You can also use two 1kΩ resistors in series as your 2kΩ (since you'll buy a pack anyway).

---

### SG90 Servo Power

**Never power SG90 directly from ESP32 GPIO pin.** The servo can draw 250–500mA when moving — that will crash the ESP32.

```
Servo Red (VCC)  → 5V rail (VUSB from ESP32's 5V pin, or separate 5V)
Servo Brown/Black (GND) → GND
Servo Orange (Signal) → Any ESP32 GPIO (3.3V signal is fine for SG90)
```

Add a 100µF capacitor between 5V and GND near the servo to absorb current spikes.

---

### Active Buzzer

```
Buzzer + → ESP32 GPIO (through 100Ω resistor, or direct — most active buzzers work fine direct)
Buzzer - → GND
```

If buzzer is loud and you want to control volume: add 100–470Ω in series.

---

## 4. Power Supply — Battery vs USB

### Option A: USB Only (Recommended for Demo)

```
Laptop USB → Micro USB cable → ESP32 Dev Board
                                     |
                         3.3V regulated (internal regulator)
                                     |
                              → All GPIO signals
                         5V (VUSB pin on ESP32)
                              → Servo VCC
                              → HC-SR04 VCC
                              → Buzzer
```

**Laptop USB provides 500mA–900mA. That's plenty.**
ESP32 draws ~80–240mA. Servo draws ~250mA peak. You're fine.

### Option B: Battery Pack (For Wireless Demo)

```
Li-Po 3.7V → TP4056 (charging) → Battery positive terminal
                                        |
                                   MT3608 Boost → 5V output
                                        |
                              ESP32 5V Pin (or Vin)
```

**TP4056 Warning:** Use the TP4056 with protection circuit (has 4 chips on board, not 1). Look for "TP4056 with protection" — they have overcurrent/overdischarge protection built in.

**DO NOT charge the battery while it's also powering the circuit through the boost converter.** Use the slide switch to disconnect the battery from the boost converter when charging.

---

## 5. Optional Sensors — IR & Heat (Fire Alert)

### 🔥 Heat / Fire Alert Options

#### Option 1: DHT11 Temperature Sensor (~₹50)
- Measures temperature + humidity
- Set threshold (e.g., >50°C = fire alert)
- Simple 1-wire protocol, easy to code
- Not a "real" fire sensor but works for demo purposes

#### Option 2: MLX90614 IR Temperature Sensor (~₹250–400)
- Non-contact temperature measurement (IR thermometer)
- I2C protocol
- More impressive — can detect heat from a distance
- Great for demo: "If object temperature > 80°C, fire alert!"

#### Option 3: KY-026 / MQ-2 Flame / Smoke Sensor (~₹50–150)
- KY-026: actual flame sensor (detects IR from flame)
- MQ-2: detects smoke/gas
- Most "IoT" looking for a demo — evaluators will be impressed

**Recommendation: Buy KY-026 Flame Sensor (cheap, dramatic demo — just light a lighter near it)**

---

### 🚪 IR Sensor Ideas for Gate / Entry

#### Option 1: IR Obstacle/Proximity Sensor (FC-51) (~₹30)
**Gate Open/Close Detection:**
- Mount at gate frame — when gate opens, IR beam breaks → "Gate Open"
- Very simple, impressive demo

**Ideas you could show evaluators:**
- "When gate opens, send notification to dashboard"
- "Log entry/exit timestamps"
- "If gate open for > 5 minutes, send alert"

#### Option 2: IR Beam Break Sensor (Transmitter + Receiver) (~₹50)
- Transmitter on one side, receiver on other side of doorway
- When beam breaks = something passed through
- Can count entries: "3 people have entered today"

#### Option 3: TCRT5000 IR Reflective Sensor (~₹20)
- Detects reflective surface very close (2–15mm)
- Could be used to detect: cabinet door open/closed, drawer state

**Best pick for impressiveness with low cost: FC-51 IR sensor as a gate sensor + KY-026 as flame sensor.** Total addition: ~₹80, doubles your feature set.

---

## 6. Testing Your ESP32 Before Full Assembly

### What to Install on Your Laptop (Windows)

**Step 1: Install Required Software**

```
1. Python 3.10+ from python.org (check "Add to PATH")
2. VS Code from code.visualstudio.com
3. VS Code Extension: "ESP-IDF" OR use Thonny (simpler for beginners)
4. Thonny IDE: thonny.org  ← RECOMMENDED for beginners using MicroPython
```

**Step 2: Install CH340/CP2102 Driver (for ESP32 USB)**

Your ESP32 dev board has a USB-to-serial chip. Most are CH340G.

```
1. Go to: wch.cn/en/downloads → CH341SER.EXE
2. Install it
3. Plug ESP32 → Open Device Manager → Look for "USB-SERIAL CH340 (COM X)"
4. Note that COM number — you'll need it
```

If the chip is CP2102 instead: download from Silicon Labs website (search "CP210x USB to UART Bridge VCP Drivers").

**Step 3: Flash MicroPython onto ESP32**

```bash
# In terminal (with Python installed):
pip install esptool

# Erase existing firmware:
esptool.py --port COM3 erase_flash
# (replace COM3 with your actual COM port)

# Download MicroPython .bin from: micropython.org/download/esp32/
# Then flash it:
esptool.py --chip esp32 --port COM3 --baud 460800 write_flash -z 0x1000 esp32-20240602-v1.23.0.bin
```

**Step 4: Test with Thonny**

```
1. Open Thonny
2. Go to Tools → Options → Interpreter
3. Select "MicroPython (ESP32)"
4. Select your COM port
5. Click OK — bottom panel should show "MicroPython v1.xx"
```

**Step 5: Quick Blink Test (Paste in Thonny REPL)**

```python
from machine import Pin
import time

led = Pin(2, Pin.OUT)  # GPIO2 is onboard LED on most ESP32 boards

while True:
    led.value(1)
    time.sleep(0.5)
    led.value(0)
    time.sleep(0.5)
```

If the blue LED on the ESP32 board blinks → Your ESP32 is working perfectly!

**Step 6: WiFi Test**

```python
import network
import time

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect("YOUR_WIFI_NAME", "YOUR_WIFI_PASSWORD")

timeout = 10
while not wlan.isconnected() and timeout > 0:
    print("Connecting...")
    time.sleep(1)
    timeout -= 1

if wlan.isconnected():
    print("Connected! IP:", wlan.ifconfig()[0])
else:
    print("Failed to connect")
```

If you see an IP address → WiFi works!

---

**Quick Buy Checklist Before Testing:**

- [ ] Multimeter — test voltage between 3.3V pin and GND (should read ~3.28–3.35V)
- [ ] Test continuity on breadboard rails before connecting anything
- [ ] Use a known-good Micro USB DATA cable (many phone charger cables are charge-only!)
- [ ] Never plug/unplug components while ESP32 is powered

---

## 7. Wiring & Connection Diagrams

### ESP32 Pin Assignment

```
ESP32 GPIO → Component
─────────────────────────────────────────────
GPIO 2  → Built-in LED (test only)
GPIO 16 → Room 1 LED (via 220Ω resistor)
GPIO 17 → Room 2 LED (via 220Ω resistor)
GPIO 18 → Room 3 LED (via 220Ω resistor)
GPIO 19 → Room 4 LED (via 220Ω resistor)
GPIO 26 → HC-SR04 Trigger (direct, 3.3V is ok)
GPIO 27 → HC-SR04 Echo (via voltage divider 1kΩ/2kΩ)
GPIO 25 → SG90 Servo Signal (direct)
GPIO 23 → Active Buzzer (direct or via 100Ω)
GPIO 34 → KY-026 Flame Sensor Digital Out (optional)
GPIO 35 → FC-51 IR Sensor Out (optional)
GPIO 21 → SDA for MLX90614/DHT11 (optional)
GPIO 22 → SCL for MLX90614 (optional)

3.3V Pin → (logic signals only, never heavy loads)
5V Pin   → HC-SR04 VCC, Servo VCC, Buzzer VCC
GND      → All component GNDs (common ground)
```

---

### Full Breadboard Wiring ASCII Diagram

```
                    ┌──────────────────┐
                    │   ESP32 DEV BOARD │
                    │                  │
3V3 ────────────────┤ 3V3          GND ├──────── GND Rail (─)
5V  ────────────────┤ 5V           D23 ├──── [100Ω] ──── BUZZER(+)
                    │              D25 ├──────────────── SERVO Signal (Orange)
                    │              D26 ├──────────────── HC-SR04 TRIG
                    │              D27 ├──── [1kΩ] ─┬── HC-SR04 ECHO
                    │                  │            └─[2kΩ]─ GND
                    │              D16 ├──── [220Ω] ─── LED1(+) → LED1(-) → GND
                    │              D17 ├──── [220Ω] ─── LED2(+) → LED2(-) → GND
                    │              D18 ├──── [220Ω] ─── LED3(+) → LED3(-) → GND
                    │              D19 ├──── [220Ω] ─── LED4(+) → LED4(-) → GND
                    │              D34 ├──────────────── KY-026 D0 (optional)
                    │              D35 ├──────────────── FC-51 OUT (optional)
                    └──────────────────┘

HC-SR04:
  VCC → 5V Rail
  GND → GND Rail
  TRIG → GPIO26 (direct)
  ECHO → Voltage divider → GPIO27

SG90 Servo:
  Red    → 5V Rail (+100µF cap to GND near it)
  Brown  → GND Rail
  Orange → GPIO25

Active Buzzer:
  (+) → GPIO23 via 100Ω
  (-) → GND Rail

LEDs (each identical):
  GPIO → 220Ω → LED Anode(+) → LED Cathode(-) → GND
```

---

### Radar Assembly (Physical)

```
Mount HC-SR04 on top of SG90:
  1. Tape or hot-glue HC-SR04 flat onto the servo horn
  2. The servo rotates 0° to 180° sweeping the sensor
  3. At each angle (every 5°), take distance reading
  4. Send (angle, distance) pair to server

Physical placement:
  ┌──────────────┐
  │   HC-SR04    │  ← Ultrasonic sensor (mounted on servo horn)
  │  [O]    [O]  │
  └──────┬───────┘
         │ (servo horn)
      ┌──┴──┐
      │SG90 │  ← Servo (fixed to base/box)
      └─────┘
```

---

## 8. Software Architecture — How It All Talks

```
┌─────────────────────────────────────────────────────────────┐
│  PHONE BROWSER  (HTML/CSS/JS Dashboard)                     │
│  - Room light toggles + stats                               │
│  - Radar canvas visualization                               │
│  - Alert notification panel                                 │
└────────────────────┬────────────────────────────────────────┘
                     │  WebSocket (ws://laptop-ip:8000/ws)
                     │  HTTP REST (http://laptop-ip:8000/...)
                     ↕
┌─────────────────────────────────────────────────────────────┐
│  FASTAPI SERVER  (Running on Laptop)                        │
│  - WebSocket manager (broadcasts to all clients)            │
│  - REST endpoints for commands                              │
│  - State store (dict in memory for demo)                    │
│  - Relays commands to ESP32                                 │
└────────────────────┬────────────────────────────────────────┘
                     │  HTTP (polling every 100ms, or ESP32 pushes)
                     ↕
┌─────────────────────────────────────────────────────────────┐
│  ESP32  (MicroPython firmware)                              │
│  - Controls GPIO: LEDs, Servo, Buzzer                       │
│  - Reads sensors: HC-SR04, optional sensors                 │
│  - Sends sensor data to FastAPI                             │
│  - Listens for commands from FastAPI                        │
└─────────────────────────────────────────────────────────────┘
```

### Communication Protocol

**ESP32 → FastAPI (push sensor data):**
```
POST http://laptop-ip:8000/sensor-data
Body: { "angle": 45, "distance": 120, "alarm": false, "temp": 28.5 }
```

**FastAPI → Phone (WebSocket broadcast):**
```json
{ "type": "radar", "angle": 45, "distance": 120 }
{ "type": "alarm", "distance": 35, "message": "Intruder detected!" }
{ "type": "room_update", "room": 1, "state": true }
```

**Phone → FastAPI (REST command):**
```
POST /command
Body: { "action": "toggle_light", "room": 1, "state": true }
POST /command
Body: { "action": "toggle_radar", "state": true }
```

**FastAPI → ESP32 (pending commands queue):**
```
GET http://esp32-ip/command  ← ESP32 polls this every 200ms
Response: { "command": "set_led", "pin": 16, "state": 1 }
```

---

## 9. WebSockets vs Polling — What to Use & Why

### The Plan (Simple & Works Great for Demo)

| Direction | Method | Why |
|-----------|--------|-----|
| Phone → FastAPI | HTTP REST POST | Simple, reliable, fire-and-forget |
| FastAPI → Phone | **WebSocket** | Live radar sweep needs real-time push |
| ESP32 → FastAPI | HTTP POST | ESP32 pushes data, simple |
| FastAPI → ESP32 | HTTP GET polling (ESP32 polls) | Simpler than running server on ESP32 |

**Why not MQTT?** MQTT needs a broker (Mosquitto server), more setup, more concepts to explain. For a college project, FastAPI + WebSocket is cleaner, more understandable, and impressive enough.

**Why WebSocket for phone?**
The radar sweeps continuously (0° to 180°). At 5° steps, that's 36 data points per sweep, multiple sweeps per second. Polling would add latency and look choppy. WebSocket gives you a smooth live radar.

**Why not WebSocket for ESP32?**
MicroPython's WebSocket support is limited and fragile. HTTP is simple, reliable, and easy to debug. Have the ESP32 POST its data every 100ms — that's effectively real-time.

---

## 10. FastAPI Backend Structure

### Folder Structure

```
smart_home/
├── main.py              ← FastAPI app
├── state.py             ← Shared state (rooms, radar, alerts)
├── models.py            ← Pydantic models
├── routers/
│   ├── commands.py      ← REST endpoints for phone commands
│   ├── sensor.py        ← Endpoint that ESP32 posts to
│   └── websocket.py     ← WebSocket manager + endpoint
└── static/
    └── index.html       ← Dashboard (served from FastAPI itself)
```

### main.py

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from routers import commands, sensor, websocket

app = FastAPI()

app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

app.include_router(commands.router)
app.include_router(sensor.router)
app.include_router(websocket.router)

app.mount("/", StaticFiles(directory="static", html=True), name="static")
```

### state.py

```python
from datetime import datetime

state = {
    "rooms": {
        1: {"on": False, "total_seconds": 0, "last_on": None},
        2: {"on": False, "total_seconds": 0, "last_on": None},
        3: {"on": False, "total_seconds": 0, "last_on": None},
        4: {"on": False, "total_seconds": 0, "last_on": None},
    },
    "radar": {
        "active": False,
        "last_angle": 0,
        "last_distance": 0,
        "alarm_threshold_cm": 50,
        "alarm_active": False,
    },
    "pending_command": None,   # ESP32 picks this up
    "alerts": [],
}

WATTS_PER_LED = 0.3          # LED draws ~0.3W (symbolic, for demo)
COST_PER_KWH = 8.0           # ₹8 per kWh (India average)

def get_room_cost(room_id):
    room = state["rooms"][room_id]
    hours = room["total_seconds"] / 3600
    kwh = (WATTS_PER_LED / 1000) * hours
    return round(kwh * COST_PER_KWH, 4)
```

### routers/commands.py

```python
from fastapi import APIRouter
from pydantic import BaseModel
from state import state
from datetime import datetime

router = APIRouter(prefix="/command")

class Command(BaseModel):
    action: str
    room: int = None
    state_val: bool = None

@router.post("")
async def handle_command(cmd: Command):
    if cmd.action == "toggle_light":
        room = state["rooms"][cmd.room]
        if cmd.state_val and not room["on"]:
            room["last_on"] = datetime.now()
        elif not cmd.state_val and room["on"]:
            elapsed = (datetime.now() - room["last_on"]).total_seconds()
            room["total_seconds"] += elapsed
        room["on"] = cmd.state_val
        # Queue command for ESP32
        state["pending_command"] = {
            "action": "set_led",
            "room": cmd.room,
            "state": int(cmd.state_val)
        }
    elif cmd.action == "toggle_radar":
        state["radar"]["active"] = cmd.state_val
        state["pending_command"] = {
            "action": "set_radar",
            "state": int(cmd.state_val)
        }
    return {"ok": True}

@router.get("/pending")
async def get_pending():
    cmd = state["pending_command"]
    state["pending_command"] = None   # Clear after reading
    return cmd or {}
```

### routers/sensor.py

```python
from fastapi import APIRouter
from pydantic import BaseModel
from state import state
from routers.websocket import manager

router = APIRouter(prefix="/sensor")

class SensorData(BaseModel):
    angle: float
    distance: float
    temp: float = None
    flame: bool = False
    gate_open: bool = False

@router.post("")
async def receive_sensor(data: SensorData):
    state["radar"]["last_angle"] = data.angle
    state["radar"]["last_distance"] = data.distance

    alarm = data.distance < state["radar"]["alarm_threshold_cm"]
    state["radar"]["alarm_active"] = alarm

    # Broadcast to all connected phones
    msg = {
        "type": "radar",
        "angle": data.angle,
        "distance": data.distance,
        "alarm": alarm
    }
    await manager.broadcast(msg)

    if alarm:
        alert = {
            "type": "alarm",
            "distance": data.distance,
            "message": f"⚠️ Object detected at {data.distance:.1f} cm!"
        }
        state["alerts"].insert(0, alert)
        state["alerts"] = state["alerts"][:20]  # Keep last 20
        await manager.broadcast(alert)

    if data.flame:
        await manager.broadcast({"type": "fire_alert", "message": "🔥 FIRE DETECTED!"})

    if data.gate_open is not None:
        await manager.broadcast({"type": "gate", "open": data.gate_open})

    return {"ok": True}
```

### routers/websocket.py

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        self.active.remove(ws)

    async def broadcast(self, data: dict):
        msg = json.dumps(data)
        for ws in self.active[:]:
            try:
                await ws.send_text(msg)
            except:
                self.active.remove(ws)

manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()  # Keep alive, ignore incoming for now
    except WebSocketDisconnect:
        manager.disconnect(ws)
```

### Running the Server

```bash
pip install fastapi uvicorn

cd smart_home
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Open on phone:** `http://YOUR_LAPTOP_IP:8000` (phone must be on same WiFi)

Find laptop IP: `ipconfig` on Windows → look for IPv4 under WiFi adapter

---

## 11. ESP32 Firmware Outline (MicroPython)

```python
# main.py on ESP32
import network, urequests, machine, time
from machine import Pin, PWM

# ─── CONFIG ──────────────────────────────────────────────
SSID = "YourWiFi"
PASSWORD = "YourPassword"
SERVER = "http://192.168.1.100:8000"   # Your laptop IP
COMMAND_POLL_MS = 200
SENSOR_PUSH_MS = 100

# ─── PIN SETUP ───────────────────────────────────────────
LED_PINS = {1: Pin(16, Pin.OUT), 2: Pin(17, Pin.OUT),
            3: Pin(18, Pin.OUT), 4: Pin(19, Pin.OUT)}

trig = Pin(26, Pin.OUT)
echo = Pin(27, Pin.IN)
buzzer = Pin(23, Pin.OUT)
servo_pwm = PWM(Pin(25), freq=50)

ROOM_TO_PIN = {1: 16, 2: 17, 3: 18, 4: 19}

# ─── SERVO HELPER ────────────────────────────────────────
def set_servo_angle(angle):
    # SG90: 0° = ~1ms pulse, 180° = ~2ms pulse, at 50Hz (20ms period)
    duty = int((angle / 180) * 77 + 26)  # approx duty cycle
    servo_pwm.duty(duty)

# ─── ULTRASONIC DISTANCE ─────────────────────────────────
def get_distance_cm():
    trig.value(0); time.sleep_us(2)
    trig.value(1); time.sleep_us(10)
    trig.value(0)
    timeout = time.ticks_us()
    while echo.value() == 0:
        if time.ticks_diff(time.ticks_us(), timeout) > 30000:
            return -1
    start = time.ticks_us()
    while echo.value() == 1:
        if time.ticks_diff(time.ticks_us(), start) > 30000:
            return -1
    end = time.ticks_us()
    duration = time.ticks_diff(end, start)
    return (duration * 0.0343) / 2

# ─── WiFi CONNECT ─────────────────────────────────────────
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    for _ in range(20):
        if wlan.isconnected():
            print("IP:", wlan.ifconfig()[0])
            return True
        time.sleep(0.5)
    return False

# ─── MAIN LOOP ───────────────────────────────────────────
radar_active = False
current_angle = 0
angle_step = 5
direction = 1   # 1 = increasing, -1 = decreasing

def main():
    global radar_active, current_angle, direction
    if not connect_wifi():
        print("WiFi failed"); return

    last_cmd_time = 0
    last_push_time = 0

    while True:
        now = time.ticks_ms()

        # ── Poll for commands from server ──
        if time.ticks_diff(now, last_cmd_time) >= COMMAND_POLL_MS:
            try:
                r = urequests.get(SERVER + "/command/pending", timeout=2)
                cmd = r.json()
                r.close()
                if cmd.get("action") == "set_led":
                    LED_PINS[cmd["room"]].value(cmd["state"])
                elif cmd.get("action") == "set_radar":
                    radar_active = bool(cmd["state"])
            except:
                pass
            last_cmd_time = now

        # ── Radar sweep & push data ──
        if time.ticks_diff(now, last_push_time) >= SENSOR_PUSH_MS:
            dist = -1
            if radar_active:
                set_servo_angle(current_angle)
                time.sleep_ms(30)  # Let servo settle
                dist = get_distance_cm()

                # Alarm if too close
                if 0 < dist < 50:
                    buzzer.value(1)
                else:
                    buzzer.value(0)

                # Step angle
                current_angle += angle_step * direction
                if current_angle >= 180:
                    direction = -1
                elif current_angle <= 0:
                    direction = 1
            else:
                buzzer.value(0)

            # Push to server
            try:
                payload = '{"angle":%.1f,"distance":%.1f}' % (current_angle, dist if dist > 0 else 0)
                r = urequests.post(SERVER + "/sensor", data=payload,
                                   headers={"Content-Type": "application/json"}, timeout=2)
                r.close()
            except:
                pass
            last_push_time = time.ticks_ms()

main()
```

---

## 12. Mobile Dashboard — What to Show

The dashboard is a single `index.html` served by FastAPI. Open on phone browser — no app needed.

### Dashboard Sections

**1. Room Controls Panel**
```
┌─────────────────────────┐
│ 💡 Room 1    [ON ] [OFF]│  ← Toggle buttons
│    On: 2h 34m           │
│    Cost: ₹0.006         │
├─────────────────────────┤
│ 💡 Room 2    [ON ] [OFF]│
│    On: 0h 15m           │
│    Cost: ₹0.0006        │
└─────────────────────────┘
```

**2. Radar Display (Canvas)**
```
Canvas draws:
- Semicircle (radar sweep area)
- Rotating line at current angle
- Dot at distance point (scaled to canvas size)
- Color: green if safe, red if alarm
```

**3. Alert Feed**
```
🚨 2:34 PM — Object at 32 cm!
🔥 2:30 PM — FIRE DETECTED!
🚪 2:15 PM — Gate opened
```

**Key JavaScript for WebSocket:**
```javascript
const ws = new WebSocket(`ws://${location.hostname}:8000/ws`);
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === "radar") updateRadar(data.angle, data.distance);
    if (data.type === "alarm") showAlert(data.message);
    if (data.type === "fire_alert") showFireAlert();
};

function toggleLight(room, state) {
    fetch('/command', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({action: 'toggle_light', room, state_val: state})
    });
}
```

---

## 13. Project Timeline Suggestion

| Week | Task |
|------|------|
| Week 1 | Buy components, test ESP32 (blink + WiFi) |
| Week 2 | Wire LEDs + breadboard, test GPIO control from Python script |
| Week 3 | Wire HC-SR04 + servo, test radar sweep, print angle+distance to terminal |
| Week 4 | Set up FastAPI, test REST from Postman, ESP32 posts data |
| Week 5 | Build basic HTML dashboard, WebSocket working, radar canvas |
| Week 6 | Add room stats (time, cost), alert system, polish UI |
| Week 7 | Add optional sensors (flame/IR), final testing |
| Week 8 | Documentation, demo rehearsal |

---

## 14. Common Mistakes & Safety Checklist

### ❌ Never Do This

- **Never connect HC-SR04 Echo directly to ESP32 GPIO** — the 5V will damage the pin
- **Never power servo from ESP32 3.3V or GPIO** — it will crash or damage the board
- **Never use a charge-only USB cable** — ESP32 won't show up on laptop
- **Never connect anything while ESP32 is powered** unless you're sure of what you're doing
- **Never reverse polarity on capacitors** — electrolytic caps have +/- polarity marked
- **Never short 5V and GND** on breadboard — it will crash USB power

### ✅ Always Do This

- **Use common GND** — all components (ESP32, servo, sensor, buzzer) must share the same GND
- **Double-check before powering** — use multimeter to verify no shorts
- **Test one component at a time** — LEDs first, then servo, then sensor
- **Power off before rewiring** — unplug USB before changing connections
- **Add capacitors near servo** — 100µF between 5V and GND absorbs current spikes that would reset ESP32
- **Use 220Ω for LEDs** — even if calculated value is lower, 220Ω is universally safe

### Quick Multimeter Checks Before First Power-On

```
1. Resistance between 5V rail and GND → should be high (>1kΩ), not 0 (short!)
2. Resistance between 3.3V and GND → same, high
3. After powering: Voltage at 3.3V pin → should read 3.28–3.35V
4. Voltage at 5V pin → should read 4.8–5.1V
```

---

## Quick Reference: Component→Pin→Resistor Summary

| Component | ESP32 Pin | Resistor Needed | Notes |
|-----------|-----------|-----------------|-------|
| LED Room 1 | GPIO 16 | 220Ω in series | From GPIO to LED+ |
| LED Room 2 | GPIO 17 | 220Ω in series | |
| LED Room 3 | GPIO 18 | 220Ω in series | |
| LED Room 4 | GPIO 19 | 220Ω in series | |
| HC-SR04 Trig | GPIO 26 | None | Direct connection ok |
| HC-SR04 Echo | GPIO 27 | 1kΩ + 2kΩ divider | **Mandatory** |
| HC-SR04 VCC | 5V Pin | None | Not 3.3V! |
| SG90 Signal | GPIO 25 | None | 3.3V signal is fine |
| SG90 VCC | 5V Pin | 100µF cap to GND | Decoupling cap! |
| Buzzer (+) | GPIO 23 | 100Ω (optional) | Active buzzer |
| KY-026 D0 | GPIO 34 | None | Input only pin |
| FC-51 OUT | GPIO 35 | None | Input only pin |

---

*Built with: ESP32 + MicroPython + FastAPI + WebSockets + Vanilla JS*
*Total estimated cost (core project): ₹700–1000*
*Total with optionals + battery: ₹1200–1600*