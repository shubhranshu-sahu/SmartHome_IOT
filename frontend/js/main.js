// ============================================
// main.js — Init, WebSocket orchestration, UI
// ============================================

let _radar = null;
let _wsOnline = false;
let _esp32Online = false;      // Separate from WS status
let _lastUpdate = null;
let _fallbackInterval = null;

document.addEventListener('DOMContentLoaded', () => {
    _radar = new RadarDisplay('radar-canvas');

    // Register WS callbacks
    wsOnConnected(() => {
        _wsOnline = true;
        _setOnlineUI(true);
        _hideOffline();
        if (_fallbackInterval) { clearInterval(_fallbackInterval); _fallbackInterval = null; }
    });

    wsOnDisconnected(() => {
        _wsOnline = false;
        _setOnlineUI(false);
        _showOffline();
        // ESP32 status unknown while WS is down — treat as offline for safety
        _setEsp32UI(false);
        if (!_fallbackInterval) {
            _fallbackInterval = setInterval(_httpFallbackPoll, 2000);
        }
    });

    wsOnMessage(_handleWsMessage);
    wsConnect();

    setInterval(_tickClock, 1000);
    setInterval(_tickLastSeen, 1000);
    _tickClock();
});

// ---- WebSocket message handler ---- //

function _handleWsMessage(msg) {
    const d = msg.data;

    switch (msg.type) {
        case 'ping':
            break;

        case 'init':
            // Full state on first connect — includes esp32_online
            if (d.sensor && Object.keys(d.sensor).length) {
                updateSensorDisplay({ ...d.sensor, leds: d.leds, protect_mode: d.protect_mode });
            }
            updateLedUI(d.leds);
            updateProtectModeUI(d.protect_mode);
            _setEsp32UI(d.esp32_online === true);
            break;

        case 'sensor_update':
            // ESP32 POST arrived — radar + sensors
            if (d.sweep && d.sweep.length > 0) {
                _radar.processSweep(d.sweep);
            }
            updateSensorDisplay(d);
            _lastUpdate = Date.now();
            _setEsp32UI(true);   // Receiving data = definitely online
            break;

        case 'state_update':
            // Command echoed back
            updateLedUI(d.leds);
            if (d.protect_mode !== undefined) updateProtectModeUI(d.protect_mode);
            if (d.esp32_online !== undefined) _setEsp32UI(d.esp32_online);
            break;

        case 'esp32_status':
            // Watchdog fired (offline) or ESP32 reconnected (online)
            _setEsp32UI(d.online);
            if (!d.online) {
                // Clear stale sensor readings
                updateSensorDisplay({ angle: null, distance: null, flame: false, gate: false });
            }
            break;
    }
}

// ---- ESP32 status UI ---- //

function _setEsp32UI(online) {
    _esp32Online = online;

    const dot  = document.getElementById('esp32-dot');
    const text = document.getElementById('esp32-text');
    if (dot)  dot.className  = online ? 'conn-dot online' : 'conn-dot offline';
    if (text) text.textContent = online ? 'ESP32 Online' : 'ESP32 Offline';

    // Grey out the controls that need ESP32
    const controls = document.getElementById('esp32-controls');
    if (controls) {
        controls.style.opacity       = online ? '1' : '0.45';
        controls.style.pointerEvents = online ? '' : 'none';
    }

    // Show/hide the offline warning inside controls section
    const warn = document.getElementById('esp32-offline-warn');
    if (warn) warn.classList.toggle('d-none', online);
}

// ---- HTTP fallback (when WS is down) ---- //

async function _httpFallbackPoll() {
    try {
        const data = await getLatestSensor();
        if (data && data.angle !== undefined) {
            updateSensorDisplay(data);
            _lastUpdate = Date.now();
        }
    } catch { /* silent — WS reconnect handles recovery */ }
}

// ---- Backend connection UI ---- //

function _setOnlineUI(ok) {
    const dot  = document.getElementById('conn-dot');
    const text = document.getElementById('conn-text');
    if (dot)  dot.className  = ok ? 'conn-dot online' : 'conn-dot offline';
    if (text) text.textContent = ok ? 'Backend Online' : 'Backend Offline';
}

function _showOffline() {
    document.getElementById('offline-overlay')?.classList.remove('d-none');
}

function _hideOffline() {
    document.getElementById('offline-overlay')?.classList.add('d-none');
}

function reconnect() { wsReconnect(); }

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
