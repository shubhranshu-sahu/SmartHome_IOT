// ============================================
// radar.js — Radar canvas rendering
//
// HOW THE JUMPS ARE FIXED:
//
// Problem 1 — Direction guessing:
//   OLD: infer dir from angleDelta(first→last in batch)
//   FAILS: when batch spans a bounce (150→165→163), delta≈0
//   FIX: ESP32 sends "dir" field explicitly on every measurement
//
// Problem 2 — Bad extrapolation:
//   OLD: displayAngle += dir × speed × elapsed (linear)
//   FAILS: servo bounces at 15°/165° but linear extrapolation
//          just keeps going past the limit and freezes at clamp
//   FIX: ping-pong extrapolation — simulates the actual bounce
//
// Problem 3 — Sensor noise in plotted objects:
//   OLD: replace distance immediately on each new reading
//   FAILS: HC-SR04 gives ±2-5cm jitter → dot jumps around
//   FIX: exponential moving average per angle bucket
//
// DATA FORMAT per measurement:
//   {seq, angle, distance, dir, rel_ms}
//   dir: +1 (sweeping towards 165°) or -1 (sweeping towards 15°)
//   rel_ms: negative ms before POST was sent (older = more negative)
// ============================================

class RadarDisplay {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');

        // Sweep line state — seeded from first data, then extrapolated
        this.displayAngle = 90;
        this.sweepDir = 1;
        this.sweepSpeed = 55;       // deg/sec, calibrated each batch
        this.lastAngle = 90;        // last received angle (snap target)
        this.lastDir = 1;           // direction at last received angle
        this.lastUpdateTs = performance.now();

        // Scan history: angle bucket → {distance (EMA), ts}
        // Gives persistent environment picture between sweeps
        this.scanHistory = new Map();

        this.cx = 0; this.cy = 0; this.radius = 0;
        this.logW = 0; this.logH = 0;

