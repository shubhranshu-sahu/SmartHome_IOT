// ============================================
// stats.js — Analytics page logic
//
// Fetches /stats/today + /stats/recent every 5s.
// Renders:
//   - Room ring cards (SVG circle progress, % of day, sessions, avg)
//   - Doughnut chart for today's room distribution
//   - Stacked 7-day bar chart
//   - Flame + gate event lists
// ============================================

const ROOMS = ['room1', 'room2', 'room3', 'room4'];
const ROOM_LABELS = { room1: 'Room 1', room2: 'Room 2', room3: 'Room 3', room4: 'Room 4' };
const ROOM_COLORS = ['#ffa502', '#54a0ff', '#00ff88', '#a78bfa'];

// SVG ring geometry
const RING_R   = 24;
const RING_CIRC = 2 * Math.PI * RING_R;   // ≈ 150.8

let _chart7day = null;
let _chartDonut = null;

// ============================================================
// INIT
// ============================================================

document.addEventListener('DOMContentLoaded', async () => {
    document.getElementById('stat-date').textContent =
        new Date().toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });

    await refreshAll();
    // 5s polling — polling is the correct choice for aggregate data that
    // changes infrequently (a few times per hour at most)
    setInterval(refreshAll, 5000);
});

async function refreshAll() {
    const lastEl = document.getElementById('last-refresh');
    if (lastEl) { lastEl.textContent = 'Refreshing…'; lastEl.style.color = 'var(--accent)'; }

    try {
        const [today, recent] = await Promise.all([
            _fetch('/stats/today'),
            _fetch('/stats/recent?days=7'),
        ]);
        _renderToday(today);
        _renderRecent(recent);
        const t = new Date().toLocaleTimeString();
        if (lastEl) { lastEl.textContent = `Updated ${t}`; lastEl.style.color = ''; }
    } catch (e) {
        console.error('[Stats] Fetch failed:', e);
        if (lastEl) { lastEl.textContent = 'Refresh failed'; lastEl.style.color = 'var(--danger)'; }
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
    if (!data.db_connected) {
        document.getElementById('db-offline-banner').classList.remove('d-none');
    } else {
        document.getElementById('db-offline-banner').classList.add('d-none');
    }

    const hoursToday = data.hours_today || 24;

    // ---- Summary cards ----
    const totalOnMin = ROOMS.reduce((s, r) => s + (data.led?.[r]?.on_min || 0), 0);
    document.getElementById('card-led-hours').textContent =
        totalOnMin >= 60 ? `${(totalOnMin / 60).toFixed(1)}h` : `${Math.round(totalOnMin)}m`;

    const energyWh = data.energy?.led_wh ?? 0;
    document.getElementById('card-energy').textContent = energyWh.toFixed(3);

    document.getElementById('card-flames').textContent = data.flame_events?.length ?? 0;
    document.getElementById('card-gate').textContent   = data.gate_opens ?? 0;

    // Hours today label
    const htEl = document.getElementById('hours-today-label');
    if (htEl) htEl.textContent = `${hoursToday.toFixed(1)}h elapsed`;

    // ---- Room ring cards ----
    _renderRooms(data.led || {}, hoursToday);

    // ---- Doughnut ----
    _renderDoughnut(data.led || {}, totalOnMin);

    // ---- Energy table ----
    _renderEnergy(data.led || {}, data.energy || {});

    // ---- Events ----
    _renderFlames(data.flame_events || []);
    _renderGates(data.gate_events || []);
}

// ---- Room ring cards ----

function _renderRooms(led, hoursToday) {
    const el = document.getElementById('led-room-cards');
    el.innerHTML = ROOMS.map((r, i) => {
        const info = led[r] || { on_min: 0, sessions: 0, avg_session_min: 0, pct_of_day: 0 };
        const pct  = Math.min(100, info.pct_of_day || 0);
        const dash = (pct / 100) * RING_CIRC;
        const gap  = RING_CIRC - dash;
        const color = ROOM_COLORS[i];

        const timeStr = info.on_min >= 60
            ? `${Math.floor(info.on_min / 60)}h ${Math.round(info.on_min % 60)}m`
            : `${Math.round(info.on_min)}m`;

        const avgStr = info.avg_session_min >= 1
            ? (info.avg_session_min >= 60
                ? `avg ${(info.avg_session_min / 60).toFixed(1)}h`
                : `avg ${Math.round(info.avg_session_min)}m`)
            : '';

        return `
        <div class="room-stat-card">
          <div class="ring-wrap">
            <svg width="58" height="58" viewBox="0 0 58 58">
              <circle cx="29" cy="29" r="${RING_R}"
                fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="5"/>
              <circle cx="29" cy="29" r="${RING_R}"
                fill="none"
                stroke="${color}"
                stroke-width="5"
                stroke-linecap="round"
                stroke-dasharray="${dash.toFixed(1)} ${gap.toFixed(1)}"
                style="transition:stroke-dasharray 0.8s cubic-bezier(0.4,0,0.2,1)"
              />
            </svg>
            <div class="ring-pct" style="color:${color}">${pct.toFixed(0)}%</div>
          </div>
          <div class="room-details">
            <div class="room-name">${ROOM_LABELS[r]}</div>
            <div class="room-time" style="color:${color}">${timeStr}</div>
            <div class="room-meta">
              ${info.sessions} session${info.sessions !== 1 ? 's' : ''}
              ${avgStr ? ' · ' + avgStr : ''}
              · ${pct.toFixed(1)}% of day
            </div>
          </div>
          <div class="room-sessions" style="background:${hexToRgba(color,0.12)};color:${color};border:1px solid ${hexToRgba(color,0.3)}">
            ${info.sessions}x
          </div>
        </div>`;
    }).join('');
}

// ---- Doughnut ----

function _renderDoughnut(led, totalOnMin) {
    const vals   = ROOMS.map(r => +(led[r]?.on_min || 0).toFixed(1));
    const hasAny = vals.some(v => v > 0);

    const ctx = document.getElementById('chart-doughnut').getContext('2d');

    const donutData = {
        labels:   ROOMS.map((r, i) => ROOM_LABELS[r]),
        datasets: [{
            data:            hasAny ? vals : [1, 1, 1, 1],
            backgroundColor: hasAny
                ? ROOM_COLORS.map(c => hexToRgba(c, 0.8))
                : ['rgba(255,255,255,0.06)', 'rgba(255,255,255,0.04)',
                   'rgba(255,255,255,0.06)', 'rgba(255,255,255,0.04)'],
            borderColor:     hasAny ? ROOM_COLORS : Array(4).fill('rgba(255,255,255,0.06)'),
            borderWidth:     2,
            hoverOffset:     6,
        }]
    };

    document.getElementById('d-total-min').textContent =
        totalOnMin >= 60 ? `${(totalOnMin / 60).toFixed(1)}h` : `${Math.round(totalOnMin)}m`;

    if (_chartDonut) {
        _chartDonut.data = donutData;
        _chartDonut.update('none');
        return;
    }

    _chartDonut = new Chart(ctx, {
        type: 'doughnut',
        data: donutData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '68%',
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(7,13,26,0.92)',
                    borderColor:     'rgba(255,255,255,0.08)',
                    borderWidth:     1,
                    titleColor:      '#c8d6e8',
                    bodyColor:       'rgba(200,214,232,0.75)',
                    callbacks: {
                        label: ctx => {
                            const v = ctx.parsed;
                            return hasAny
                                ? ` ${ctx.label}: ${v >= 60 ? (v/60).toFixed(1)+'h' : Math.round(v)+'m'}`
                                : ' No data yet';
                        }
                    }
                }
            }
        }
    });
}

