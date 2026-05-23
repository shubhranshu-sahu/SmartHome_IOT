# =============================================
# app/routes/health.py
#
# GET /health
# ESP32 pings this every 15s to verify the
# full WiFi → HTTP → FastAPI pipeline works.
# =============================================

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
def health():
    print("[HEALTH] Ping received")
    return {"status": "ok"}
