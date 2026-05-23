# =============================================
# app/routes/sensor.py  —  Sensor data from ESP32
#
# POST /sensor-data  — ESP32 pushes readings every 500ms
# GET  /sensor-data/latest — fallback HTTP poll for clients
#
# KEY DESIGN:
#   - LED states in payload are IGNORED for display
#     (backend tracks authoritatively via commands)
#   - Payload is broadcast via WebSocket to all browsers
#   - Flame edge detection → auto-queues alarm beep
# =============================================

from fastapi import APIRouter, Request

from app import state
from app.ws_manager import manager

router = APIRouter(tags=["Sensor"])


@router.post("/sensor-data")
async def receive_sensor_data(request: Request):
    data = await request.json()

    # Store snapshot (angle, distance, flame, gate only — not LED states)
    state.latest_sensor = {
        "angle":    data.get("angle"),
        "distance": data.get("distance"),
        "flame":    data.get("flame", False),
        "gate":     data.get("gate", False),
    }

    # Flame edge detection: beep alarm on first detect, not every 500ms
    new_flame = data.get("flame", False)
    if new_flame and not state.last_flame_state:
        print("[SENSOR] 🔥 FLAME DETECTED — queueing alarm")
        state.pending_commands.append({"action": "beep", "duration_ms": 1000})
    state.last_flame_state = new_flame

    # Broadcast full state to all browser WebSocket clients
    await manager.broadcast({
        "type": "sensor_update",
        "data": {
            **state.latest_sensor,
            "leds":         state.led_states,
            "protect_mode": state.protect_mode,
        }
    })

    print(
        f"[SENSOR] angle={data.get('angle')}° "
        f"dist={data.get('distance')}cm "
        f"flame={data.get('flame')} gate={data.get('gate')}"
    )
    return {"success": True}


@router.get("/sensor-data/latest")
def latest_sensor_data():
    """HTTP fallback — used if WebSocket unavailable."""
    return {
        **state.latest_sensor,
        "leds":         state.led_states,
        "protect_mode": state.protect_mode,
    }
