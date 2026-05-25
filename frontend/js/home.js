// ============================================
// home.js — Landing page logic
//
// 1. Auth check: if valid token → show "Dashboard" button
// 2. Particle system (canvas background)
// 3. Hero radar (self-animating semicircle canvas)
// 4. GSAP animations (hero, scroll-triggered sections)
// 5. Counter animation for stats bar
// 6. Login modal (doLogin, togglePwd)
// ============================================

gsap.registerPlugin(ScrollTrigger);

// ============================================================
// 1. AUTH CHECK — If already logged in, swap Login → Dashboard
// ============================================================
(async function checkSession() {
    const valid = await verifyAuthToken();
    if (valid) {
        // Already logged in — show Dashboard button, hide Login
        document.getElementById('btn-go-dash')?.classList.remove('d-none');
        document.getElementById('btn-open-login')?.classList.add('d-none');

        // Swap hero + CTA buttons too
        ['btn-hero-login', 'btn-cta'].forEach(id => {
            const el = document.getElementById(id);
            if (!el) return;
            el.removeAttribute('data-bs-toggle');
            el.removeAttribute('data-bs-target');
            el.innerHTML = '<i class="bi bi-grid-fill me-2"></i>Go to Dashboard';
            el.onclick = () => window.location.href = 'index.html';
        });
    }
})();

// ============================================================
// 2. NAVBAR — add .scrolled class on scroll
// ============================================================
window.addEventListener('scroll', () => {
    document.getElementById('home-nav')
        .classList.toggle('scrolled', window.scrollY > 40);
}, { passive: true });

