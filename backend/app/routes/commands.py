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
#   - Then queues for ESP32 to execute within 500ms
#   - This eliminates the "toggle bounce" bug where the
#     next sensor poll would revert the UI to old state.
# =============================================

import time
from fastapi import APIRouter, Request

from app import state
from app.ws_manager import manager

router = APIRouter(tags=["Commands"])


# ---- ESP32 polling ---- #

@router.get("/command/pending")
def command_pending():
    """ESP32 polls this every 500ms. Returns + clears the queue."""
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
    ESP32 picks it up on its next 500ms poll.
    """
    cmd    = await request.json()
    action = cmd.get("action", "")

    # --- Update authoritative state instantly ---
    if action == "set_led":
        room = cmd.get("room")
        val  = cmd.get("state", 0)
        key  = f"room{room}"
        _track_led_change(key, val)
        state.led_states[key] = val

    elif action == "set_all":
        val = cmd.get("state", 0)
        for r in range(1, 5):
            _track_led_change(f"room{r}", val)
            state.led_states[f"room{r}"] = val

    elif action == "protect_mode":
        state.protect_mode = cmd.get("state", False)
        print("[CMD] Protect mode:", state.protect_mode)

    # --- Queue for ESP32 ---
    state.pending_commands.append(cmd)
    print("[CMD] Queued:", cmd)

    # --- Broadcast to all browsers immediately via WebSocket ---
    await manager.broadcast({
        "type": "state_update",
        "data": {
            "leds":         state.led_states,
            "protect_mode": state.protect_mode,
        }
    })

    return {"queued": True}


# ---- LED on-time tracking ---- #

def _track_led_change(key: str, new_val: int):
    """Track how long each LED is on for stats."""
    current = state.led_states.get(key, 0)
    now     = time.time()

    if current == 1 and new_val == 0:
        # Turning off — accumulate time
        on_since = state.led_on_since.get(key)
        if on_since is not None:
            state.led_total_on_sec[key] = state.led_total_on_sec.get(key, 0) + (now - on_since)
            state.led_on_since[key] = None

    elif current == 0 and new_val == 1:
        # Turning on — record start time
        state.led_on_since[key] = now
