// ============================================
// stats.js — Analytics page logic
//
// Fetches /stats/today and /stats/recent from FastAPI.
// Renders LED bars, battery table, 7-day chart,
// flame events, gate events.
// Auto-refreshes every 30 seconds.
// ============================================

const ROOMS = ['room1', 'room2', 'room3', 'room4'];
const ROOM_LABELS = { room1: 'Room 1', room2: 'Room 2', room3: 'Room 3', room4: 'Room 4' };
const ROOM_COLORS = ['#ffa502', '#54a0ff', '#00ff88', '#a78bfa'];

let _chart7day = null;

// ============================================================
// INIT
// ============================================================

document.addEventListener('DOMContentLoaded', async () => {
    // Set date label
    document.getElementById('stat-date').textContent =
        new Date().toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });

    await refreshAll();
    setInterval(refreshAll, 30000);   // Refresh every 30s
});

async function refreshAll() {
    try {
        const [today, recent] = await Promise.all([
            _fetch('/stats/today'),
            _fetch('/stats/recent?days=7'),
        ]);
        _renderToday(today);
        _renderRecent(recent);
        document.getElementById('last-refresh').textContent =
            'Updated ' + new Date().toLocaleTimeString();
    } catch (e) {
        console.error('[Stats] Fetch failed:', e);
        document.getElementById('last-refresh').textContent = 'Refresh failed';
    }
}

async function _fetch(path) {
    const r = await fetch(CONFIG.API_BASE + path);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
}

// ============================================================
// TODAY'S STATS
// ============================================================

function _renderToday(data) {
    // DB offline banner
    if (!data.db_connected) {
        document.getElementById('db-offline-banner').classList.remove('d-none');
    } else {
        document.getElementById('db-offline-banner').classList.add('d-none');
    }

    // ---- Summary cards ----
    const totalOnMin = ROOMS.reduce((s, r) => s + (data.led?.[r]?.on_min || 0), 0);
    document.getElementById('card-led-hours').textContent =
        totalOnMin >= 60
            ? `${(totalOnMin / 60).toFixed(1)}h`
            : `${Math.round(totalOnMin)}m`;

    document.getElementById('card-battery').textContent =
        `${data.battery?.total_mah ?? '—'}`;

    document.getElementById('card-flames').textContent =
        data.flame_events?.length ?? 0;

    document.getElementById('card-gate').textContent =
        data.gate_opens ?? 0;

    // ---- LED bars ----
    const maxMin = Math.max(1, ...ROOMS.map(r => data.led?.[r]?.on_min || 0));
    const barsEl = document.getElementById('led-bars');
    barsEl.innerHTML = ROOMS.map((r, i) => {
        const info   = data.led?.[r] || { on_min: 0, sessions: 0 };
        const pct    = Math.min(100, (info.on_min / maxMin) * 100);
        const timeStr = info.on_min >= 60
            ? `${(info.on_min / 60).toFixed(1)}h`
            : `${Math.round(info.on_min)}m`;
        const hasTime = info.on_min > 0;

        return `
        <div class="led-bar-row">
            <div class="led-bar-label" style="color:${ROOM_COLORS[i]}">
                <i class="bi bi-lightbulb-fill"></i>${ROOM_LABELS[r]}
            </div>
            <div class="led-bar-track">
                <div class="led-bar-fill" style="width:${pct}%;background:${ROOM_COLORS[i]}"></div>
            </div>
            <div class="led-bar-time ${hasTime ? 'has-time' : ''}"
                 style="${hasTime ? `color:${ROOM_COLORS[i]}` : ''}">
                ${hasTime ? timeStr : '0m'}
            </div>
        </div>`;
    }).join('');

    // ---- Battery breakdown ----
    const b = data.battery || {};
    document.getElementById('bat-led').textContent   = `${(b.led_mah   || 0).toFixed(1)} mAh`;
    document.getElementById('bat-mcu').textContent   = `${(b.mcu_mah   || 0).toFixed(1)} mAh`;
    document.getElementById('bat-servo').textContent = `${(b.servo_mah || 0).toFixed(1)} mAh`;
    document.getElementById('bat-total').textContent = `${(b.total_mah || 0).toFixed(1)} mAh`;

    // ---- Flame events ----
    _renderFlames(data.flame_events || []);

    // ---- Gate events ----
    _renderGates(data.gate_events || []);
}

