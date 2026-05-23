# =============================================
# radar.py  —  Servo sweep + HC-SR04 distance
#
# Runs in its own background thread via start().
# The sweep is FULLY independent of WiFi/HTTP calls.
#
# IMPORTANT WIRING:
#   HC-SR04 VCC  → 5V pin  (NOT 3.3V)
#   HC-SR04 ECHO → 1kΩ → GPIO27 → 2kΩ → GND  (voltage divider!)
#   HC-SR04 TRIG → GPIO5  (direct)
#   SG90 VCC     → 5V pin  (+ 100µF cap to GND)
#   SG90 Signal  → GPIO25
# =============================================

from machine     import Pin, PWM, time_pulse_us
import time
import _thread
from config      import SERVO_PIN, TRIG_PIN, ECHO_PIN

# ---- Hardware init ----
_servo = PWM(Pin(SERVO_PIN), freq=50)
_trig  = Pin(TRIG_PIN, Pin.OUT)
_echo  = Pin(ECHO_PIN, Pin.IN)

# ---- Sweep constants ----
MIN_ANGLE = 15
MAX_ANGLE = 165
STEP      = 3          # Original working step size

# ---- Thread-shared state ----
# Written by radar thread, read by main thread.
# Dict assignment is atomic enough in MicroPython for this use case.
_latest = {"angle": MIN_ANGLE, "distance": None}

# ---- Sweep internals ----
_angle     = MIN_ANGLE
_direction = STEP

print("[RADAR] Initialised — servo:", SERVO_PIN,
      "| trig:", TRIG_PIN, "| echo:", ECHO_PIN)

# ---- Internal helpers ----

def _duty(angle):
    """Convert 0–180° to SG90 duty cycle (ESP32 50Hz, 0–1023 range)."""
    return int((angle / 180) * 75 + 40)

# ---- Public control functions ----

def set_angle(angle):
    angle = max(MIN_ANGLE, min(MAX_ANGLE, angle))
    _servo.duty(_duty(angle))


def get_distance():
    """
    Fire HC-SR04 and return distance in cm, or None on timeout.
    Run time: ~2–30ms depending on distance.
    """
    _trig.off()
    time.sleep_us(2)
    _trig.on()
    time.sleep_us(10)
    _trig.off()

    try:
        duration = time_pulse_us(_echo, 1, 30000)   # 30ms max = ~5m
        if duration < 0:
            return None
        dist = (duration * 0.0343) / 2
        return round(dist, 2) if 2 < dist <= 400 else None
    except Exception as e:
        return None


def get_latest():
    """Return the most recent {angle, distance} from the sweep thread."""
    return _latest


# ---- Background sweep thread ----

def _sweep_thread():
    """
    Runs continuously in a background thread.
    Sweeps 15°→165°→15° taking a distance reading at every step.
    Completely independent of WiFi/HTTP — never pauses for API calls.
    """
    global _angle, _direction, _latest

    print("[RADAR] Sweep thread started")

    while True:
        set_angle(_angle)
        dist = get_distance()

        # Atomic update of shared state
        _latest = {"angle": _angle, "distance": dist}

        _angle += _direction

        if _angle >= MAX_ANGLE:
            _direction = -STEP
        elif _angle <= MIN_ANGLE:
            _direction = STEP


def start():
    """Start the radar sweep in a background thread. Call once at boot."""
    _thread.start_new_thread(_sweep_thread, ())
