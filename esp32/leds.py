# =============================================
# leds.py  —  Room LED control
#
# Controls 4 room LEDs on GPIO 16-19.
# All pin numbers come from config.py.
# =============================================

from machine import Pin
from config  import LED_PINS

# Initialise LED pins as outputs, all off at start
_leds = [Pin(p, Pin.OUT) for p in LED_PINS]

for _led in _leds:
    _led.off()

print("[LEDS] Initialised — pins:", LED_PINS)

# ---- Public API ----

def set_room(room, state):
    """
    Turn a single room LED on or off.
    room: 1–4
    state: True/1 = ON, False/0 = OFF
    """
    if 1 <= room <= 4:
        _leds[room - 1].value(1 if state else 0)
        print("[LEDS] Room", room, "→", "ON" if state else "OFF")
    else:
        print("[LEDS] Invalid room:", room)


def set_all(state):
    """Turn all 4 room LEDs on or off."""
    for led in _leds:
        led.value(1 if state else 0)
    print("[LEDS] All →", "ON" if state else "OFF")


def get_states():
    """Return current state of all 4 room LEDs as a dict."""
    return {
        "room1": _leds[0].value(),
        "room2": _leds[1].value(),
        "room3": _leds[2].value(),
        "room4": _leds[3].value()
    }
