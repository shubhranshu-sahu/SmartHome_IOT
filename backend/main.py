# =============================================
# main.py  —  FastAPI app entry point
#
# Run with:
#   py -3.11 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
#
# Phase 4: WebSocket + Protect Mode + LED stats
# =============================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import health, sensor, commands, ws, stats

app = FastAPI(
    title="Smart Home IoT Backend",
    version="0.4.0",
    description="ESP32 Smart Home — WebSocket + Protect Mode + LED Stats"
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
