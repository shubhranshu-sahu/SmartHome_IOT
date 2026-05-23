# =============================================
# app/routes/commands.py  —  Command queue
#
# POST /command  — dashboard sends LED/buzzer/protect commands
# GET  /command/pending — ESP32 polls for commands to execute
# GET  /command/queue   — debug: inspect without consuming
#
# KEY DESIGN:
#   - /command updates state.led_states IMMEDIATELY
#   - Then broadcasts via WebSocket → UI updates in <50ms
#   - Then queues for ESP32 to execute within 300ms
#   - LED sessions are persisted to MongoDB on each state change
# =============================================

import datetime
from fastapi import APIRouter, Request

from app import state, db
from app.ws_manager import manager

router = APIRouter(tags=["Commands"])


# ---- ESP32 polling ---- #

@router.get("/command/pending")
def command_pending():
    """ESP32 polls this every 300ms. Returns + clears the queue."""
    cmds = list(state.pending_commands)
    state.pending_commands.clear()
    if cmds:
        print("[CMD] → ESP32:", cmds)
    return {"commands": cmds}


@router.get("/command/queue")
def view_queue():
    """Debug: inspect pending commands without consuming them."""
    return {"commands": state.pending_commands, "count": len(state.pending_commands)}


# ---- Dashboard commands ---- #

@router.post("/command")
async def queue_command(request: Request):
    """
    Dashboard sends a command here.
    State is updated IMMEDIATELY then broadcast via WS.
    ESP32 picks it up on its next 300ms poll.
    LED on/off sessions are persisted to MongoDB.
    """
    cmd    = await request.json()
    action = cmd.get("action", "")

    # --- Update authoritative state + write LED sessions ---
    if action == "set_led":
        room = cmd.get("room")
        val  = cmd.get("state", 0)
        key  = f"room{room}"
        if state.esp32_online:
            await _track_led_change(key, val)   # Only persist when ESP32 can act on it
        state.led_states[key] = val

    elif action == "set_all":
        val = cmd.get("state", 0)
        for r in range(1, 5):
            if state.esp32_online:
                await _track_led_change(f"room{r}", val)
            state.led_states[f"room{r}"] = val

    elif action == "protect_mode":
        state.protect_mode = cmd.get("state", False)
        print("[CMD] Protect mode:", state.protect_mode)

    # --- Queue for ESP32 (picks it up on next 300ms poll) ---
    state.pending_commands.append(cmd)
    print("[CMD] Queued:", cmd)

    # --- Broadcast to all browsers immediately ---
    await manager.broadcast({
        "type": "state_update",
        "data": {
            "leds":         state.led_states,
            "protect_mode": state.protect_mode,
            "esp32_online": state.esp32_online,
        }
    })

    return {
        "queued":       True,
        "esp32_online": state.esp32_online,
        # If offline, command is queued and will execute when ESP32 reconnects
    }


# ---- LED session tracking ---- #

async def _track_led_change(key: str, new_val: int):
    """
    Track LED on→off transitions.
    Writes a session document to MongoDB when LED turns off.
    Records turn-on time in state.led_on_since when LED turns on.
    """
    current = state.led_states.get(key, 0)
    now     = datetime.datetime.now(datetime.timezone.utc)

    if current == 0 and new_val == 1:
        # --- Turning ON ---
        state.led_on_since[key] = now
        print(f"[LED] {key} ON at {now.isoformat()}")

    elif current == 1 and new_val == 0:
        # --- Turning OFF → write session to MongoDB ---
        on_since = state.led_on_since.get(key)
        state.led_on_since[key] = None

        if on_since and db.is_connected():
            duration_sec = (now - on_since).total_seconds()
            session = {
                "room":         key,
                "turned_on":    on_since,
                "turned_off":   now,
                "duration_sec": round(duration_sec, 1),
                # Battery estimate: 20mA × duration in hours
                "battery_mah":  round((duration_sec / 3600) * 20, 4),
            }
            try:
                await db.get_db().led_sessions.insert_one(session)
                print(f"[LED] {key} session saved — {duration_sec:.0f}s / {session['battery_mah']:.3f}mAh")
            except Exception as e:
                print(f"[LED] DB write failed: {e}")
