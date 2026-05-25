# =============================================
# sensors.py  —  Passive sensor reads
#
# Reads KY-026 flame sensor and FC-51 IR sensor.
# Flame sensor: GPIO34 (input-only), IR sensor: GPIO21 (standard I/O)
# Both sensors output LOW when triggered.
# =============================================

from machine import Pin
from config  import FLAME_PIN, IR_PIN

# GPIO 34 is input-only on ESP32 (flame). GPIO21 is standard — used for IR.
_flame = Pin(FLAME_PIN, Pin.IN)
_ir    = Pin(IR_PIN,    Pin.IN)

print("[SENSORS] Initialised — flame:", FLAME_PIN, "IR:", IR_PIN)

# ---- Public API ----

def read_flame():
    """
    Read KY-026 flame sensor.
    Returns True if flame detected, False if clear.
    KY-026 digital output: LOW (0) = flame detected.
    """
    return _flame.value() == 0


def read_gate():
    """
    Read FC-51 IR obstacle sensor used as gate sensor.
    Returns True if gate is CLOSED (obstacle/beam break detected).
    Returns False if gate is OPEN (no obstacle).
    FC-51 digital output: LOW (0) = obstacle detected.
    """
    return _ir.value() == 0
