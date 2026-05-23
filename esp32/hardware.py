from machine import Pin
import time

wifi_led = Pin(2, Pin.OUT)

MODE_CONNECTED = 1
MODE_DISCONNECTED = 2
MODE_AP = 3

current_mode = MODE_DISCONNECTED

last_blink = 0
led_state = False

def set_mode(mode):

    global current_mode

    current_mode = mode

def update_led():

    global last_blink
    global led_state

    now = time.ticks_ms()

    # =====================================
    # CONNECTED
    # =====================================

    if current_mode == MODE_CONNECTED:

        wifi_led.on()

    # =====================================
    # DISCONNECTED
    # =====================================

    elif current_mode == MODE_DISCONNECTED:

        if time.ticks_diff(now, last_blink) > 500:

            led_state = not led_state

            wifi_led.value(led_state)

            last_blink = now

    # =====================================
    # AP MODE
    # =====================================

    elif current_mode == MODE_AP:

        if time.ticks_diff(now, last_blink) > 100:

            led_state = not led_state

            wifi_led.value(led_state)

            last_blink = now