// ============================================================
// 3. PARTICLE SYSTEM
// ============================================================
(function initParticles() {
    const canvas = document.getElementById('particles-canvas');
    const ctx    = canvas.getContext('2d');
    let W, H, particles;

    const N_PARTICLES = 55;
    const CONNECT_DIST = 130;

    function resize() {
        W = canvas.width  = window.innerWidth;
        H = canvas.height = window.innerHeight;
    }

    function createParticles() {
        particles = Array.from({ length: N_PARTICLES }, () => ({
            x:  Math.random() * W,
            y:  Math.random() * H,
            vx: (Math.random() - 0.5) * 0.35,
            vy: (Math.random() - 0.5) * 0.35,
            r:  1 + Math.random() * 1.5,
            a:  0.2 + Math.random() * 0.4,
        }));
    }

    function drawParticles() {
        ctx.clearRect(0, 0, W, H);
        for (let i = 0; i < particles.length; i++) {
            const p = particles[i];
            // Drift
            p.x += p.vx; p.y += p.vy;
            if (p.x < 0 || p.x > W) p.vx *= -1;
            if (p.y < 0 || p.y > H) p.vy *= -1;
            // Dot
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(0,255,136,${p.a})`;
            ctx.fill();
            // Connect nearby
            for (let j = i + 1; j < particles.length; j++) {
                const q  = particles[j];
                const dx = p.x - q.x, dy = p.y - q.y;
                const d  = Math.sqrt(dx * dx + dy * dy);
                if (d < CONNECT_DIST) {
                    ctx.beginPath();
                    ctx.moveTo(p.x, p.y);
                    ctx.lineTo(q.x, q.y);
                    ctx.strokeStyle = `rgba(0,255,136,${0.06 * (1 - d / CONNECT_DIST)})`;
                    ctx.lineWidth = 0.8;
                    ctx.stroke();
                }
            }
        }
        requestAnimationFrame(drawParticles);
    }

    window.addEventListener('resize', () => { resize(); createParticles(); }, { passive: true });
    resize();
    createParticles();
    drawParticles();
})();

// ============================================================
// 4. HERO RADAR — self-animating decorative semicircle
// ============================================================
(function initHeroRadar() {
    const canvas = document.getElementById('hero-radar');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    // Fake objects (static positions, appear as sweep passes)
    const OBJECTS = [
        { deg: 28,  dist: 0.45 },
        { deg: 62,  dist: 0.72 },
        { deg: 90,  dist: 0.31 },
        { deg: 118, dist: 0.58 },
        { deg: 152, dist: 0.84 },
    ].map(o => ({ ...o, intensity: 0 }));

    let sweepDeg = 0;    // 0° = right, 90° = top, 180° = left
    let sweepDir = 1;    // +1 = left, -1 = right
    const SPEED  = 1.2;  // degrees per frame

    function resize() {
        const rect = canvas.parentElement.getBoundingClientRect();
        canvas.width  = rect.width;
        canvas.height = rect.height;
    }

    function xy(deg, frac) {
        const rad = deg * Math.PI / 180;
        const cx  = canvas.width / 2;
        const cy  = canvas.height;
        const r   = Math.min(canvas.width * 0.45, canvas.height * 0.9) * frac;
        return { x: cx + Math.cos(rad) * r, y: cy - Math.sin(rad) * r };
    }

    function draw() {
        const W  = canvas.width;
        const H  = canvas.height;
        const cx = W / 2;
        const cy = H;
        const R  = Math.min(W * 0.45, H * 0.9);
        ctx.clearRect(0, 0, W, H);

        // ---- Rings ----
        [0.25, 0.5, 0.75, 1.0].forEach((f, i) => {
            ctx.beginPath();
            ctx.arc(cx, cy, R * f, Math.PI, 2 * Math.PI);
            ctx.strokeStyle = `rgba(0,255,136,${0.06 + i * 0.03})`;
            ctx.lineWidth = 1;
            ctx.stroke();
        });

        // ---- Spokes ----
        [0, 30, 60, 90, 120, 150, 180].forEach(deg => {
            const rad = deg * Math.PI / 180;
            ctx.beginPath();
            ctx.moveTo(cx, cy);
            ctx.lineTo(cx + Math.cos(rad) * R, cy - Math.sin(rad) * R);
            ctx.strokeStyle = 'rgba(0,255,136,0.06)';
            ctx.lineWidth = 1;
            ctx.stroke();
        });

        // ---- Baseline ----
        ctx.beginPath();
        ctx.moveTo(cx - R, cy);
        ctx.lineTo(cx + R, cy);
        ctx.strokeStyle = 'rgba(0,255,136,0.18)';
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // ---- Sweep trail ----
        const TRAIL = 35;
        for (let i = 0; i < TRAIL; i++) {
            const trailDeg = sweepDeg - i * sweepDir;
            if (trailDeg < 0 || trailDeg > 180) continue;
            const a   = ((TRAIL - i) / TRAIL) * 0.22;
            const rad = trailDeg * Math.PI / 180;
            ctx.beginPath();
            ctx.moveTo(cx, cy);
            ctx.lineTo(cx + Math.cos(rad) * R, cy - Math.sin(rad) * R);
            ctx.strokeStyle = `rgba(0,255,136,${a})`;
            ctx.lineWidth = 1;
            ctx.stroke();
        }

        // ---- Sweep line ----
        const sRad = sweepDeg * Math.PI / 180;
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(cx + Math.cos(sRad) * R, cy - Math.sin(sRad) * R);
        ctx.strokeStyle = '#00ff88';
        ctx.lineWidth   = 2;
        ctx.shadowColor = '#00ff88';
        ctx.shadowBlur  = 10;
        ctx.stroke();
        ctx.shadowBlur  = 0;

        // ---- Advance sweep ----
        sweepDeg += SPEED * sweepDir;
        if (sweepDeg >= 180) { sweepDir = -1; sweepDeg = 180; }
        if (sweepDeg <= 0)   { sweepDir =  1; sweepDeg = 0; }

        // ---- Update + draw objects ----
        OBJECTS.forEach(obj => {
            const diff = Math.abs(obj.deg - sweepDeg);
            obj.intensity = diff < 10
                ? Math.min(1, obj.intensity + 0.18)
                : Math.max(0, obj.intensity - 0.004);

            if (obj.intensity < 0.02) return;
            const pos = xy(obj.deg, obj.dist);
            ctx.beginPath();
            ctx.arc(pos.x, pos.y, 4, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(0,255,136,${obj.intensity})`;
            ctx.shadowColor = '#00ff88';
            ctx.shadowBlur  = obj.intensity * 16;
            ctx.fill();
            ctx.shadowBlur = 0;
        });

        // ---- Origin dot ----
        ctx.beginPath();
        ctx.arc(cx, cy, 4, 0, Math.PI * 2);
        ctx.fillStyle = '#00ff88';
        ctx.shadowColor = '#00ff88';
        ctx.shadowBlur  = 12;
        ctx.fill();
        ctx.shadowBlur = 0;

        requestAnimationFrame(draw);
    }

    window.addEventListener('resize', resize, { passive: true });
    resize();
    draw();
})();

