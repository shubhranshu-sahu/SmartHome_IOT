# =============================================
# radar.py  —  Servo sweep + HC-SR04 distance
#
# Runs in its own background thread via start().
# The sweep is FULLY independent of WiFi/HTTP calls.
#
# PHASE 4 CHANGES:
#   - Rolling buffer replaces single _latest dict
#   - get_and_drain() empties buffer for each POST
#   - get_latest() still works for buzzer logic
#   - Sweep speed reduced slightly (SETTLE_MS = 22)
#   - Sequence number on every measurement lets
#     the frontend reconstruct the exact sweep path
#
# IMPORTANT WIRING:
#   HC-SR04 VCC  → 5V pin  (NOT 3.3V)
#   HC-SR04 ECHO → 1kΩ → GPIO27 → 2kΩ → GND  (voltage divider!)
#   HC-SR04 TRIG → GPIO5  (direct)
#   SG90 VCC     → 5V pin  (+ 100µF cap to GND)
#   SG90 Signal  → GPIO25
# =============================================

from machine import Pin, PWM, time_pulse_us
import time
import _thread
from config import SERVO_PIN, TRIG_PIN, ECHO_PIN

# ---- Hardware init ----
_servo = PWM(Pin(SERVO_PIN), freq=50)
_trig  = Pin(TRIG_PIN, Pin.OUT)
_echo  = Pin(ECHO_PIN, Pin.IN)

# ---- Sweep constants ----
MIN_ANGLE  = 15
MAX_ANGLE  = 165
STEP       = 3       # degrees per move
SETTLE_MS  = 22      # ms to wait after each servo move (was ~0, slight slow-down)
MAX_BUFFER = 60      # keep at most 60 measurements in buffer

# ---- Thread-shared rolling buffer ----
# Written by radar thread, drained by main thread.
_buf      = []       # list of {seq, angle, distance}
_buf_lock = _thread.allocate_lock()
_seq      = 0        # global sequence counter

# Keep a copy of the very latest for buzzer logic (no lock needed — dict assign atomic)
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
        duration = time_pulse_us(_echo, 1, 11600)   # 11.6ms max ≈ 200cm range
        # 30ms was overkill (5m range) and added latency when nothing in range.
        # 200cm is the practical radar max for an indoor room.
        if duration < 0:
            return None
        dist = (duration * 0.0343) / 2
        return round(dist, 2) if 2 < dist <= 400 else None
    except Exception:
        return None


def get_latest():
    """Return the most recent {angle, distance} snapshot (for buzzer logic)."""
    return _latest


def get_and_drain():
    """
    Return all buffered measurements since the last call, then clear the buffer.
    Each item includes rel_ms: milliseconds before this drain happened
    (negative number: e.g. -750 means measured 750ms before POST was sent).
    Frontend uses rel_ms to know the true age of each measurement.
    """
    _buf_lock.acquire()
    items = list(_buf)
    _buf.clear()
    _buf_lock.release()

    drain_ts = time.ticks_ms()
    for item in items:
        item["rel_ms"] = -time.ticks_diff(drain_ts, item["ts"])  # negative = older
        del item["ts"]  # Remove raw ts, keep rel_ms only
    return items


# ---- Background sweep thread ----

def _sweep_thread():
    """
    Runs continuously in a background thread.
    Sweeps MIN_ANGLE→MAX_ANGLE→MIN_ANGLE taking a distance reading at every step.
    Completely independent of WiFi/HTTP — never pauses for API calls.
    """
    global _angle, _direction, _latest, _seq

    print("[RADAR] Sweep thread started")

    while True:
        set_angle(_angle)
        time.sleep_ms(SETTLE_MS)   # Let servo reach position before measuring
        dist = get_distance()

        # Update latest for buzzer logic (atomic dict assignment — no lock needed)
        _latest = {"angle": _angle, "distance": dist}

        # Append to rolling buffer (guarded by lock)
        _buf_lock.acquire()
        _seq += 1
        _buf.append({
            "seq":      _seq,
            "angle":    _angle,
            "distance": dist,
            "dir":      1 if _direction > 0 else -1,   # Explicit: +1 or -1
            "ts":       time.ticks_ms()
        })
        if len(_buf) > MAX_BUFFER:
            _buf.pop(0)
        _buf_lock.release()

        # Advance angle; bounce at limits
        _angle += _direction
        if _angle >= MAX_ANGLE:
            _angle     = MAX_ANGLE
            _direction = -STEP
        elif _angle <= MIN_ANGLE:
            _angle     = MIN_ANGLE
            _direction = STEP


def start():
    """Start the radar sweep in a background thread. Call once at boot."""
    _thread.start_new_thread(_sweep_thread, ())
