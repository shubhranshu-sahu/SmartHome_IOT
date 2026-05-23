// ============================================
// config.js — All frontend constants
//
// DEPLOYMENT: Change API_BASE to your Render URL.
// WS URL is auto-derived (http→ws, https→wss).
// ============================================

const CONFIG = Object.freeze({
    // Local development
    API_BASE: 'https://smarthome-iot-16ks.onrender.com',
    // API_BASE: 'http://192.168.1.5:8000',

    // Render deployment (uncomment + change when deploying):
    // API_BASE: 'https://your-app.onrender.com',

    // Radar geometry (must match radar.py constants)
    MAX_DISTANCE_CM: 150,
    MIN_ANGLE: 15,
    MAX_ANGLE: 165,

    // WebSocket reconnect interval
    WS_RECONNECT_MS: 4000,
});