function _renderFlames(events) {
    const list  = document.getElementById('flame-list');
    const badge = document.getElementById('badge-flames');
    badge.textContent = events.length;

    if (events.length === 0) {
        list.innerHTML = '<div class="event-empty">No flame events today 🛡️</div>';
        return;
    }

    list.innerHTML = events.map(e => {
        const t   = new Date(e.detected_at).toLocaleTimeString();
        const dur = e.duration_sec != null ? `${e.duration_sec}s` : 'Active';
        return `
        <div class="event-item">
            <span class="event-icon">🔥</span>
            <div class="event-body">
                <div class="event-time">${t}</div>
                <div class="event-desc">Flame detected</div>
            </div>
            <span class="event-dur dur-flame">${dur}</span>
        </div>`;
    }).join('');
}

function _renderGates(events) {
    const list  = document.getElementById('gate-list');
    const badge = document.getElementById('badge-gates');
    badge.textContent = events.length;

    if (events.length === 0) {
        list.innerHTML = '<div class="event-empty">No gate events today</div>';
        return;
    }

    list.innerHTML = events.map(e => {
        const t      = new Date(e.timestamp).toLocaleTimeString();
        const isOpen = e.state === 'open';
        return `
        <div class="event-item">
            <span class="event-icon">${isOpen ? '🚪' : '🔒'}</span>
            <div class="event-body">
                <div class="event-time">${t}</div>
                <div class="event-desc">Gate ${e.state}</div>
            </div>
            <span class="event-dur ${isOpen ? 'dur-open' : 'dur-closed'}">
                ${isOpen ? 'OPEN' : 'CLOSED'}
            </span>
        </div>`;
    }).join('');
}

// ============================================================
// 7-DAY CHART
// ============================================================

function _renderRecent(data) {
    const days = data.days || [];

    const labels = days.map(d => {
        const dt = new Date(d.date + 'T12:00:00Z');
        return dt.toLocaleDateString(undefined, { weekday: 'short', month: 'numeric', day: 'numeric' });
    });

    const datasets = ROOMS.map((r, i) => ({
        label:           ROOM_LABELS[r],
        data:            days.map(d => +(d.rooms?.[r]?.on_min || 0).toFixed(1)),
        backgroundColor: hexToRgba(ROOM_COLORS[i], 0.7),
        borderColor:     ROOM_COLORS[i],
        borderWidth:     1,
        borderRadius:    4,
    }));

    const ctx = document.getElementById('chart-7day').getContext('2d');

    if (_chart7day) {
        _chart7day.data.labels   = labels;
        _chart7day.data.datasets = datasets;
        _chart7day.update('none');
        return;
    }

    _chart7day = new Chart(ctx, {
        type: 'bar',
        data: { labels, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: {
                    labels: { color: 'rgba(200,214,232,0.7)', font: { size: 11 }, boxWidth: 12 }
                },
                tooltip: {
                    backgroundColor: 'rgba(7,13,26,0.92)',
                    borderColor:     'rgba(255,255,255,0.08)',
                    borderWidth:     1,
                    titleColor:      '#c8d6e8',
                    bodyColor:       'rgba(200,214,232,0.75)',
                    callbacks: {
                        label: ctx => ` ${ctx.dataset.label}: ${ctx.parsed.y}m`
                    }
                }
            },
            scales: {
                x: {
                    stacked: false,
                    ticks:   { color: 'rgba(200,214,232,0.5)', font: { size: 10 } },
                    grid:    { color: 'rgba(255,255,255,0.04)' }
                },
                y: {
                    stacked: false,
                    title:   { display: true, text: 'Minutes on', color: 'rgba(200,214,232,0.4)', font: { size: 10 } },
                    ticks:   { color: 'rgba(200,214,232,0.5)', font: { size: 10 } },
                    grid:    { color: 'rgba(255,255,255,0.04)' },
                    beginAtZero: true,
                }
            }
        }
    });
}

function hexToRgba(hex, alpha) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r},${g},${b},${alpha})`;
}
