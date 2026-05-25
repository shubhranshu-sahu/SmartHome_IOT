# =============================================
# config.py  —  All constants in one place
# =============================================

# --- WiFi fallback (used if config.json missing) ---
DEFAULT_WIFI_SSID     = "test"
DEFAULT_WIFI_PASSWORD = "12345678"
DEFAULT_API_BASE      = "http://192.168.1.5:8000"

# --- Captive-portal hotspot ---
AP_SSID     = "SmartHome-Setup"
AP_PASSWORD = "12345678"

# --- Onboard status LED ---
WIFI_LED_PIN = 2          # D2 on most ESP32 dev boards

# --- Room LEDs ---
LED_PINS = [16, 17, 18, 19]   # Room 1-4

# --- Radar ---
SERVO_PIN = 25
TRIG_PIN  = 32
ECHO_PIN  = 27

# --- Buzzer ---
BUZZER_PIN = 26

# --- Optional sensors ---
FLAME_PIN = 34
IR_PIN    = 21

# --- API Timing ---
# Health ping: 250s  (only needed to keep Render.com free tier awake)
# Sensor POST: 400ms  (carries full radar buffer — ~12-15 measurements per POST)
# Command poll: 300ms  (runs in its own thread, independent of sensor POST)
API_HEALTH_INTERVAL_MS   = 250000
SENSOR_POST_INTERVAL_MS  =    400
COMMAND_POLL_INTERVAL_MS =    300