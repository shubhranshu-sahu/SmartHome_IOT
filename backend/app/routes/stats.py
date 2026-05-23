import datetime
from fastapi import APIRouter

from app import db, state

router = APIRouter(tags=["Stats"])

LED_CURRENT_MA   = 20
MCU_CURRENT_MA   = 80
SERVO_CURRENT_MA = 120


def _fmt_dt(dt: datetime.datetime | None) -> str | None:
    """
    Serialize a datetime to ISO-8601 string that JavaScript can parse correctly.
    Motor sometimes returns naive datetimes (UTC without tzinfo) — we always
    add +00:00 so `new Date(str)` in the browser interprets as UTC, not local.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)   # Motor naive → UTC
    return dt.isoformat()   # e.g. "2026-05-23T13:33:10+00:00"


def _today_start() -> datetime.datetime:
    """
    Return UTC datetime representing midnight of today in the SERVER's local
    timezone (e.g. IST midnight = 18:30 UTC of the previous day).
    This ensures "today" in the stats matches what the user sees on the clock.
    """
    local_midnight = (
        datetime.datetime.now().astimezone()          # local tz-aware now
        .replace(hour=0, minute=0, second=0, microsecond=0)
    )
    return local_midnight.astimezone(datetime.timezone.utc)


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
    now   = datetime.datetime.now(datetime.timezone.utc)
    hours_today = max((now - today).total_seconds() / 3600, 0.01)

    # ---- LED sessions ----
    rooms = ["room1", "room2", "room3", "room4"]
    led = {r: {"on_min": 0.0, "sessions": 0} for r in rooms}

    if db.is_connected():
        col = db.get_db().led_sessions
        sessions = await col.find({"turned_on": {"$gte": today}}).to_list(None)
        for s in sessions:
            r = s.get("room")
            if r in led:
                led[r]["sessions"] += 1
                led[r]["on_min"]   += s.get("duration_sec", 0) / 60

    # Add any currently-ON LEDs (session still open)
    for r in rooms:
        if state.led_on_since.get(r):
            elapsed_sec = (now - state.led_on_since[r]).total_seconds()
            led[r]["on_min"]   += elapsed_sec / 60
            led[r]["sessions"] += 1   # Currently active (counts as a session)

    # Derived stats per room (only from measured data)
    for r in rooms:
        on_min = led[r]["on_min"]
        n      = led[r]["sessions"]
        led[r]["on_min"]          = round(on_min, 2)
        led[r]["avg_session_min"] = round(on_min / n, 1) if n > 0 else 0.0
        led[r]["pct_of_day"]      = round((on_min / 60) / hours_today * 100, 1)
        # LED energy: P = I × V = 20mA × 3.3V = 66mW → Wh = 66mW × hours_on
        led[r]["energy_wh"]       = round((on_min / 60) * 0.020 * 3.3, 4)

    # ---- LED total energy (the ONE number we can compute honestly) ----
    total_led_wh   = round(sum(v["energy_wh"] for v in led.values()), 3)
    total_led_mah  = round(total_led_wh / 3.3 * 1000, 1)   # Back to mAh if needed

    # ---- Flame events ----
    flames = []
    if db.is_connected():
        docs = await db.get_db().flame_events.find(
            {"detected_at": {"$gte": today}},
            sort=[("detected_at", -1)]
        ).to_list(50)
        for d in docs:
            flames.append({
                "id":           str(d["_id"]),
                "detected_at":  _fmt_dt(d["detected_at"]),
                "cleared_at":   _fmt_dt(d.get("cleared_at")),
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
                "timestamp": _fmt_dt(d["timestamp"]),
                "state":     d["state"],
            })

    return {
        "date":         today.date().isoformat(),
        "hours_today":  round(hours_today, 2),
        "db_connected": db.is_connected(),
        "led":          led,
        # Only LED energy is calculated from real data (20mA × 3.3V × on-hours).
        # ESP32/servo consumption is NOT included — we have no sensor for that.
        "energy": {
            "led_wh":  total_led_wh,
            "led_mah": total_led_mah,
            "note":    "LED energy only. ESP32/servo draw not measured."
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
