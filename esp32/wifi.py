import network
import ujson
import time

from hardware import *

CONFIG_FILE = "config.json"

wlan = network.WLAN(network.STA_IF)

# =====================================
# LOAD CONFIG
# =====================================

def load_config():

    try:

        with open(CONFIG_FILE, "r") as f:

            return ujson.load(f)

    except:

        return None

# =====================================
# SAVE CONFIG
# =====================================

def save_config(data):

    with open(CONFIG_FILE, "w") as f:

        ujson.dump(data, f)

# =====================================
# CONNECT WIFI
# =====================================

def connect_wifi():

    config = load_config()

    if not config:

        return False

    ssid = config["wifi_ssid"]
    password = config["wifi_password"]

    wlan.active(True)

    wlan.connect(ssid, password)

    set_mode(MODE_DISCONNECTED)

    print("Connecting WiFi...")

    timeout = 20

    while timeout > 0:

        update_led()

        if wlan.isconnected():

            print("Connected")
            print(wlan.ifconfig())

            set_mode(MODE_CONNECTED)

            return True

        time.sleep(0.1)

        timeout -= 1

    print("Connection Failed")

    return False

# =====================================
# CHECK STATUS
# =====================================

def wifi_connected():

    return wlan.isconnected()