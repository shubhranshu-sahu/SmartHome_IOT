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

from app.routes import health, sensor, commands, ws, stats
from app import db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: connect MongoDB.  Shutdown: disconnect."""
    await db.connect()
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
app.include_router(sensor.router)
app.include_router(commands.router)
app.include_router(ws.router)
app.include_router(stats.router)
