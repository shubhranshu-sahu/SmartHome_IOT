# =============================================
# app/state.py  —  Shared in-memory state
#
# Single source of truth for ALL runtime data.
# Backend is the authority for LED states and
# protect mode — NOT the ESP32 sensor data.
# =============================================

from typing import Any

# ---- Command queue ----
pending_commands: list[dict[str, Any]] = []

# ---- Latest sensor snapshot (from ESP32) ----
latest_sensor: dict[str, Any] = {}

# ---- Authoritative LED states ----
led_states: dict[str, int] = {
    "room1": 0, "room2": 0, "room3": 0, "room4": 0
}

# ---- Protect mode ----
protect_mode: bool = False

# ---- Flame edge tracking ----
last_flame_state: bool = False

# ---- Gate edge tracking ----
last_gate_state: bool = False

# ---- ESP32 liveness ----
# Updated every time a /sensor-data POST arrives.
# Watchdog in main.py sets esp32_online=False if no POST in >5s.
import time as _time
last_sensor_post_ts: float = 0.0
esp32_online: bool = False

# ---- LED session tracking (in-memory, written to MongoDB on turn-off) ----
# Stores {room: datetime_turned_on} for currently-ON LEDs
import datetime as _dt
led_on_since: dict[str, _dt.datetime | None] = {
    "room1": None, "room2": None, "room3": None, "room4": None
}
