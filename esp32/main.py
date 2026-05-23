# =============================================
# main.py  —  ESP32 orchestrator (Phase 4)
#
# Responsibilities:
#   1. WiFi connect + reconnect + portal fallback
#   2. D2 LED status blink
#   3. Periodic health ping (15s — keeps Render awake)
#   4. Periodic sensor POST (500ms — live radar data)
#   5. Periodic command poll (500ms)
#   6. Protect mode: non-blocking buzzer based on distance
#   7. Flame: direct buzzer (no network delay)
# =============================================

import time

from wifi         import connect_wifi, wifi_is_connected
from wifi_manager import start_portal
from hardware     import set_mode, update_led, MODE_CONNECTED, MODE_DISCONNECTED

import api
import leds
import buzzer
import sensors
import radar

from config import (
    API_HEALTH_INTERVAL_MS,
    SENSOR_POST_INTERVAL_MS,
    COMMAND_POLL_INTERVAL_MS
)

# =============================================
# PROTECT MODE STATE
# =============================================

_protect_mode = False   # Set by backend command

# Non-blocking buzzer state machine
_buzz_on_ms      = 50   # Duration of each beep tone (ms)
_buzz_off_ms     = -1   # Gap between beeps (-1 = silent)
_buzz_state      = False        # True = currently sounding
_buzz_changed_ms = 0            # Timestamp of last state change
_manual_beep_end = 0            # ticks_ms() when manual beep ends

# =============================================
# COMMAND HANDLER
# =============================================

def _handle_command(cmd):
    global _protect_mode, _manual_beep_end

    action = cmd.get("action", "")

    if action == "set_led":
        leds.set_room(cmd.get("room", 0), cmd.get("state", 0))
        print("[CMD] LED room", cmd.get("room"), "→", cmd.get("state"))

    elif action == "set_all":
        leds.set_all(cmd.get("state", 0))
        print("[CMD] All LEDs →", cmd.get("state"))

    elif action == "beep":
        # Schedule a non-blocking manual beep
        dur = cmd.get("duration_ms", 200)
        _manual_beep_end = time.ticks_add(time.ticks_ms(), dur)
        buzzer.on()
        print("[CMD] Beep", dur, "ms")

    elif action == "protect_mode":
        _protect_mode = cmd.get("state", False)
        if not _protect_mode:
            buzzer.off()
        print("[CMD] Protect mode →", _protect_mode)

    elif action == "all_off":
        leds.set_all(0)
        buzzer.off()

    else:
        print("[CMD] Unknown:", action)


# =============================================
# NON-BLOCKING BUZZER ENGINE
#
# Priority 1: Flame detected       → solid ON
# Priority 2: Manual beep command  → on until timer expires
# Priority 3: Protect mode + near  → periodic beep
# Priority 4: No threat            → off
# =============================================

def _update_buzzer(now_ms, distance):
    global _buzz_state, _buzz_changed_ms, _buzz_off_ms, _manual_beep_end

    # P1: Flame → always solid ON
    if sensors.read_flame():
        buzzer.on()
        _buzz_state = False  # reset timer state
        return

    # P2: Manual beep (from backend command)
    if time.ticks_diff(_manual_beep_end, now_ms) > 0:
        buzzer.on()
        return
    # Manual beep just ended — turn off (unless protect mode takes over below)

    # P3: Protect mode
    if _protect_mode and distance is not None:
        if   distance < 25:  _buzz_off_ms = 40
        elif distance < 50:  _buzz_off_ms = 180
        elif distance < 80:  _buzz_off_ms = 420
        elif distance < 110: _buzz_off_ms = 750
        else:                _buzz_off_ms = -1
    else:
        _buzz_off_ms = -1

    if _buzz_off_ms < 0:
        buzzer.off()
        _buzz_state = False
        return

    # Oscillate: on for _buzz_on_ms, off for _buzz_off_ms
    elapsed = time.ticks_diff(now_ms, _buzz_changed_ms)
    if _buzz_state:
        if elapsed >= _buzz_on_ms:
            buzzer.off()
            _buzz_state = False
            _buzz_changed_ms = now_ms
    else:
        if elapsed >= _buzz_off_ms:
            buzzer.on()
            _buzz_state = True
            _buzz_changed_ms = now_ms


# =============================================
# BOOT — WiFi connect
# =============================================

connected = connect_wifi()

if not connected:
    print("[MAIN] Initial connect failed — starting portal")
    start_portal()      # Blocks until user saves credentials + reboot

# Start radar sweep in background thread (independent of HTTP)
radar.start()

print("[MAIN] System Running — Phase 4")

# =============================================
# LOOP TIMERS
# =============================================

_fail_count   = 0
_MAX_FAILS    = 2

_last_health  = 0
_last_sensor  = 0
_last_command = 0

# =============================================
# MAIN LOOP
# =============================================

while True:

    now = time.ticks_ms()

    # Always: update WiFi status LED
    update_led()

    # ---- Buzzer engine (non-blocking, runs every iteration) ----
    _rd = radar.get_latest()
    _update_buzzer(now, _rd["distance"])

    # ==========================================
    # WiFi monitor — reconnect if dropped
    # ==========================================
    if not wifi_is_connected():
        _fail_count += 1
        set_mode(MODE_DISCONNECTED)
        print("[MAIN] WiFi lost — attempt", _fail_count, "of", _MAX_FAILS)

        if connect_wifi():
            print("[MAIN] Reconnected!")
            _fail_count = 0
        elif _fail_count >= _MAX_FAILS:
            print("[MAIN] Cannot reconnect — starting portal")
            start_portal()

        time.sleep_ms(50)
        continue           # Skip API calls until WiFi is back

    set_mode(MODE_CONNECTED)
    _fail_count = 0

    # ==========================================
    # PERIODIC — Health ping (keeps Render alive)
    # ==========================================
    if time.ticks_diff(now, _last_health) >= API_HEALTH_INTERVAL_MS:
        api.ping_health()
        _last_health = now

    # ==========================================
    # PERIODIC — Sensor data POST (500ms)
    # ==========================================
    if time.ticks_diff(now, _last_sensor) >= SENSOR_POST_INTERVAL_MS:
        payload = {
            "angle":    _rd["angle"],
            "distance": _rd["distance"],
            "flame":    sensors.read_flame(),
            "gate":     sensors.read_gate(),
            "leds":     leds.get_states()   # Sent for stats/verification
        }
        api.send_sensor_data(payload)
        _last_sensor = now

    # ==========================================
    # PERIODIC — Command poll (500ms)
    # ==========================================
    if time.ticks_diff(now, _last_command) >= COMMAND_POLL_INTERVAL_MS:
        result = api.get_pending_commands()
        for cmd in result.get("commands", []):
            _handle_command(cmd)
        _last_command = now

    # Tiny yield to prevent CPU thrash
    time.sleep_ms(20)