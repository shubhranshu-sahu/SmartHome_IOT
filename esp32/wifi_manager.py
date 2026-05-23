# =============================================
# wifi_manager.py  —  Captive portal (AP mode)
#
# Starts hotspot "SmartHome-Setup"
# Serves a mobile-friendly config page at
# http://192.168.4.1
# Saves WiFi + API URL  →  reboots ESP32
# =============================================

import network
import socket
import machine
import ure
import time

from hardware import set_mode, update_led, MODE_AP
from wifi     import save_config
from config   import AP_SSID, AP_PASSWORD

# ---- Helper: send proper HTTP response ----

def _send(client, html):
    """Build a valid HTTP/1.1 response and send all bytes."""
    body    = html.encode("utf-8")
    header  = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: text/html; charset=utf-8\r\n"
        "Connection: close\r\n"
        "Content-Length: " + str(len(body)) + "\r\n"
        "\r\n"
    ).encode("utf-8")
    client.sendall(header + body)

# ---- HTML pages ----

def _page_config():
    return (
        "<!doctype html><html lang='en'><head>"
        "<meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>SmartHome Setup</title>"
        "<style>"
        "*{box-sizing:border-box;margin:0;padding:0}"
        "body{font-family:sans-serif;background:#0f1117;color:#e0e0e0;"
        "display:flex;align-items:center;justify-content:center;min-height:100vh;padding:16px}"
        ".card{background:#1c1f2b;border-radius:12px;padding:28px 24px;width:100%;max-width:360px;"
        "box-shadow:0 4px 24px rgba(0,0,0,.5)}"
        "h2{color:#4fc3f7;margin-bottom:6px;font-size:1.3rem}"
        "p{color:#888;font-size:.85rem;margin-bottom:20px}"
        "label{display:block;font-size:.8rem;color:#aaa;margin-bottom:4px;margin-top:14px}"
        "input{width:100%;padding:10px 12px;border:1px solid #333;border-radius:8px;"
        "background:#0f1117;color:#e0e0e0;font-size:.95rem}"
        "input:focus{outline:none;border-color:#4fc3f7}"
        "button{margin-top:22px;width:100%;padding:12px;border:none;border-radius:8px;"
        "background:#4fc3f7;color:#000;font-weight:700;font-size:1rem}"
        "button:active{background:#0288d1}"
        "</style></head><body>"
        "<div class='card'>"
        "<h2>&#128736; SmartHome Setup</h2>"
        "<p>Connect your ESP32 to WiFi</p>"
        "<form action='/save'>"
        "<label>WiFi Name (SSID)</label>"
        "<input name='ssid' placeholder='Your WiFi name' autocomplete='off'>"
        "<label>WiFi Password</label>"
        "<input name='password' type='password' placeholder='Password'>"
        "<label>API Server URL</label>"
        "<input name='api' placeholder='http://192.168.x.x:8000' autocomplete='off'>"
        "<button type='submit'>Save &amp; Restart</button>"
        "</form></div></body></html>"
    )

def _page_saved():
    return (
        "<!doctype html><html><head>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<meta http-equiv='refresh' content='4'>"
        "<style>"
        "body{font-family:sans-serif;background:#0f1117;color:#e0e0e0;"
        "display:flex;align-items:center;justify-content:center;"
        "min-height:100vh;text-align:center;padding:16px}"
        "h2{color:#66bb6a;font-size:1.5rem}"
        "p{color:#aaa;margin-top:12px;font-size:.9rem}"
        "</style></head><body>"
        "<div>"
        "<h2>&#10003; Saved!</h2>"
        "<p>Credentials received.<br>ESP32 is restarting and connecting...</p>"
        "<p style='margin-top:20px;color:#555;font-size:.8rem'>You can close this page.</p>"
        "</div></body></html>"
    )

# ---- URL decoder ----

def _url_decode(s):
    """Decode %XX and + from URL-encoded query string."""
    s = s.replace("+", " ")
    out = []
    i = 0
    while i < len(s):
        if s[i] == "%" and i + 2 < len(s):
            try:
                out.append(chr(int(s[i+1:i+3], 16)))
                i += 3
                continue
            except:
                pass
        out.append(s[i])
        i += 1
    return "".join(out)

# ---- Portal entry point ----

def start_portal():

    set_mode(MODE_AP)

    # Disable STA — prevents radio interference, frees ~20KB RAM
    network.WLAN(network.STA_IF).active(False)

    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(
        essid=AP_SSID,
        password=AP_PASSWORD,
        authmode=network.AUTH_WPA_WPA2_PSK
    )

    print("[PORTAL] Hotspot started:", AP_SSID)
    print("[PORTAL] Password:", AP_PASSWORD)
    print("[PORTAL] Open browser: http://192.168.4.1")

    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(3)
    s.settimeout(0.1)    # Non-blocking — LED keeps blinking between accept() calls

    while True:
        update_led()

        try:
            client, client_addr = s.accept()
            print("[PORTAL] Client connected:", client_addr)
        except OSError:
            continue   # Timeout — loop, update LED

        try:
            # 2048 bytes — large enough for all browser GET headers
            raw = client.recv(2048).decode("utf-8", "ignore")

            # Log first line of request (the URL line)
            first_line = raw.split("\r\n")[0] if "\r\n" in raw else raw[:80]
            print("[PORTAL] Request:", first_line)

            if "/save?" in raw:

                # ---- Parse query params ----
                # Use [^& ]+ — MicroPython ure does not reliably support \s
                try:
                    m_ssid = ure.search(r"ssid=([^& ]+)", raw)
                    m_pwd  = ure.search(r"password=([^& ]+)", raw)
                    m_api  = ure.search(r"api=([^& ]+)", raw)

                    ssid = _url_decode(m_ssid.group(1)) if m_ssid else ""
                    pwd  = _url_decode(m_pwd.group(1))  if m_pwd  else ""
                    api  = _url_decode(m_api.group(1))  if m_api  else ""

                    print("[PORTAL] SSID received    :", ssid)
                    print("[PORTAL] Password received :", "*" * len(pwd), "(", len(pwd), "chars )")
                    print("[PORTAL] API URL received  :", api)

                except Exception as e:
                    print("[PORTAL] Parse error:", e)
                    ssid = pwd = api = ""

                if ssid:
                    print("[PORTAL] Saving config...")
                    save_config({
                        "wifi_ssid":     ssid,
                        "wifi_password": pwd,
                        "api_base":      api
                    })
                    print("[PORTAL] Config saved to config.json")

                    _send(client, _page_saved())
                    client.close()

                    print("[PORTAL] Rebooting in 2s...")
                    time.sleep_ms(2000)
                    machine.reset()

                else:
                    print("[PORTAL] Warning: SSID was empty — showing form again")
                    _send(client, _page_config())

            else:
                # Serve config page (also handles favicon.ico, etc.)
                print("[PORTAL] Serving config page")
                _send(client, _page_config())

        except Exception as e:
            print("[PORTAL] Handler error:", e)

        finally:
            try:
                client.close()
            except:
                pass