// ============================================================
// 5. GSAP ANIMATIONS
// ============================================================
window.addEventListener('load', function() {

    // ---- Hero entrance (no scroll trigger — fires immediately) ----
    const tl = gsap.timeline({ delay: 0.1 });
    tl.from('#hero-badge',    { opacity: 0, y: 24, duration: 0.55, ease: 'power3.out' })
      .from('#ht-1',          { opacity: 0, y: 50, duration: 0.6,  ease: 'power3.out' }, '-=0.25')
      .from('#ht-2',          { opacity: 0, y: 50, duration: 0.6,  ease: 'power3.out' }, '-=0.45')
      .from('#hero-sub',      { opacity: 0, y: 30, duration: 0.55, ease: 'power3.out' }, '-=0.35')
      .from('#hero-actions',  { opacity: 0, y: 24, duration: 0.5,  ease: 'power3.out' }, '-=0.3')
      .from('#hero-chips',    { opacity: 0, y: 20, duration: 0.5,  ease: 'power3.out' }, '-=0.25')
      .from('#hero-radar-col',{ opacity: 0, x: 40, duration: 0.8,  ease: 'power3.out' }, '-=0.8')
      .from('#scroll-hint',   { opacity: 0, duration: 0.5 }, '-=0.1');

    // ---- Stats bar counters ----
    ScrollTrigger.create({
        trigger: '#stats-bar',
        start:   'top 85%',
        once:    true,
        onEnter: () => {
            document.querySelectorAll('.sb-num').forEach(el => {
                const target = parseInt(el.dataset.target);
                gsap.to({ v: 0 }, {
                    v: target, duration: 1.6, ease: 'power2.out',
                    onUpdate: function() { el.textContent = Math.round(this.targets()[0].v); }
                });
            });
        }
    });

    // ---- Robust scroll animation helper ----
    // gsap.from() with scrollTrigger property sets opacity:0 IMMEDIATELY on load,
    // before any scroll event. If the trigger never fires (CDN block, user already
    // scrolled, bad viewport calc), elements stay permanently invisible.
    // Fix: use explicit gsap.set() + ScrollTrigger.create() + IntersectionObserver
    // fallback that reveals elements after a timeout if already in view.
    function scrollReveal(selector, fromVars, trigger, stagger) {
        const els = document.querySelectorAll(selector);
        if (!els.length) return;
        // Ensure elements start invisible
        gsap.set(els, { ...fromVars, opacity: 0 });

        const toVars = Object.fromEntries(
            Object.keys(fromVars).map(k => [k, k === 'scale' ? 1 : k === 'rotationY' ? 0 : 0])
        );

        const reveal = () => gsap.to(els, {
            ...toVars, opacity: 1, stagger: stagger || 0.1, duration: 0.55, ease: 'power3.out'
        });

        ScrollTrigger.create({
            trigger: trigger,
            start:   'top 80%',
            once:    true,
            onEnter: reveal
        });

        // Fallback: if elements are already in viewport when page loads (or CDN
        // didn't load GSAP's ScrollTrigger), reveal them after 700ms.
        setTimeout(() => {
            const rect = els[0].getBoundingClientRect();
            if (rect.top < window.innerHeight * 1.05) reveal();
        }, 700);
    }

    // Feature cards
    scrollReveal('.feat-col', { y: 50 }, '#features', 0.12);

    // Component 3D flip cards
    scrollReveal('.comp-anim', { scale: 0.85, y: 20 }, '#components', 0.07);

    // Tech stack
    scrollReveal('.tech-anim', { y: 30, rotationY: 20 }, '#tech', 0.08);

    // CTA
    scrollReveal('#cta-title, #cta-sub, #btn-cta', { y: 30 }, '#cta', 0.15);

    // ---- Mobile: click to flip component cards ----
    // On touch devices hover doesn't persist — clicking toggles the flip class.
    const isTouchDevice = window.matchMedia('(hover: none)').matches;
    if (isTouchDevice) {
        document.querySelectorAll('.c3d-wrap').forEach(wrap => {
            wrap.addEventListener('click', () => wrap.classList.toggle('flipped'));
        });
    }
});

