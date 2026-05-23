# =============================================
# main.py  —  FastAPI app entry point (Phase 5)
#
# Run with:
#   py -3.11 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
#
# Phase 5: MongoDB Atlas for LED sessions, flame events, gate events
# =============================================

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import health, sensor, commands, ws, stats, auth
from app import db

from dotenv import load_dotenv

load_dotenv()

import asyncio
import time

from app import state as app_state
from app.ws_manager import manager as ws_manager


async def _esp32_watchdog():
    """
    Runs every 3s. If no /sensor-data POST has arrived in >5s,
    marks ESP32 as offline and broadcasts the falling-edge event.
    The 5s threshold gives the ESP32 two missed 400ms cycles plus
    a generous HTTP buffer before we declare it dead.
    """
    while True:
        await asyncio.sleep(3)
        if app_state.esp32_online and (time.time() - app_state.last_sensor_post_ts) > 5:
            app_state.esp32_online = False
            print("[WATCHDOG] ✗ ESP32 offline — no sensor data for 5s")
            await ws_manager.broadcast({"type": "esp32_status", "data": {"online": False}})


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: connect MongoDB + start watchdog.  Shutdown: disconnect."""
    await db.connect()
    asyncio.create_task(_esp32_watchdog())
    yield
    await db.disconnect()


app = FastAPI(
    title       = "Smart Home IoT Backend",
    version     = "0.5.0",
    description = "ESP32 Smart Home — WebSocket + Protect Mode + MongoDB Stats",
    lifespan    = lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(sensor.router)
app.include_router(commands.router)
app.include_router(ws.router)
app.include_router(stats.router)
