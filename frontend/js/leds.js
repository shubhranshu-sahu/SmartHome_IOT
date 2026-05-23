// ============================================
// leds.js — Room LED state & control
// ============================================

// Local mirror of backend LED state
const _led = { room1: 0, room2: 0, room3: 0, room4: 0 };

/** Called by main.js on every WS message that includes leds */
function updateLedUI(states) {
    if (!states) return;
    Object.assign(_led, states);
    for (let r = 1; r <= 4; r++) {
        const key    = `room${r}`;
        const toggle = document.getElementById(`toggle-r${r}`);
        const tile   = document.getElementById(`tile-r${r}`);
        // Programmatic .checked change does NOT fire onchange — no loop risk
        if (toggle) toggle.checked = states[key] === 1;
        if (tile)   tile.classList.toggle('led-on', states[key] === 1);
    }
}

/** User flips a room toggle — optimistic update + backend command */
async function toggleRoom(room) {
    const key      = `room${room}`;
    const newState = _led[key] === 1 ? 0 : 1;
    _led[key]      = newState;

    // Instant local update (WS broadcast from backend confirms within ~50ms)
    const tile = document.getElementById(`tile-r${room}`);
    if (tile) tile.classList.toggle('led-on', newState === 1);

    try {
        await sendCommand({ action: 'set_led', room, state: newState });
    } catch (e) {
        console.warn('[LEDs] Command failed:', e);
        // Revert optimistic update on error
        _led[key] = newState === 1 ? 0 : 1;
        if (tile) tile.classList.toggle('led-on', _led[key] === 1);
    }
}

/** All On / All Off */
async function setAllLeds(state) {
    for (let r = 1; r <= 4; r++) {
        _led[`room${r}`] = state;
        const toggle = document.getElementById(`toggle-r${r}`);
        const tile   = document.getElementById(`tile-r${r}`);
        if (toggle) toggle.checked = state === 1;
        if (tile)   tile.classList.toggle('led-on', state === 1);
    }
    try {
        await sendCommand({ action: 'set_all', state });
    } catch (e) {
        console.warn('[LEDs] set_all failed:', e);
    }
}
