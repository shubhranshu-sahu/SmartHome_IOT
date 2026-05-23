# =============================================
# main.py  —  ESP32 orchestrator (Phase 4)
#
# ARCHITECTURE (3 independent threads):
#
#   Thread 1 (radar.py)   — servo sweep + distance measurement
#                           Updates radar buffer continuously
#
#   Thread 2 (_cmd_thread) — command poll every 300ms
#                            Completely independent of sensor POST timing
#                            Executes LED/buzzer/protect-mode commands
#
#   Main loop              — sensor POST every 800ms (carries radar buffer)
#                            Health ping every 250s (keeps Render alive)
#                            Buzzer state machine (non-blocking)
#                            WiFi reconnect watchdog
#
# With this split, a slow sensor POST (1-3s on slow WiFi) NEVER
# delays command execution. Commands always arrive within 300ms + HTTP time.
# =============================================

import time
import _thread

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
# PROTECT MODE + BUZZER STATE
# =============================================

_protect_mode    = False
_buzz_on_ms      = 50
_buzz_off_ms     = -1
_buzz_state      = False
_buzz_changed_ms = 0
_manual_beep_end = 0

# =============================================
# COMMAND HANDLER  (called from _cmd_thread)
# =============================================

def _handle_command(cmd):
    global _protect_mode, _manual_beep_end

    action = cmd.get("action", "")

    if action == "set_led":
        leds.set_room(cmd.get("room", 0), cmd.get("state", 0))
        print("[CMD] LED room", cmd.get("room"), "=", cmd.get("state"))

    elif action == "set_all":
        leds.set_all(cmd.get("state", 0))
        print("[CMD] All LEDs =", cmd.get("state"))

    elif action == "beep":
        dur = cmd.get("duration_ms", 200)
        _manual_beep_end = time.ticks_add(time.ticks_ms(), dur)
        buzzer.on()
        print("[CMD] Beep", dur, "ms")

    elif action == "protect_mode":
        _protect_mode = cmd.get("state", False)
        if not _protect_mode:
            buzzer.off()
        print("[CMD] Protect mode =", _protect_mode)

    elif action == "all_off":
        leds.set_all(0)
        buzzer.off()

    else:
        print("[CMD] Unknown:", action)


# =============================================
# COMMAND POLL THREAD
#
# Runs completely independently of the main loop.
# A slow sensor POST never delays command execution.
# Max command latency = COMMAND_POLL_INTERVAL_MS + HTTP time
# =============================================

def _cmd_thread():
    """Background thread: polls /command/pending every 300ms."""
    print("[CMD] Command poll thread started")
    while True:
        try:
            result = api.get_pending_commands()
            for cmd in result.get("commands", []):
                _handle_command(cmd)
        except Exception as e:
            print("[CMD] Thread error:", e)
        time.sleep_ms(COMMAND_POLL_INTERVAL_MS)


# =============================================
# NON-BLOCKING BUZZER ENGINE  (called from main loop)
#   P1: Flame detected       → solid ON
#   P2: Manual beep          → on until timer expires
#   P3: Protect mode + close → variable-rate beep
#   P4: No threat            → off
# =============================================

def _update_buzzer(now_ms, distance):
    global _buzz_state, _buzz_changed_ms, _buzz_off_ms, _manual_beep_end

    if sensors.read_flame():
        buzzer.on()
        _buzz_state = False
        return

    if time.ticks_diff(_manual_beep_end, now_ms) > 0:
        buzzer.on()
        return

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
# BOOT
# =============================================

connected = connect_wifi()
if not connected:
    print("[MAIN] Initial connect failed — starting portal")
    start_portal()

# Start radar sweep thread (independent servo + distance)
radar.start()

# Start command poll thread (independent from sensor POST)
_thread.start_new_thread(_cmd_thread, ())

print("[MAIN] System Running — Phase 4 (3-thread architecture)")

# =============================================
# MAIN LOOP — Sensor POST + Health + Buzzer
#
# This loop no longer polls commands.
# It only POSTs sensor data (with radar buffer)
# and handles the buzzer state machine.
# =============================================

_fail_count  = 0
_MAX_FAILS   = 3

_last_health = 0
_last_sensor = 0

while True:

    now = time.ticks_ms()

    # Fast work — always runs every iteration
    update_led()
    _rd = radar.get_latest()
    _update_buzzer(now, _rd["distance"])

    # ---- WiFi watchdog ----
    if not wifi_is_connected():
        _fail_count += 1
        set_mode(MODE_DISCONNECTED)
        print("[MAIN] WiFi lost — attempt", _fail_count)
        if connect_wifi():
            print("[MAIN] Reconnected!")
            _fail_count = 0
        elif _fail_count >= _MAX_FAILS:
            print("[MAIN] Starting portal")
            start_portal()
        time.sleep_ms(100)
        continue

    set_mode(MODE_CONNECTED)
    _fail_count = 0

    # ---- Sensor POST (carries full radar buffer) ----
    if time.ticks_diff(now, _last_sensor) >= SENSOR_POST_INTERVAL_MS:
        sweep_buf = radar.get_and_drain()   # All measurements since last POST
        payload = {
            "sweep":    sweep_buf,          # [{seq, angle, distance}, ...]
            "flame":    sensors.read_flame(),
            "gate":     sensors.read_gate(),
            "leds":     leds.get_states()
        }
        api.send_sensor_data(payload)
        _last_sensor = time.ticks_ms()     # Refresh after HTTP completes
        continue                            # One HTTP call per iteration

    # ---- Health ping (250s — keeps Render.com free tier awake) ----
    if time.ticks_diff(now, _last_health) >= API_HEALTH_INTERVAL_MS:
        api.ping_health()
        _last_health = time.ticks_ms()
        continue

    time.sleep_ms(15)