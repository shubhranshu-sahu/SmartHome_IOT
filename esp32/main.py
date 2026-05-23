from wifi import *
from wifi_manager import *
from hardware import *

import time

# =====================================
# TRY WIFI
# =====================================

connected = connect_wifi()

# =====================================
# IF FAILED
# =====================================

if not connected:

    start_portal()

# =====================================
# MAIN LOOP
# =====================================

print("System Running")

while True:

    # Keep LED updated
    update_led()

    # Detect disconnect
    if not wifi_connected():

        print("WiFi Lost")

        set_mode(MODE_DISCONNECTED)

    else:

        set_mode(MODE_CONNECTED)

    time.sleep(0.1)