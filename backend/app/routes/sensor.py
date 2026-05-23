# =============================================
# app/routes/sensor.py  —  Sensor data from ESP32
#
# POST /sensor-data  — ESP32 pushes every 400ms
# GET  /sensor-data/latest — HTTP fallback
#
# Phase 5 additions:
#   - Flame EDGE detection → writes flame_events to MongoDB
#   - Gate EDGE detection  → writes gate_events to MongoDB
#   - LED states from ESP32 are IGNORED (state.py is authoritative)
# =============================================

import datetime
from fastapi import APIRouter, Request

from app import state, db
from app.ws_manager import manager

router = APIRouter(tags=["Sensor"])


@router.post("/sensor-data")
async def receive_sensor_data(request: Request):
    data = await request.json()

    # ---- Mark ESP32 as alive ----
    import time
    state.last_sensor_post_ts = time.time()
    was_online = state.esp32_online
    state.esp32_online = True

    # Rising edge: ESP32 just came back online
    if not was_online:
        print("[SENSOR] ✓ ESP32 came online")
        await manager.broadcast({"type": "esp32_status", "data": {"online": True}})

    sweep = data.get("sweep", [])

    # Latest angle/distance from last item in sweep buffer
    latest_angle    = None
    latest_distance = None
    if sweep:
        last = sweep[-1]
        latest_angle    = last.get("angle")
        latest_distance = last.get("distance")

    # Store snapshot for HTTP fallback
    state.latest_sensor = {
        "angle":    latest_angle,
        "distance": latest_distance,
        "flame":    data.get("flame", False),
        "gate":     data.get("gate", False),
    }

    # ---- Flame edge detection ----
    new_flame = data.get("flame", False)
    if new_flame and not state.last_flame_state:
        # Rising edge — flame just detected
        print("[SENSOR] 🔥 FLAME DETECTED")
        state.pending_commands.append({"action": "beep", "duration_ms": 1000})
        await _write_flame_event(detected=True)
    elif not new_flame and state.last_flame_state:
        # Falling edge — flame cleared
        print("[SENSOR] Flame cleared")
        await _write_flame_event(detected=False)
    state.last_flame_state = new_flame

    # ---- Gate edge detection ----
    new_gate = data.get("gate", False)
    if new_gate != state.last_gate_state:
        gate_str = "closed" if new_gate else "open"
        print(f"[SENSOR] Gate → {gate_str}")
        await _write_gate_event(gate_str)
    state.last_gate_state = new_gate

    # ---- Broadcast to browser via WebSocket ----
    await manager.broadcast({
        "type": "sensor_update",
        "data": {
            "sweep":        sweep,
            "angle":        latest_angle,
            "distance":     latest_distance,
            "flame":        data.get("flame", False),
            "gate":         data.get("gate", False),
            "leds":         state.led_states,
            "protect_mode": state.protect_mode,
            "esp32_online": True,
        }
    })

    return {"success": True}


@router.get("/sensor-data/latest")
def latest_sensor_data():
    """HTTP fallback when WebSocket is unavailable."""
    return {
        **state.latest_sensor,
        "sweep":        [],
        "leds":         state.led_states,
        "protect_mode": state.protect_mode,
    }


# ---- MongoDB event writers ---- #

# Track open flame event ID to update when cleared
_open_flame_id = None

async def _write_flame_event(detected: bool):
    global _open_flame_id
    if not db.is_connected():
        return
    col = db.get_db().flame_events
    now = datetime.datetime.now(datetime.timezone.utc)
    try:
        if detected:
            result = await col.insert_one({"detected_at": now, "cleared_at": None, "duration_sec": None})
            _open_flame_id = result.inserted_id
        elif _open_flame_id:
            doc = await col.find_one({"_id": _open_flame_id})
            if doc:
                dur = (now - doc["detected_at"]).total_seconds()
                await col.update_one(
                    {"_id": _open_flame_id},
                    {"$set": {"cleared_at": now, "duration_sec": round(dur, 1)}}
                )
            _open_flame_id = None
    except Exception as e:
        print(f"[DB] Flame event write failed: {e}")


async def _write_gate_event(state_str: str):
    if not db.is_connected():
        return
    try:
        await db.get_db().gate_events.insert_one({
            "timestamp": datetime.datetime.now(datetime.timezone.utc),
            "state":     state_str,
        })
    except Exception as e:
        print(f"[DB] Gate event write failed: {e}")
