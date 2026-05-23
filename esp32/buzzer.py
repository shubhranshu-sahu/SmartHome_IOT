# =============================================
# buzzer.py  —  Active buzzer control
#
# Controls active buzzer on GPIO 26.
# Active buzzer sounds when voltage is applied
# — no PWM or frequency needed.
# =============================================

from machine import Pin
import time
from config  import BUZZER_PIN

_buzzer = Pin(BUZZER_PIN, Pin.OUT)
_buzzer.off()

print("[BUZZER] Initialised — pin:", BUZZER_PIN)

# ---- Public API ----

def on():
    """Turn buzzer on (continuous sound)."""
    _buzzer.on()

def off():
    """Turn buzzer off."""
    _buzzer.off()

def beep(duration_ms=100):
    """
    Single beep.
    duration_ms: how long to beep in milliseconds (default 100ms).
    Note: this is a blocking call for the duration.
    """
    _buzzer.on()
    time.sleep_ms(duration_ms)
    _buzzer.off()

def double_beep():
    """Two short beeps — used for alerts."""
    beep(100)
    time.sleep_ms(80)
    beep(100)
