import network
import socket
import machine
import ure

from hardware import *
from wifi import save_config

AP_NAME = "SmartHome-Setup"

AP_PASSWORD = "12345678"

def start_portal():

    set_mode(MODE_AP)

    ap = network.WLAN(network.AP_IF)

    ap.active(True)

    ap.config(
        essid=AP_NAME,
        password=AP_PASSWORD,
        authmode=network.AUTH_WPA_WPA2_PSK
    )

    print("AP Started")
    print("Connect to:", AP_NAME)
    print("Open: http://192.168.4.1")

    addr = socket.getaddrinfo(
        "0.0.0.0",
        80
    )[0][-1]

    s = socket.socket()

    s.bind(addr)

    s.listen(1)

    while True:

        update_led()

        try:

            client, addr = s.accept()

            request = client.recv(1024).decode()

            # =====================================
            # SAVE SETTINGS
            # =====================================

            if "/save?" in request:

                ssid = ure.search(
                    "ssid=([^&]*)",
                    request
                ).group(1)

                password = ure.search(
                    "password=([^&]*)",
                    request
                ).group(1)

                api = ure.search(
                    "api=([^ ]*)",
                    request
                ).group(1)

                data = {

                    "wifi_ssid": ssid,

                    "wifi_password": password,

                    "api_base": api
                }

                save_config(data)

                response = """HTTP/1.1 200 OK

Content-Type: text/html

<html>
<body>
<h2>Saved Successfully</h2>
<p>ESP32 restarting...</p>
</body>
</html>
"""

                client.send(response)

                client.close()

                time.sleep(2)

                machine.reset()

            # =====================================
            # CONFIG PAGE
            # =====================================

            else:

                html = """HTTP/1.1 200 OK

Content-Type: text/html

<html>

<head>
<title>ESP32 Setup</title>
</head>

<body style="font-family:sans-serif;padding:20px">

<h2>Smart Home Setup</h2>

<form action="/save">

<p>WiFi Name</p>
<input name="ssid">

<p>Password</p>
<input name="password" type="password">

<p>API Base URL</p>
<input name="api">

<br><br>

<button type="submit">
Save
</button>

</form>

</body>
</html>
"""

                client.send(html)

                client.close()

        except Exception as e:

            print("Portal Error:", e)