// ============================================================
// 6. LOGIN MODAL LOGIC
// ============================================================
function togglePwd() {
    const inp  = document.getElementById('login-password');
    const icon = document.getElementById('eye-icon');
    if (inp.type === 'password') {
        inp.type = 'text';
        icon.className = 'bi bi-eye-slash';
    } else {
        inp.type = 'password';
        icon.className = 'bi bi-eye';
    }
}

async function doLogin() {
    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;
    const errEl    = document.getElementById('login-error');
    const btn      = document.getElementById('btn-login-submit');
    const btnText  = document.getElementById('lm-btn-text');
    const btnSpin  = document.getElementById('lm-btn-spin');

    // Clear previous error
    errEl.classList.add('d-none');
    errEl.textContent = '';

    // Basic validation
    if (!username || !password) {
        showLoginError('Please enter both username and password.');
        return;
    }

    // Loading state
    btn.disabled  = true;
    btnText.classList.add('d-none');
    btnSpin.classList.remove('d-none');

    try {
        const resp = await fetch(CONFIG.API_BASE + '/auth/login', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ username, password }),
        });

        if (resp.ok) {
            const data = await resp.json();
            setAuthToken(data.token);
            // Redirect to dashboard
            window.location.href = 'index.html';
        } else {
            const data = await resp.json().catch(() => ({}));
            const msg = resp.status === 401 ? 'Invalid username or password.'
                      : resp.status === 503 ? 'Database unavailable — check backend connection.'
                      : data.detail || `Login failed (${resp.status})`;
            showLoginError(msg);
        }
    } catch (e) {
        showLoginError('Cannot reach server. Is the backend running?');
    } finally {
        btn.disabled = false;
        btnText.classList.remove('d-none');
        btnSpin.classList.add('d-none');
    }
}

function showLoginError(msg) {
    const el = document.getElementById('login-error');
    el.textContent = msg;
    el.classList.remove('d-none');
    // Trigger shake re-animation by removing and re-adding
    el.style.animation = 'none';
    el.offsetHeight;   // reflow
    el.style.animation = '';
}

// ---- Clear error when modal re-opens ----
document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('login-modal');
    if (modal) {
        modal.addEventListener('show.bs.modal', () => {
            document.getElementById('login-error')?.classList.add('d-none');
            document.getElementById('login-username').value = '';
            document.getElementById('login-password').value = '';
        });
    }
});

// ============================================================
// 7. 3D VIEWER MODAL
// ============================================================
function open3DModal(src, title, event) {
    if (event) {
        event.stopPropagation(); // Prevent the card from flipping
    }
    
    document.getElementById('m3d-title').textContent = title;
    const viewer = document.getElementById('m3d-viewer');
    viewer.src = src;
    
    const modal = new bootstrap.Modal(document.getElementById('model-3d-modal'));
    modal.show();
}

// Reset viewer source on hide to free memory
document.addEventListener('DOMContentLoaded', () => {
    const m3dModal = document.getElementById('model-3d-modal');
    if (m3dModal) {
        m3dModal.addEventListener('hidden.bs.modal', () => {
            document.getElementById('m3d-viewer').src = "";
        });
    }
});
