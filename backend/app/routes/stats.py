# =============================================
# app/routes/stats.py  —  LED usage statistics
#
# GET /stats/leds — returns per-room on-time
# (Phase 4: in-memory. Phase 7: stored in MongoDB)
# =============================================

import time
from fastapi import APIRouter
from app import state

router = APIRouter(tags=["Stats"])


@router.get("/stats/leds")
def led_stats():
    """Return cumulative on-time per room."""
    now    = time.time()
    result = {}
    for r in range(1, 5):
        key    = f"room{r}"
        total  = state.led_total_on_sec.get(key, 0.0)
        # Add current session if LED is currently on
        on_since = state.led_on_since.get(key)
        if on_since is not None:
            total += now - on_since
        result[key] = {
            "is_on":      state.led_states.get(key, 0) == 1,
            "on_seconds": round(total, 1),
            "on_minutes": round(total / 60, 2),
        }
    return {"led_stats": result}
