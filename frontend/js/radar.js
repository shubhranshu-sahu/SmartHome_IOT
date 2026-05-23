// ============================================
// radar.js — Radar canvas rendering
//
// Uses requestAnimationFrame at 60fps.
// Extrapolates sweep angle between backend
// updates so the line moves smoothly at all times.
// ============================================

class RadarDisplay {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx    = this.canvas.getContext('2d');

        // Blip store: {angle, distance, ts}
        this.blips = [];

        // Sweep state
        this.displayAngle  = 90;      // What's currently drawn
        this.targetAngle   = 90;      // Last angle from backend
        this.prevAngle     = null;
        this.sweepVelocity = CONFIG.SWEEP_SPEED_DEG_S;
        this.lastUpdateTs  = performance.now();

        // Geometry — set in _resize()
        this.cx = 0; this.cy = 0; this.radius = 0;
        this.logW = 0; this.logH = 0;

        this._resize();
        const ro = new ResizeObserver(() => this._resize());
        ro.observe(this.canvas.parentElement);

        this._startLoop();
    }

    // ---- Setup / resize ---- //

    _resize() {
        const wrapper = this.canvas.parentElement;
        const dpr = window.devicePixelRatio || 1;

        // Logical size
        const lw = Math.min(Math.max(wrapper.clientWidth - 32, 280), 560);
        const lh = Math.round(lw * 0.52);      // slightly taller than strict half

        // Physical canvas resolution
        this.canvas.width  = Math.round(lw * dpr);
        this.canvas.height = Math.round(lh * dpr);
        this.canvas.style.width  = `${lw}px`;
        this.canvas.style.height = `${lh}px`;

        // Reset transform for DPI
        this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

        // Geometry in LOGICAL pixels
        this.logW   = lw;
        this.logH   = lh;
        this.cx     = lw / 2;
        this.cy     = lh;           // Centre on the base line
        this.radius = Math.min(this.cx - 16, lh - 10);
    }

    // ---- Public API ---- //

    update(angle, distance) {
        const now = performance.now();

        // Estimate velocity from consecutive angle readings
        if (this.prevAngle !== null) {
            const dt    = (now - this.lastUpdateTs) / 1000;
            const delta = angle - this.prevAngle;
            if (dt > 0.05 && Math.abs(delta) < 70) {
                this.sweepVelocity = delta / dt;    // deg / sec
            }
        }

        this.prevAngle    = this.targetAngle;
        this.targetAngle  = angle;
        this.lastUpdateTs = now;

        if (distance !== null && distance !== undefined) {
            this.blips.push({ angle, distance, ts: now });
        }

        // Prune expired blips
        const cutoff = now - CONFIG.BLIP_LIFETIME_MS;
        this.blips = this.blips.filter(b => b.ts > cutoff);
    }

    // ---- Coordinate helpers ---- //

    // Radar angle 0°=left, 90°=top, 180°=right  →  canvas (cx,cy) origin
    _toXY(angleDeg, distCm) {
        const ratio = Math.min(distCm / CONFIG.MAX_DISTANCE_CM, 1);
        const r     = ratio * this.radius;
        const rad   = Math.PI - (angleDeg * Math.PI / 180);
        return {
            x: this.cx + r * Math.cos(rad),
            y: this.cy - r * Math.sin(rad)
        };
    }

    // ---- Draw ---- //

    _draw() {
        const ctx = this.ctx;
        const { cx, cy, radius } = this;

        // Extrapolate display angle between backend polls
        const elapsed = (performance.now() - this.lastUpdateTs) / 1000;
        this.displayAngle = Math.max(
            CONFIG.MIN_ANGLE,
            Math.min(CONFIG.MAX_ANGLE,
                this.targetAngle + this.sweepVelocity * elapsed)
        );

        // ---- Clear ----
        ctx.clearRect(0, 0, this.logW, this.logH);

        // ---- Radar background ----
        ctx.fillStyle = '#020912';
        ctx.beginPath();
        ctx.arc(cx, cy, radius, Math.PI, 2 * Math.PI, false);
        ctx.closePath();
        ctx.fill();

        // ---- Distance rings ----
        const rings = 4;
        for (let i = 1; i <= rings; i++) {
            const r    = (i / rings) * radius;
            const dist = Math.round((i / rings) * CONFIG.MAX_DISTANCE_CM);

            ctx.strokeStyle = 'rgba(0,255,136,0.10)';
            ctx.lineWidth   = 1;
            ctx.beginPath();
            ctx.arc(cx, cy, r, Math.PI, 2 * Math.PI, false);
            ctx.stroke();

            // Label at the rightmost point of each ring
            ctx.fillStyle = 'rgba(0,255,136,0.30)';
            ctx.font      = '9px Roboto Mono, monospace';
            ctx.textAlign = 'left';
            ctx.fillText(`${dist}cm`, cx + r + 3, cy - 3);
        }

        // ---- Angle lines ----
        ctx.strokeStyle = 'rgba(0,255,136,0.08)';
        ctx.lineWidth   = 1;
        for (let a = 0; a <= 180; a += 30) {
            const rad = Math.PI - (a * Math.PI / 180);
            ctx.beginPath();
            ctx.moveTo(cx, cy);
            ctx.lineTo(cx + radius * Math.cos(rad), cy - radius * Math.sin(rad));
            ctx.stroke();

            // Angle labels — skip 0° and 180° (they'd fall outside canvas)
            if (a > 0 && a < 180) {
                const lx = cx + (radius + 13) * Math.cos(rad);
                const ly = cy - (radius + 13) * Math.sin(rad);
                ctx.fillStyle = 'rgba(0,255,136,0.38)';
                ctx.font      = '9px Roboto Mono, monospace';
                ctx.textAlign = 'center';
                ctx.fillText(`${a}°`, lx, ly + 3);
            }
        }

        // ---- Sweep trail (fan of fading lines) ----
        const trailSteps = 28;
        const trailSpan  = 22;    // degrees
        const dir        = Math.sign(this.sweepVelocity) || 1;
        for (let i = 0; i < trailSteps; i++) {
            const ta  = this.displayAngle - dir * (trailSpan * i / trailSteps);
            const rad = Math.PI - (ta * Math.PI / 180);
            ctx.strokeStyle = `rgba(0,255,136,${(1 - i / trailSteps) * 0.22})`;
            ctx.lineWidth   = 2;
            ctx.beginPath();
            ctx.moveTo(cx, cy);
            ctx.lineTo(cx + radius * Math.cos(rad), cy - radius * Math.sin(rad));
            ctx.stroke();
        }

        // ---- Active sweep line ----
        const sweepRad = Math.PI - (this.displayAngle * Math.PI / 180);
        ctx.strokeStyle = '#00ff88';
        ctx.lineWidth   = 2.5;
        ctx.shadowColor = '#00ff88';
        ctx.shadowBlur  = 14;
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(cx + radius * Math.cos(sweepRad), cy - radius * Math.sin(sweepRad));
        ctx.stroke();
        ctx.shadowBlur = 0;

        // ---- Blips ----
        const now = performance.now();
        for (const b of this.blips) {
            const age     = now - b.ts;
            const opacity = Math.max(0, 1 - age / CONFIG.BLIP_LIFETIME_MS);
            if (opacity <= 0) continue;

            const pos = this._toXY(b.angle, b.distance);

            // Outer ring
            ctx.strokeStyle = `rgba(255,110,50,${opacity * 0.45})`;
            ctx.lineWidth   = 1;
            ctx.beginPath();
            ctx.arc(pos.x, pos.y, 9, 0, Math.PI * 2);
            ctx.stroke();

            // Inner dot
            ctx.fillStyle   = `rgba(255,120,50,${opacity})`;
            ctx.shadowColor = `rgba(255,100,30,${opacity})`;
            ctx.shadowBlur  = 12;
            ctx.beginPath();
            ctx.arc(pos.x, pos.y, 4, 0, Math.PI * 2);
            ctx.fill();
            ctx.shadowBlur = 0;
        }

        // ---- Base line ----
        ctx.strokeStyle = 'rgba(0,255,136,0.28)';
        ctx.lineWidth   = 1;
        ctx.beginPath();
        ctx.moveTo(cx - radius, cy);
        ctx.lineTo(cx + radius, cy);
        ctx.stroke();

        // ---- Centre dot ----
        ctx.fillStyle   = '#00ff88';
        ctx.shadowColor = '#00ff88';
        ctx.shadowBlur  = 8;
        ctx.beginPath();
        ctx.arc(cx, cy, 4, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0;

        // ---- Watermark ----
        ctx.fillStyle = 'rgba(0,255,136,0.07)';
        ctx.font      = `bold ${Math.round(radius * 0.16)}px Rajdhani, sans-serif`;
        ctx.textAlign = 'center';
        ctx.fillText('RADAR', cx, cy - radius * 0.48);
    }

    // ---- Loop ---- //

    _startLoop() {
        const tick = () => {
            this._draw();
            requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
    }
}
