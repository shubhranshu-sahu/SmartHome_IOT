# =============================================
# hardware.py  —  D2 WiFi status LED
#
# Non-blocking blink — call update_led()
# frequently inside your main loop.
#
# Modes:
#   MODE_DISCONNECTED  →  slow blink  500 ms
#   MODE_AP            →  fast blink  100 ms
#   MODE_CONNECTED     →  solid ON
# =============================================

from machine import Pin
import time
from config import WIFI_LED_PIN

# ---- LED object ----
_led       = Pin(WIFI_LED_PIN, Pin.OUT)
_led.off()

# ---- Mode constants ----
MODE_DISCONNECTED = 0
MODE_AP           = 1
MODE_CONNECTED    = 2

# ---- Internal state ----
_mode      = MODE_DISCONNECTED
_led_state = False
_last_ms   = 0

# ---- Public API ----

def set_mode(mode):
    global _mode
    _mode = mode
    if mode == MODE_CONNECTED:
        _led.on()          # Solid on immediately

def update_led():
    """Call this as often as possible inside loops."""
    global _led_state, _last_ms

    if _mode == MODE_CONNECTED:
        # Already forced solid ON in set_mode()
        return

    interval = 20 if _mode == MODE_AP else 500

    now = time.ticks_ms()
    if time.ticks_diff(now, _last_ms) >= interval:
        _led_state = not _led_state
        _led.value(_led_state)
        _last_ms = now