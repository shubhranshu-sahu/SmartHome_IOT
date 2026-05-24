# =============================================
# main.py  —  ESP32 orchestrator (Phase 5)
#
# ARCHITECTURE (3 independent threads):
#
#   radar.py thread     — servo sweep + distance measurement
#                         Runs tight, never blocks on HTTP.
#                         Updates radar buffer continuously.
#
#   _sensor_thread      — sensor POST every 800ms
#                         MOVED OUT OF MAIN LOOP so the main loop
#                         is NEVER blocked by a slow HTTP call to Render.
#                         A slow POST (1-3s) no longer freezes the buzzer
#                         or starves the radar buffer.
#
#   _cmd_thread         — command poll every 300ms
#                         Independent from everything else.
#                         Executes LED/buzzer/protect-mode commands.
#
#   Main loop (Core 0)  — buzzer state machine + WiFi watchdog + LED update
#                         Always runs at ~15ms tick.
#                         Never makes any HTTP calls.
#
# With this split:
#   - Servo sweeps smoothly with no HTTP-induced pauses
#   - Radar buffer fills continuously (no gaps from blocked main loop)
#   - Buzzer reacts in <15ms to proximity changes
#   - Commands arrive within 300ms + HTTP time
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
        # One-shot manual beep. Duration from command, default 500ms.
        dur = cmd.get("duration_ms", 500)
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
# Polls /command/pending every 300ms.
# Completely independent of main loop and sensor POST.
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
# SENSOR POST THREAD
#
# Previously this was in the main loop.
# PROBLEM: api.send_sensor_data() blocks for 1-3s on Render's free tier.
# While it blocked, the main loop couldn't run _update_buzzer(), and
# radar.get_and_drain() was called infrequently → large angle gaps in buffer.
#
# FIX: Move to its own thread. The main loop now runs every ~15ms
# regardless of HTTP round-trip time.
# =============================================

# Health ping interval (keep Render alive; from config)
_last_health_ts = [0]  # mutable list so thread can write to it


def _sensor_thread():
    """Background thread: POSTs sensor data + health ping."""
    print("[SENSOR] Sensor POST thread started")
    last_sensor = time.ticks_ms()
    last_health = time.ticks_ms()

    while True:
        now = time.ticks_ms()

        # ---- Sensor POST (radar buffer + flame + gate) ----
        if time.ticks_diff(now, last_sensor) >= SENSOR_POST_INTERVAL_MS:
            sweep_buf = radar.get_and_drain()   # All readings since last POST
            payload = {
                "sweep": sweep_buf,
                "flame": sensors.read_flame(),
                "gate":  sensors.read_gate(),
                "leds":  leds.get_states()
            }
            try:
                api.send_sensor_data(payload)
            except Exception as e:
                print("[SENSOR] POST error:", e)
            last_sensor = time.ticks_ms()
            # Yield a bit after HTTP call
            time.sleep_ms(50)
            continue

        # ---- Health ping (250s — keeps Render.com free tier awake) ----
        if time.ticks_diff(now, last_health) >= API_HEALTH_INTERVAL_MS:
            try:
                api.ping_health()
            except Exception as e:
                print("[HEALTH] Ping error:", e)
            last_health = time.ticks_ms()
            time.sleep_ms(50)
            continue

        time.sleep_ms(20)


# =============================================
# NON-BLOCKING BUZZER ENGINE  (called from main loop every ~15ms)
#
# Priority order:
#   P1: Flame detected       → solid ON (direct sensor read, zero latency)
#   P2: Manual beep          → ON until timer expires
#   P3: Protect mode + close → variable-rate beep based on distance
#       <25cm  → 40ms off  (very rapid — danger zone)
#       <50cm  → 180ms off (fast)
#       <80cm  → 420ms off (moderate)
#       <110cm → 750ms off (slow warning)
#       else   → silent
#   P4: No threat            → off
#
# All of this runs on the ESP32 with no network round-trip.
# Protect mode flag is set by _cmd_thread when backend sends the command.
# Distance is read from radar module's latest reading.
# =============================================

def _update_buzzer(now_ms, distance):
    global _buzz_state, _buzz_changed_ms, _buzz_off_ms, _manual_beep_end

    # P1: Flame → solid on
    if sensors.read_flame():
        buzzer.on()
        _buzz_state = False
        return

    # P2: Manual beep (from alarm button)
    if time.ticks_diff(_manual_beep_end, now_ms) > 0:
        buzzer.on()
        return

    # P3: Protect mode proximity beep
    if _protect_mode and distance is not None:
        if   distance < 25:  _buzz_off_ms = 40    # Very rapid
        elif distance < 50:  _buzz_off_ms = 130   # Fast
        elif distance < 80:  _buzz_off_ms = 320   # Moderate
        elif distance < 110: _buzz_off_ms = 620   # Slow warning
        else:                _buzz_off_ms = -1    # Too far — silent
    else:
        _buzz_off_ms = -1

    # P4: No threat
    if _buzz_off_ms < 0:
        buzzer.off()
        _buzz_state = False
        return

    # Toggle the buzzer based on timers
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

# Start command poll thread (independent HTTP, ~300ms cycle)
_thread.start_new_thread(_cmd_thread, ())

# Start sensor POST thread (independent HTTP, ~800ms cycle)
# This is the key fix: main loop is now NEVER blocked by HTTP calls.
_thread.start_new_thread(_sensor_thread, ())

print("[MAIN] System Running — Phase 5 (3-thread: radar | cmd | sensor)")

# =============================================
# MAIN LOOP — Buzzer engine + WiFi watchdog + LED update
#
# This loop ONLY does local work:
#   - update_led()      — hardware PWM, microsecond precision
#   - _update_buzzer()  — buzzer state machine, 15ms resolution
#   - WiFi watchdog     — reconnect if dropped
#
# It makes NO HTTP calls. It never blocks.
# Radar buffer fills independently in radar.py thread.
# HTTP happens independently in _sensor_thread and _cmd_thread.
# =============================================

while True:
    now = time.ticks_ms()

    # Local hardware update — always fast
    update_led()
    _rd = radar.get_latest()
    _update_buzzer(now, _rd["distance"])

    # ---- WiFi watchdog ----
    if not wifi_is_connected():
        set_mode(MODE_DISCONNECTED)
        print("[MAIN] WiFi lost — reconnecting...")
        if connect_wifi():
            print("[MAIN] Reconnected!")
        time.sleep_ms(100)
        continue

    set_mode(MODE_CONNECTED)
    time.sleep_ms(15)