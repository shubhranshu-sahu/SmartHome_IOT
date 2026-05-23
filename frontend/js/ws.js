// ============================================
// ws.js — WebSocket connection + auto-reconnect
//
// Replaces HTTP polling. Single persistent connection
// delivers all sensor updates and state changes.
// Falls back to HTTP poll if WS unavailable.
// ============================================

let _ws             = null;
let _reconnectTimer = null;
let _onMsg          = null;   // set by main.js
let _onOpen         = null;
let _onClose        = null;

/** Derive ws:// or wss:// from the API_BASE http(s):// URL */
function _wsUrl() {
    return CONFIG.API_BASE.replace(/^http/, 'ws') + '/ws';
}

/** Called by main.js to start the connection */
function wsConnect() {
    if (_ws && (_ws.readyState === WebSocket.OPEN ||
                _ws.readyState === WebSocket.CONNECTING)) return;

    console.log('[WS] Connecting to', _wsUrl());
    _ws = new WebSocket(_wsUrl());

    _ws.onopen = () => {
        console.log('[WS] Connected');
        clearTimeout(_reconnectTimer);
        if (_onOpen) _onOpen();
    };

    _ws.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);
            if (_onMsg) _onMsg(msg);
        } catch (e) {
            console.warn('[WS] Bad message:', event.data);
        }
    };

    _ws.onclose = () => {
        console.warn('[WS] Disconnected — retry in', CONFIG.WS_RECONNECT_MS, 'ms');
        if (_onClose) _onClose();
        _scheduleReconnect();
    };

    _ws.onerror = () => {
        // onerror always followed by onclose, so just log
        console.warn('[WS] Error');
    };
}

/** Force an immediate reconnect (called by the Reconnect button) */
function wsReconnect() {
    clearTimeout(_reconnectTimer);
    if (_ws) { try { _ws.close(); } catch (_) {} _ws = null; }
    wsConnect();
}

function _scheduleReconnect() {
    clearTimeout(_reconnectTimer);
    _reconnectTimer = setTimeout(wsConnect, CONFIG.WS_RECONNECT_MS);
}

/** Register callbacks from main.js */
function wsOnMessage(fn)    { _onMsg   = fn; }
function wsOnConnected(fn)  { _onOpen  = fn; }
function wsOnDisconnected(fn){ _onClose = fn; }