// ---- LED Energy table ----

function _renderEnergy(led, energy) {
    const rows = document.getElementById('energy-rows');
    rows.innerHTML = ROOMS.map((r, i) => {
        const wh = led[r]?.energy_wh ?? 0;
        const color = ROOM_COLORS[i];
        return `
        <div class="battery-row">
          <span class="bat-label">
            <span style="width:8px;height:8px;border-radius:50%;background:${color};display:inline-block;flex-shrink:0"></span>
            ${ROOM_LABELS[r]}
          </span>
          <span class="bat-val">${wh.toFixed(4)} Wh</span>
        </div>`;
    }).join('');

    document.getElementById('bat-total-wh').textContent =
        `${(energy.led_wh ?? 0).toFixed(3)} Wh`;
}

// ---- Events ----

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
          <span class="event-dur ${isOpen ? 'dur-open' : 'dur-closed'}">${isOpen ? 'OPEN' : 'CLOSED'}</span>
        </div>`;
    }).join('');
}

// ============================================================
// 7-DAY STACKED BAR CHART
// ============================================================

function _renderRecent(data) {
    const days = data.days || [];

    const labels = days.map(d => {
        const dt = new Date(d.date + 'T12:00:00Z');
        return dt.toLocaleDateString(undefined, { weekday: 'short', month: 'numeric', day: 'numeric' });
    });

    // Stacked bars: each room is a layer, total height = total LED usage that day
    const datasets = ROOMS.map((r, i) => ({
        label:           ROOM_LABELS[r],
        data:            days.map(d => +(d.rooms?.[r]?.on_min || 0).toFixed(1)),
        backgroundColor: hexToRgba(ROOM_COLORS[i], 0.75),
        borderColor:     ROOM_COLORS[i],
        borderWidth:     1,
        borderRadius:    i === ROOMS.length - 1 ? 4 : 0,  // round top of last (topmost) bar
        stack:           'led',
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
                    labels: { color: 'rgba(200,214,232,0.7)', font: { size: 11 }, boxWidth: 12, padding: 16 }
                },
                tooltip: {
                    backgroundColor: 'rgba(7,13,26,0.92)',
                    borderColor:     'rgba(255,255,255,0.08)',
                    borderWidth:     1,
                    titleColor:      '#c8d6e8',
                    bodyColor:       'rgba(200,214,232,0.75)',
                    callbacks: {
                        label: ctx => ` ${ctx.dataset.label}: ${ctx.parsed.y}m`,
                        footer: items => {
                            const total = items.reduce((s, i) => s + i.parsed.y, 0);
                            return `Total: ${total >= 60 ? (total/60).toFixed(1)+'h' : total+'m'}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    stacked: true,
                    ticks:   { color: 'rgba(200,214,232,0.5)', font: { size: 10 } },
                    grid:    { color: 'rgba(255,255,255,0.04)' }
                },
                y: {
                    stacked: true,
                    title:   { display: true, text: 'Minutes (stacked)', color: 'rgba(200,214,232,0.4)', font: { size: 10 } },
                    ticks:   { color: 'rgba(200,214,232,0.5)', font: { size: 10 } },
                    grid:    { color: 'rgba(255,255,255,0.04)' },
                    beginAtZero: true,
                }
            }
        }
    });
}

// ============================================================
// UTILS
// ============================================================

function hexToRgba(hex, alpha) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r},${g},${b},${alpha})`;
}
