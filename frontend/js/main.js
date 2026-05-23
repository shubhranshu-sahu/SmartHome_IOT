// ============================================
// main.js — Init, WebSocket orchestration, UI
// ============================================

let _radar      = null;
let _wsOnline   = false;
let _lastUpdate = null;
let _fallbackInterval = null;

document.addEventListener('DOMContentLoaded', () => {
    _radar = new RadarDisplay('radar-canvas');

    // Register WS callbacks
    wsOnConnected(() => {
        _wsOnline = true;
        _setOnlineUI(true);
        _hideOffline();
        // Stop HTTP fallback if it was running
        if (_fallbackInterval) { clearInterval(_fallbackInterval); _fallbackInterval = null; }
    });

    wsOnDisconnected(() => {
        _wsOnline = false;
        _setOnlineUI(false);
        _showOffline();
        // Start HTTP fallback polling while WS is down
        if (!_fallbackInterval) {
            _fallbackInterval = setInterval(_httpFallbackPoll, 2000);
        }
    });

    wsOnMessage(_handleWsMessage);

    // Connect WebSocket
    wsConnect();

    // UI clocks
    setInterval(_tickClock,    1000);
    setInterval(_tickLastSeen, 1000);
    _tickClock();
});

// ---- WebSocket message handler ---- //

function _handleWsMessage(msg) {
    const d = msg.data;

    switch (msg.type) {
        case 'init':
            // Full state on first connect
            if (d.sensor && Object.keys(d.sensor).length) {
                _radar.update(d.sensor.angle, d.sensor.distance);
                updateSensorDisplay({ ...d.sensor, leds: d.leds, protect_mode: d.protect_mode });
            }
            updateLedUI(d.leds);
            updateProtectModeUI(d.protect_mode);
            break;

        case 'sensor_update':
            // ESP32 POST arrived — radar + all sensor data
            _radar.update(d.angle, d.distance);
            updateSensorDisplay(d);
            _lastUpdate = Date.now();
            break;

        case 'state_update':
            // LED or protect_mode command was received by backend — reflect immediately
            updateLedUI(d.leds);
            if (d.protect_mode !== undefined) updateProtectModeUI(d.protect_mode);
            break;
    }
}

// ---- HTTP fallback (when WS is down) ---- //

async function _httpFallbackPoll() {
    try {
        const data = await getLatestSensor();
        if (data && data.angle !== undefined) {
            _radar.update(data.angle, data.distance);
            updateSensorDisplay(data);
            _lastUpdate = Date.now();
        }
    } catch { /* silent — WS reconnect handles recovery */ }
}

// ---- Connection UI ---- //

function _setOnlineUI(ok) {
    const dot  = document.getElementById('conn-dot');
    const text = document.getElementById('conn-text');
    if (dot)  dot.className  = ok ? 'conn-dot online' : 'conn-dot offline';
    if (text) text.textContent = ok ? 'Connected' : 'Offline';
}

function _showOffline() {
    document.getElementById('offline-overlay')?.classList.remove('d-none');
}

function _hideOffline() {
    document.getElementById('offline-overlay')?.classList.add('d-none');
}

/** Called by the Reconnect button */
function reconnect() {
    wsReconnect();
}

// ---- Clocks ---- //

function _tickClock() {
    const el = document.getElementById('clock');
    if (el) el.textContent = new Date().toLocaleTimeString();
}

function _tickLastSeen() {
    const el = document.getElementById('last-update');
    if (!el || !_lastUpdate) return;
    const s = Math.round((Date.now() - _lastUpdate) / 1000);
    el.textContent = s < 2 ? 'Live' : `${s}s ago`;
}
