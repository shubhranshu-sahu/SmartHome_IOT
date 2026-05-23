# =============================================
# app/routes/ws.py  —  WebSocket endpoint
#
# Browser connects here for real-time updates.
# Server sends a heartbeat every 20s to keep the
# connection alive through proxies and firewalls.
# =============================================

import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.ws_manager import manager
from app import state

router = APIRouter(tags=["WebSocket"])

HEARTBEAT_INTERVAL = 20   # seconds


def _full_state() -> dict:
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
        # Push current state immediately on connect
        await ws.send_json({"type": "init", "data": _full_state()})

        # Keep connection alive with periodic heartbeat
        while True:
            try:
                # Wait for a client message, but also send heartbeat if idle
                await asyncio.wait_for(ws.receive_text(), timeout=HEARTBEAT_INTERVAL)
            except asyncio.TimeoutError:
                # No message received — send a ping to keep the socket alive
                await ws.send_json({"type": "ping"})

    except WebSocketDisconnect:
        manager.disconnect(ws)
        print(f"[WS] Client disconnected — active: {manager.count}")
    except Exception as e:
        manager.disconnect(ws)
        print(f"[WS] Error: {e} — active: {manager.count}")
