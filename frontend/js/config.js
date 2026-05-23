// ============================================
// config.js — All frontend constants
//
// DEPLOYMENT: Change API_BASE to your Render URL.
// WS URL is auto-derived (http→ws, https→wss).
// ============================================

const CONFIG = Object.freeze({
    // Local development
    API_BASE: 'http://192.168.1.5:8000',

    // Render deployment (uncomment + change when deploying):
    // API_BASE: 'https://your-app.onrender.com',

    // Radar display settings
    MAX_DISTANCE_CM:  150,
    BLIP_LIFETIME_MS: 6000,
    MIN_ANGLE:        15,
    MAX_ANGLE:        165,
    SWEEP_SPEED_DEG_S: 200,

    // WebSocket reconnect interval
    WS_RECONNECT_MS:  4000,
});
