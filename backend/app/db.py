# =============================================
# app/db.py  —  MongoDB Atlas connection
#
# Uses Motor (async driver) so FastAPI never blocks.
# Call connect() at startup, disconnect() at shutdown.
#
# If MONGODB_URI is not set, all write methods
# silently do nothing and reads return empty lists.
# This lets the app run without a DB for local dev.
# =============================================

import os
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


def get_db() -> AsyncIOMotorDatabase | None:
    return _db


def is_connected() -> bool:
    return _db is not None


async def connect():
    global _client, _db
    uri = os.getenv("MONGODB_URI", "").strip()
    if not uri:
        print("[DB] MONGODB_URI not set — MongoDB disabled (stats won't persist)")
        return
    try:
        _client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000)
        # Ping to verify connection
        await _client.admin.command("ping")
        _db = _client["smart_home"]
        print("[DB] ✓ Connected to MongoDB Atlas — database: smart_home")
        # Ensure indexes for fast date-based queries
        await _db.led_sessions.create_index("turned_on")
        await _db.led_sessions.create_index("room")
        await _db.flame_events.create_index("detected_at")
        await _db.gate_events.create_index("timestamp")
    except Exception as e:
        print(f"[DB] ✗ MongoDB connection failed: {e}")
        _db = None


async def disconnect():
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
        print("[DB] Disconnected from MongoDB")
