# =============================================
# app/routes/ws.py  —  WebSocket endpoint
#
# Browser connects here for real-time updates.
# On connect: sends full current state immediately.
# On each ESP32 POST: backend broadcasts sensor_update.
# On each command: backend broadcasts state_update.
# =============================================

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.ws_manager import manager
from app import state

router = APIRouter(tags=["WebSocket"])


def _full_state() -> dict:
    """Return complete current state for the 'init' message."""
    return {
        "leds":         state.led_states,
        "protect_mode": state.protect_mode,
        "sensor":       state.latest_sensor,
    }


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    print(f"[WS] Client connected  — active: {manager.count}")

    try:
        # Push full state immediately so UI doesn't wait for first ESP32 POST
        await ws.send_json({"type": "init", "data": _full_state()})

        # Hold connection open — ESP32 POSTs trigger broadcasts via manager.broadcast()
        while True:
            await ws.receive_text()   # raises WebSocketDisconnect on close

    except WebSocketDisconnect:
        manager.disconnect(ws)
        print(f"[WS] Client disconnected — active: {manager.count}")
