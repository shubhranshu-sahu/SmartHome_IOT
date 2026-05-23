# =============================================
# app/ws_manager.py  —  WebSocket connection manager
#
# Singleton that tracks all active browser
# WebSocket connections and broadcasts messages.
# =============================================

from fastapi import WebSocket
from typing import Set


class ConnectionManager:
    def __init__(self):
        self._active: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._active.add(ws)

    def disconnect(self, ws: WebSocket):
        self._active.discard(ws)

    async def broadcast(self, message: dict):
        """Send message to all connected browser clients. Dead sockets are pruned."""
        dead: Set[WebSocket] = set()
        for ws in list(self._active):
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)
        self._active -= dead

    @property
    def count(self) -> int:
        return len(self._active)


# Module-level singleton — import this everywhere
manager = ConnectionManager()
