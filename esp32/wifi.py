# =============================================
# wifi.py  —  Connect to saved WiFi
# =============================================

import network
import ujson
import time
from hardware import set_mode, update_led
from hardware import MODE_DISCONNECTED, MODE_CONNECTED
from config   import DEFAULT_WIFI_SSID, DEFAULT_WIFI_PASSWORD, DEFAULT_API_BASE

CONFIG_FILE = "config.json"

# One shared station interface
_wlan = network.WLAN(network.STA_IF)

# ---- Config helpers ----

def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            return ujson.load(f)
    except:
        return None

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        ujson.dump(data, f)

def _ensure_config():
    """Return config dict, creating default file if missing."""
    cfg = load_config()
    if cfg is None:
        cfg = {
            "wifi_ssid":     DEFAULT_WIFI_SSID,
            "wifi_password": DEFAULT_WIFI_PASSWORD,
            "api_base":      DEFAULT_API_BASE
        }
        save_config(cfg)
        print("Created default config.json")
    return cfg

# ---- Connection ----

def connect_wifi():
    """
    Try to connect with saved credentials.
    Returns True on success, False on failure.
    LED blinks slowly (500 ms) while trying.
    LED goes solid ON when connected.
    """
    cfg  = _ensure_config()
    ssid = cfg["wifi_ssid"]
    pwd  = cfg["wifi_password"]

    _wlan.active(True)

    # Guard: already connected (e.g. retained from previous cycle)
    if _wlan.isconnected():
        set_mode(MODE_CONNECTED)
        print("Already connected! IP:", _wlan.ifconfig()[0])
        return True

    # Clean disconnect before fresh attempt
    try:
        _wlan.disconnect()
    except:
        pass

    _wlan.connect(ssid, pwd)

    set_mode(MODE_DISCONNECTED)
    print("Connecting to:", ssid)

    for _ in range(40):           # 40 × 250 ms = 10 s timeout
        update_led()
        if _wlan.isconnected():
            set_mode(MODE_CONNECTED)
            print("Connected! IP:", _wlan.ifconfig()[0])
            return True
        time.sleep_ms(250)

    print("WiFi failed")
    return False

# ---- Status ----

def wifi_is_connected():
    return _wlan.isconnected()