        this._resize();
        new ResizeObserver(() => this._resize()).observe(this.canvas.parentElement);
        this._startLoop();
    }

    // ---- Resize / HiDPI ----

    _resize() {
        const wrapper = this.canvas.parentElement;
        const dpr = window.devicePixelRatio || 1;
        const lw = Math.min(Math.max(wrapper.clientWidth - 32, 280), 620);
        const lh = Math.round(lw * 0.52);

        this.canvas.width  = Math.round(lw * dpr);
        this.canvas.height = Math.round(lh * dpr);
        this.canvas.style.width  = `${lw}px`;
        this.canvas.style.height = `${lh}px`;
        this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

        this.logW = lw;
        this.logH = lh;
        this.cx = lw / 2;
        this.cy = lh;
        this.radius = Math.min(this.cx - 16, lh - 10);
    }

    // ---- Ping-pong extrapolation ----
    // Correctly simulates servo bouncing between MIN/MAX during any gap.
    // Returns {angle, dir} after `elapsedSec` from `startAngle` going `startDir`.

    _pingPong(startAngle, startDir, speedDegSec, elapsedSec) {
        let pos = startAngle;
        let dir = startDir;
        let remaining = speedDegSec * elapsedSec;
        const MIN = CONFIG.MIN_ANGLE;
        const MAX = CONFIG.MAX_ANGLE;

        for (let guard = 0; guard < 30 && remaining > 0.2; guard++) {
            if (dir > 0) {
                const toMax = MAX - pos;
                if (remaining <= toMax) { pos += remaining; remaining = 0; }
                else { remaining -= toMax; pos = MAX; dir = -1; }
            } else {
                const toMin = pos - MIN;
                if (remaining <= toMin) { pos -= remaining; remaining = 0; }
                else { remaining -= toMin; pos = MIN; dir = 1; }
            }
        }
        return { angle: pos, dir };
    }

    // ---- Process incoming sweep buffer ----

    processSweep(sweepArr) {
        if (!sweepArr || sweepArr.length === 0) return;

        const wsNow = performance.now();
        sweepArr.sort((a, b) => a.seq - b.seq);

        const last = sweepArr[sweepArr.length - 1];

        // --- Calibrate sweep speed from batch timing ---
        if (sweepArr.length >= 2) {
            const first = sweepArr[0];
            const batchMs = Math.abs((last.rel_ms || 0) - (first.rel_ms || 0));
            const angleTravelled = sweepArr.reduce((sum, m, i) => {
                if (i === 0) return 0;
                return sum + Math.abs(m.angle - sweepArr[i - 1].angle);
            }, 0);
            if (batchMs > 50 && angleTravelled > 3) {
                const measured = (angleTravelled / batchMs) * 1000;
                if (measured > 5 && measured < 200) {
                    // Weighted average — trust new measurement partially
                    this.sweepSpeed = this.sweepSpeed * 0.4 + measured * 0.6;
                }
            }
        }

        // --- Use EXPLICIT dir from ESP32 (last measurement in batch) ---
        // This is the direction the servo was moving when it was measured.
        this.lastDir = (last.dir != null) ? last.dir : this.lastDir;
        this.lastAngle = last.angle;
        this.lastUpdateTs = wsNow;

        // Snap display to last received position
        this.displayAngle = last.angle;
        this.sweepDir = this.lastDir;

        // --- Update scan history with EMA smoothing ---
        const BUCKET = 6;           // 6° per bucket (2× servo step)
        const EMA_ALPHA = 0.65;     // How much to trust new reading (0-1)
        const HIST_LIFETIME = 9000; // ms — how long to keep a detection

        for (const m of sweepArr) {
            if (m.distance == null) continue;

            // True age of this measurement
            const measTs = wsNow + (m.rel_ms || 0);
            const key = Math.round(m.angle / BUCKET) * BUCKET;

            const existing = this.scanHistory.get(key);
            if (existing) {
                // EMA: blend new reading with history to smooth jitter
                const smoothed = existing.distance * (1 - EMA_ALPHA) + m.distance * EMA_ALPHA;
                this.scanHistory.set(key, {
                    distance: smoothed,
                    ts: measTs,
                    rawDist: m.distance
                });
            } else {
                this.scanHistory.set(key, {
                    distance: m.distance,
                    ts: measTs,
                    rawDist: m.distance
                });
            }
        }

        // Age out stale detections that weren't refreshed this sweep
        // (only remove if the whole angle range has been swept over since detection)
        const now = performance.now();
        for (const [key, entry] of this.scanHistory) {
            if (now - entry.ts > HIST_LIFETIME) {
                this.scanHistory.delete(key);
            }
        }
    }

    // ---- Coordinate helpers ----

    _toXY(angleDeg, distCm) {
        const r   = Math.min(distCm / CONFIG.MAX_DISTANCE_CM, 1) * this.radius;
        const rad = angleDeg * Math.PI / 180;   // small angle = RIGHT side of screen
        return { x: this.cx + r * Math.cos(rad), y: this.cy - r * Math.sin(rad) };
    }

    // ---- Draw frame (60fps) ----

    _draw() {
        const ctx = this.ctx;
        const { cx, cy, radius, logW, logH } = this;
        const now = performance.now();

        // --- Ping-pong extrapolation for sweep line ---
        const elapsed = (now - this.lastUpdateTs) / 1000;
        const pp = this._pingPong(this.lastAngle, this.lastDir, this.sweepSpeed, elapsed);
        this.displayAngle = pp.angle;
        // Update sweepDir for trail direction (don't store pp.dir back to lastDir —
        // that would cause drift; only update lastDir from real ESP32 data)
        const currentDir = pp.dir;

        // --- Clear ---
        ctx.clearRect(0, 0, logW, logH);

        // --- Background semicircle ---
        ctx.fillStyle = '#020912';
        ctx.beginPath();
        ctx.arc(cx, cy, radius, Math.PI, 2 * Math.PI, false);
        ctx.closePath();
        ctx.fill();

        // --- Distance rings ---
        for (let i = 1; i <= 4; i++) {
            const r = (i / 4) * radius;
            const dist = Math.round((i / 4) * CONFIG.MAX_DISTANCE_CM);
            ctx.strokeStyle = 'rgba(0,255,136,0.10)';
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.arc(cx, cy, r, Math.PI, 2 * Math.PI, false);
            ctx.stroke();
            ctx.fillStyle = 'rgba(0,255,136,0.25)';
            ctx.font = '9px Roboto Mono, monospace';
            ctx.textAlign = 'left';
            ctx.fillText(`${dist}cm`, cx + r + 4, cy - 4);
        }

        // --- Angle grid lines ---
        ctx.strokeStyle = 'rgba(0,255,136,0.07)';
        ctx.lineWidth = 1;
        for (let a = 0; a <= 180; a += 30) {
            const rad = a * Math.PI / 180;
            ctx.beginPath();
            ctx.moveTo(cx, cy);
            ctx.lineTo(cx + radius * Math.cos(rad), cy - radius * Math.sin(rad));
            ctx.stroke();
            if (a > 0 && a < 180) {
                const lx = cx + (radius + 13) * Math.cos(rad);
                const ly = cy - (radius + 13) * Math.sin(rad);
                ctx.fillStyle = 'rgba(0,255,136,0.35)';
                ctx.font = '9px Roboto Mono, monospace';
                ctx.textAlign = 'center';
                ctx.fillText(`${a}°`, lx, ly + 3);
            }
        }

        // --- Scan history: draw connected arcs + dots ---
        const HIST_LIFETIME = 9000;
        const detections = [];
        for (const [key, entry] of this.scanHistory) {
            const age = now - entry.ts;
            if (age > HIST_LIFETIME) { this.scanHistory.delete(key); continue; }
            detections.push({ angle: key, distance: entry.distance, age });
        }
        detections.sort((a, b) => a.angle - b.angle);

        // Connect adjacent detections with arcs (same object = within 12° and 25% dist)
        if (detections.length > 1) {
            for (let i = 0; i < detections.length - 1; i++) {
                const a = detections[i];
                const b = detections[i + 1];
                const dAngle = b.angle - a.angle;
                const dDist  = Math.abs(a.distance - b.distance) / Math.max(a.distance, b.distance);
                const avgAge = (a.age + b.age) / 2;
                const op     = Math.max(0, (1 - avgAge / HIST_LIFETIME) * 0.6);
                if (dAngle <= 12 && dDist < 0.25 && op > 0) {
                    const pA = this._toXY(a.angle, a.distance);
                    const pB = this._toXY(b.angle, b.distance);
                    ctx.strokeStyle = `rgba(255,100,50,${op})`;
                    ctx.lineWidth = 2;
                    ctx.shadowColor = `rgba(255,80,20,${op * 0.5})`;
                    ctx.shadowBlur = 5;
                    ctx.beginPath();
                    ctx.moveTo(pA.x, pA.y);
                    ctx.lineTo(pB.x, pB.y);
                    ctx.stroke();
                    ctx.shadowBlur = 0;
                }
            }
        }

        // Individual dots
        for (const { angle, distance, age } of detections) {
            const op = Math.max(0, 1 - age / HIST_LIFETIME);
            if (op <= 0) continue;
            const pos = this._toXY(angle, distance);
            ctx.strokeStyle = `rgba(255,100,50,${op * 0.35})`;
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.arc(pos.x, pos.y, 7, 0, Math.PI * 2);
            ctx.stroke();
            ctx.fillStyle = `rgba(255,120,50,${op})`;
            ctx.shadowColor = `rgba(255,90,20,${op * 0.7})`;
            ctx.shadowBlur = op > 0.5 ? 9 : 3;
            ctx.beginPath();
            ctx.arc(pos.x, pos.y, 3.5, 0, Math.PI * 2);
            ctx.fill();
            ctx.shadowBlur = 0;
        }

        // --- Sweep trail (correct direction) ---
        for (let i = 0; i < 22; i++) {
            const ta = this.displayAngle - currentDir * (20 * i / 22);
            if (ta < CONFIG.MIN_ANGLE || ta > CONFIG.MAX_ANGLE) continue;
            const rad = ta * Math.PI / 180;
            ctx.strokeStyle = `rgba(0,255,136,${(1 - i / 22) * 0.18})`;
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(cx, cy);
            ctx.lineTo(cx + radius * Math.cos(rad), cy - radius * Math.sin(rad));
            ctx.stroke();
        }

        // --- Active sweep line ---
        const sweepRad = this.displayAngle * Math.PI / 180;
        ctx.strokeStyle = '#00ff88';
        ctx.lineWidth = 2.5;
        ctx.shadowColor = '#00ff88';
        ctx.shadowBlur = 14;
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(cx + radius * Math.cos(sweepRad), cy - radius * Math.sin(sweepRad));
        ctx.stroke();
        ctx.shadowBlur = 0;

        // --- Base line ---
        ctx.strokeStyle = 'rgba(0,255,136,0.22)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(cx - radius, cy);
        ctx.lineTo(cx + radius, cy);
        ctx.stroke();

        // --- Centre dot ---
        ctx.fillStyle = '#00ff88';
        ctx.shadowColor = '#00ff88';
        ctx.shadowBlur = 8;
        ctx.beginPath();
        ctx.arc(cx, cy, 4, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0;

        // --- Watermark ---
        ctx.fillStyle = 'rgba(0,255,136,0.06)';
        ctx.font = `bold ${Math.round(radius * 0.16)}px Rajdhani, sans-serif`;
        ctx.textAlign = 'center';
        ctx.fillText('RADAR', cx, cy - radius * 0.48);
    }

    _startLoop() {
        const tick = () => { this._draw(); requestAnimationFrame(tick); };
        requestAnimationFrame(tick);
    }
}
