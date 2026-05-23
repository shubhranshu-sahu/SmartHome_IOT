# =============================================
# app/routes/stats.py  —  Analytics API
#
# GET /stats/today  — today's LED usage, battery, events
# GET /stats/recent — last 7 days LED summary
# =============================================

import datetime
from fastapi import APIRouter

from app import db, state

router = APIRouter(tags=["Stats"])

LED_CURRENT_MA = 20          # mA per LED at 3.3V GPIO
MCU_CURRENT_MA = 80          # ESP32 base draw
SERVO_CURRENT_MA = 120       # Average servo draw (sweeps continuously)


def _today_start() -> datetime.datetime:
    now = datetime.datetime.now(datetime.timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _str_id(doc: dict) -> dict:
    """Convert ObjectId to string for JSON serialisation."""
    if doc and "_id" in doc:
        doc["id"] = str(doc["_id"])
        del doc["_id"]
    return doc


@router.get("/stats/today")
async def stats_today():
    """
    Returns today's stats:
    - LED on-time per room (minutes)
    - Battery consumed (mAh)
    - Flame events list
    - Gate events list
    Falls back gracefully if MongoDB not connected.
    """
    today = _today_start()

    # ---- LED sessions ----
    rooms = ["room1", "room2", "room3", "room4"]
    led = {r: {"on_min": 0.0, "sessions": 0, "battery_mah": 0.0} for r in rooms}

    if db.is_connected():
        col = db.get_db().led_sessions
        sessions = await col.find({"turned_on": {"$gte": today}}).to_list(None)
        for s in sessions:
            r = s.get("room")
            if r in led:
                led[r]["sessions"] += 1
                led[r]["on_min"]     += round(s.get("duration_sec", 0) / 60, 2)
                led[r]["battery_mah"] += s.get("battery_mah", 0)

    # Add any currently-ON LEDs (session not closed yet)
    now = datetime.datetime.now(datetime.timezone.utc)
    for r in rooms:
        if state.led_on_since.get(r):
            elapsed_sec = (now - state.led_on_since[r]).total_seconds()
            led[r]["on_min"]      += round(elapsed_sec / 60, 2)
            led[r]["battery_mah"] += round((elapsed_sec / 3600) * LED_CURRENT_MA, 4)
            led[r]["sessions"]    += 1   # Currently active

    # Total battery (LED + MCU base)
    led_total_mah  = sum(v["battery_mah"] for v in led.values())

    # MCU always-on: uptime from midnight ≈ hours since today_start
    hours_today = (now - today).total_seconds() / 3600
    mcu_mah     = round(hours_today * MCU_CURRENT_MA, 2)
    servo_mah   = round(hours_today * SERVO_CURRENT_MA, 2)
    total_mah   = round(led_total_mah + mcu_mah + servo_mah, 2)

    # ---- Flame events ----
    flames = []
    if db.is_connected():
        docs = await db.get_db().flame_events.find(
            {"detected_at": {"$gte": today}},
            sort=[("detected_at", -1)]
        ).to_list(50)
        for d in docs:
            flames.append({
                "id":          str(d["_id"]),
                "detected_at": d["detected_at"].isoformat(),
                "cleared_at":  d["cleared_at"].isoformat() if d.get("cleared_at") else None,
                "duration_sec": d.get("duration_sec"),
            })

    # ---- Gate events ----
    gates = []
    if db.is_connected():
        docs = await db.get_db().gate_events.find(
            {"timestamp": {"$gte": today}},
            sort=[("timestamp", -1)]
        ).to_list(100)
        for d in docs:
            gates.append({
                "id":        str(d["_id"]),
                "timestamp": d["timestamp"].isoformat(),
                "state":     d["state"],
            })

    return {
        "date":         today.date().isoformat(),
        "db_connected": db.is_connected(),
        "led":          led,
        "battery": {
            "led_mah":   round(led_total_mah, 2),
            "mcu_mah":   mcu_mah,
            "servo_mah": servo_mah,
            "total_mah": total_mah,
        },
        "flame_events": flames,
        "gate_events":  gates,
        "gate_opens":   sum(1 for g in gates if g["state"] == "open"),
        "gate_closes":  sum(1 for g in gates if g["state"] == "closed"),
    }


@router.get("/stats/recent")
async def stats_recent(days: int = 7):
    """
    Returns LED on-time per room for the last N days.
    Used for the 7-day bar chart on the stats page.
    """
    if not db.is_connected():
        return {"days": [], "db_connected": False}

    since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
    col   = db.get_db().led_sessions

    # Aggregate by (date, room)
    pipeline = [
        {"$match": {"turned_on": {"$gte": since}}},
        {"$group": {
            "_id": {
                "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$turned_on"}},
                "room": "$room"
            },
            "on_min":      {"$sum": {"$divide": ["$duration_sec", 60]}},
            "battery_mah": {"$sum": "$battery_mah"},
            "sessions":    {"$sum": 1}
        }},
        {"$sort": {"_id.date": 1}}
    ]

    results = await col.aggregate(pipeline).to_list(None)

    # Reshape for frontend: {date: {room1: {on_min, battery_mah}, ...}}
    days_map: dict = {}
    for r in results:
        date = r["_id"]["date"]
        room = r["_id"]["room"]
        if date not in days_map:
            days_map[date] = {}
        days_map[date][room] = {
            "on_min":      round(r["on_min"], 1),
            "battery_mah": round(r["battery_mah"], 3),
            "sessions":    r["sessions"]
        }

    return {
        "db_connected": True,
        "days": [
            {"date": date, "rooms": rooms_data}
            for date, rooms_data in sorted(days_map.items())
        ]
    }
