// ============================================
// sensors.js — Sensor display + protect mode
// ============================================

let _protectMode = false;

function updateSensorDisplay(data) {
    _setAngle(data.angle);
    _setDistance(data.distance);
    _setFlame(data.flame);
    _setGate(data.gate);
    if (data.leds)         updateLedUI(data.leds);
    if (data.protect_mode !== undefined) updateProtectModeUI(data.protect_mode);
}

// ---- Individual field updates ---- //

function _setAngle(angle) {
    const el = document.getElementById('val-angle');
    if (el) el.textContent = (angle != null) ? `${angle}°` : '--°';
}

function _setDistance(dist) {
    const el = document.getElementById('val-distance');
    if (!el) return;
    if (dist != null) {
        el.textContent   = `${dist} cm`;
        el.style.opacity = '1';
    } else {
        el.textContent   = 'Clear';
        el.style.opacity = '0.4';
    }
}

function _setFlame(flame) {
    const el   = document.getElementById('val-flame');
    const card = document.getElementById('card-flame');
    const icon = document.getElementById('icon-flame');
    if (!el) return;

    if (flame) {
        el.textContent = 'DANGER!';
        el.style.color = 'var(--danger)';
        if (icon) icon.textContent = '🔥';
        card?.classList.add('flame-danger');
    } else {
        el.textContent = 'SAFE';
        el.style.color = '';
        if (icon) icon.textContent = '🛡️';
        card?.classList.remove('flame-danger');
    }
}

function _setGate(gate) {
    const el   = document.getElementById('val-gate');
    const card = document.getElementById('card-gate');
    const icon = document.getElementById('icon-gate');
    if (!el) return;

    if (gate) {
        el.textContent = 'CLOSED';
        el.style.color = 'var(--warning)';
        if (icon) icon.textContent = '🔒';
        card?.classList.add('gate-closed');
    } else {
        el.textContent = 'OPEN';
        el.style.color = 'var(--info)';
        if (icon) icon.textContent = '🚪';
        card?.classList.remove('gate-closed');
    }
}

// ---- Protect Mode ---- //

function updateProtectModeUI(enabled) {
    _protectMode = enabled;
    const btn  = document.getElementById('btn-protect');
    const icon = document.getElementById('icon-protect');
    const text = document.getElementById('text-protect');
    const card = document.getElementById('card-protect');
    if (!btn) return;

    if (enabled) {
        btn.classList.add('protect-on');
        card?.classList.add('protect-active');
        if (icon) icon.className = 'bi bi-shield-fill-check';
        if (text) text.textContent = 'ACTIVE';
    } else {
        btn.classList.remove('protect-on');
        card?.classList.remove('protect-active');
        if (icon) icon.className = 'bi bi-shield-slash-fill';
        if (text) text.textContent = 'OFF';
    }
}

async function toggleProtectMode() {
    const newState = !_protectMode;
    updateProtectModeUI(newState);   // Optimistic
    try {
        await sendCommand({ action: 'protect_mode', state: newState });
    } catch (e) {
        console.warn('[Protect] Failed:', e);
        updateProtectModeUI(!newState);  // Revert
    }
}

// ---- Manual Buzzer ---- //

async function triggerBuzzer() {
    const btn = document.getElementById('btn-buzzer');
    if (btn) {
        btn.classList.add('buzzing');
        setTimeout(() => btn.classList.remove('buzzing'), 400);
    }
    try {
        await sendCommand({ action: 'beep', duration_ms: 500 });
    } catch (e) {
        console.warn('[Buzzer] Failed:', e);
    }
}
