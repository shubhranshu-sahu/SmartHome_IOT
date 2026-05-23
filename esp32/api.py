# =============================================
# api.py  —  ESP32 HTTP communication layer
#
# All network calls to the FastAPI backend
# go through this file.
#
# Design rules:
#   - Every function wraps in try/except
#   - Never raises — returns safe default on failure
#   - Prints [API] prefixed status to console
#   - Closes every response object to free RAM
# =============================================

import urequests
import ujson
from config import DEFAULT_API_BASE

# ---- Load API base URL (cached after first read) ----
_base_url = None

def _get_base():
    """
    Return API base URL from config.json (cached after first read).
    Falls back to DEFAULT_API_BASE if config.json is missing,
    or if api_base field is empty / not a valid http URL.
    """
    global _base_url
    if _base_url is None:
        try:
            with open("config.json", "r") as f:
                url = ujson.load(f).get("api_base", "")
            if url and url.startswith("http"):
                _base_url = url
                print("[API] Base URL:", _base_url)
            else:
                _base_url = DEFAULT_API_BASE
                print("[API] api_base empty/invalid in config.json")
                print("[API] Using default:", _base_url)
        except Exception as e:
            _base_url = DEFAULT_API_BASE
            print("[API] Config read failed:", e)
            print("[API] Using default:", _base_url)
    return _base_url

# ---- Endpoints ----

def ping_health():
    """
    GET /health
    Verifies the full ESP32 → WiFi → FastAPI pipeline.
    Returns True on success, False on failure.
    """
    try:
        url = _get_base() + "/health"
        r   = urequests.get(url, timeout=2)
        data = r.json()
        r.close()
        print("[API] Health OK →", data)
        return True
    except Exception as e:
        print("[API] Health FAILED:", e)
        return False


def send_sensor_data(payload):
    """
    POST /sensor-data
    Sends a dict of sensor readings to the backend.
    Returns True on success, False on failure.
    """
    try:
        url  = _get_base() + "/sensor-data"
        body = ujson.dumps(payload).encode("utf-8")
        r    = urequests.post(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            timeout=2
        )
        r.close()
        print("[API] Sensor data sent ✓")
        return True
    except Exception as e:
        print("[API] Sensor post FAILED:", e)
        return False


def get_pending_commands():
    """
    GET /command/pending
    Returns dict with 'commands' list.
    Returns {'commands': []} on failure — safe default.
    """
    try:
        url = _get_base() + "/command/pending"
        r   = urequests.get(url, timeout=2)
        data = r.json()
        r.close()
        if data.get("commands"):
            print("[API] Commands received:", data["commands"])
        return data
    except Exception as e:
        print("[API] Command poll FAILED:", e)
        return {"commands": []}
