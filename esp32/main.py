# =============================================
# main.py  —  ESP32 entry point (WiFi phase)
# =============================================

from wifi         import connect_wifi, wifi_is_connected
from wifi_manager import start_portal
from hardware     import set_mode, update_led
from hardware     import MODE_CONNECTED, MODE_DISCONNECTED

import time

# ---- 1. Initial connect ----
connected = connect_wifi()

if not connected:
    print("Initial connect failed — starting portal")
    start_portal()          # Blocks here until user saves config + reboot

# ---- 2. WiFi connected — monitor loop ----
print("System Running")

_fail_count = 0
_MAX_FAILS  = 2            # After 2 failed reconnects → portal

while True:

    update_led()

    if wifi_is_connected():
        set_mode(MODE_CONNECTED)
        _fail_count = 0
        time.sleep_ms(100)

    else:
        # WiFi dropped
        _fail_count += 1
        print("WiFi lost — reconnect attempt", _fail_count, "of", _MAX_FAILS)
        set_mode(MODE_DISCONNECTED)

        if connect_wifi():
            print("Reconnected!")
            _fail_count = 0

        elif _fail_count >= _MAX_FAILS:
            print("Cannot reconnect — starting portal")
            start_portal()  # Blocks until reboot