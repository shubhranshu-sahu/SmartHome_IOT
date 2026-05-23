// ============================================
// api.js — HTTP calls (commands only)
//
// All real-time sensor data arrives via WebSocket.
// HTTP is only used for sending commands (rare)
// and as a fallback health check.
// ============================================

async function sendCommand(cmd) {
    const res = await fetch(`${CONFIG.API_BASE}/command`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(cmd),
        signal:  AbortSignal.timeout(4000)
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
}

/** HTTP fallback — poll sensor data if WS unavailable */
async function getLatestSensor() {
    const res = await fetch(`${CONFIG.API_BASE}/sensor-data/latest`, {
        signal: AbortSignal.timeout(3000)
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
}

async function getLedStats() {
    const res = await fetch(`${CONFIG.API_BASE}/stats/leds`, {
        signal: AbortSignal.timeout(3000)
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
}
