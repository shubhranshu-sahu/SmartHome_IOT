# =============================================
# app/state.py  —  Shared in-memory state
#
# Single source of truth for ALL runtime data.
# Backend is the authority for LED states and
# protect mode — NOT the ESP32 sensor data.
# =============================================

from typing import Any
import time as _time

# ---- Command queue ----
# ESP32 polls /command/pending every 500ms.
pending_commands: list[dict[str, Any]] = []

# ---- Latest sensor snapshot (from ESP32) ----
latest_sensor: dict[str, Any] = {}

# ---- Authoritative LED states ----
# Updated immediately when /command is received.
# NOT overwritten by ESP32 sensor data reports.
led_states: dict[str, int] = {
    "room1": 0, "room2": 0, "room3": 0, "room4": 0
}

# ---- Protect mode ----
protect_mode: bool = False

# ---- Flame edge tracking (for auto-beep on first detect) ----
last_flame_state: bool = False

# ---- LED on-time tracking (Phase 4 in-memory; MongoDB in Phase 7) ----
led_on_since: dict[str, float | None] = {
    "room1": None, "room2": None, "room3": None, "room4": None
}
led_total_on_sec: dict[str, float] = {
    "room1": 0.0, "room2": 0.0, "room3": 0.0, "room4": 0.0
}
