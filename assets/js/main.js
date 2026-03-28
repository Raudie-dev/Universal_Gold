/* ═══════════════════════════════════════════════════════
   UNIVERSAL GOLD — main.js
   Constellation rendered INSIDE specific dark sections
   (no fixed canvas, no white-gap issue)
═══════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {

  // ─── CONSTELLATION ENGINE ─────────────────────────────
  // Renders a canvas constellation as an absolute background
  // inside any given container element.
  function createConstellation(container, opts = {}) {
    const {
      starCount    = 90,
      connectDist  = 150,
      withShooting = true,
      intensity    = 1,
    } = opts;

    const canvas = document.createElement('canvas');
    canvas.className = 'constellation-canvas';
    Object.assign(canvas.style, {
      position:      'absolute',
      inset:         '0',
      width:         '100%',
      height:        '100%',
      pointerEvents: 'none',
      zIndex:        '0',
    });
    // Make sure the host section clips the canvas properly
    if (getComputedStyle(container).position === 'static') {
      container.style.position = 'relative';
    }
    container.prepend(canvas);

    const ctx  = canvas.getContext('2d');
    const GOLD   = [184, 150, 46];
    const SILVER = [220, 210, 190];
    let W, H, frame = 0;
    let stars = [], shooters = [], nebulae = [];

    function rgba(rgb, a) {
      return `rgba(${rgb[0]},${rgb[1]},${rgb[2]},${Math.max(0, Math.min(1, a))})`;
    }

    function buildAll() {
      W = canvas.width  = container.offsetWidth  || 1;
      H = canvas.height = container.offsetHeight || 1;

      nebulae = [];
      for (let i = 0; i < 4; i++) {
        nebulae.push({
          x:     Math.random() * W,
          y:     Math.random() * H,
          rx:    90 + Math.random() * 200,
          ry:    60 + Math.random() * 130,
          alpha: (0.014 + Math.random() * 0.020) * intensity,
          hue:   Math.random() > 0.5 ? GOLD : SILVER,
        });
      }

      stars = [];
      const count = Math.round(starCount * intensity);
      for (let i = 0; i < count; i++) {
        const bright = Math.random() > 0.75;
        stars.push({
          x:     Math.random() * W,
          y:     Math.random() * H,
          r:     bright ? 1.0 + Math.random() * 1.4 : 0.3 + Math.random() * 0.8,
          phase: Math.random() * Math.PI * 2,
          speed: 0.006 + Math.random() * 0.011,
          alpha: (bright ? 0.5 + Math.random() * 0.45 : 0.18 + Math.random() * 0.35) * intensity,
          color: Math.random() > 0.28 ? GOLD : SILVER,
          sparkle:     bright && Math.random() > 0.52,
          sparkleSize: 1.6 + Math.random() * 2.6,
          drift: {
            x: (Math.random() - 0.5) * 0.03,
            y: (Math.random() - 0.5) * 0.016,
          },
        });
      }
    }

    function spawnShooter() {
      if (!withShooting) return;
      const fromLeft = Math.random() > 0.5;
      const angle    = (12 + Math.random() * 22) * Math.PI / 180;
      const speed    = 7 + Math.random() * 9;
      shooters.push({
        x: fromLeft ? -20 : W + 20,
        y: Math.random() * H * 0.7,
        vx: fromLeft ?  Math.cos(angle) * speed : -Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        len: 70 + Math.random() * 110,
        alpha: 0, life: 0,
        maxLife: 55 + Math.random() * 50,
      });
    }

    function drawSparkle(x, y, size, a, color) {
      ctx.save();
      ctx.strokeStyle = rgba(color, a);
      ctx.lineWidth = 0.65;
      ctx.beginPath();
      ctx.moveTo(x, y - size);  ctx.lineTo(x, y + size);
      ctx.moveTo(x - size, y);  ctx.lineTo(x + size, y);
      const d = size * 0.48;
      ctx.moveTo(x - d, y - d); ctx.lineTo(x + d, y + d);
      ctx.moveTo(x + d, y - d); ctx.lineTo(x - d, y + d);
      ctx.stroke();
      ctx.restore();
    }

    function draw() {
      ctx.clearRect(0, 0, W, H);
      frame++;

      // Nebulae
      nebulae.forEach(n => {
        const r  = Math.max(n.rx, n.ry);
        const sx = n.rx / r, sy = n.ry / r;
        ctx.save();
        ctx.scale(sx, sy);
        const gx = n.x / sx, gy = n.y / sy;
        const gr = ctx.createRadialGradient(gx, gy, 0, gx, gy, r);
        gr.addColorStop(0,   rgba(n.hue, n.alpha));
        gr.addColorStop(0.5, rgba(n.hue, n.alpha * 0.38));
        gr.addColorStop(1,   rgba(n.hue, 0));
        ctx.fillStyle = gr;
        ctx.beginPath();
        ctx.arc(gx, gy, r, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      });

      // Constellation lines
      for (let i = 0; i < stars.length; i++) {
        for (let j = i + 1; j < stars.length; j++) {
          const dx   = stars[i].x - stars[j].x;
          const dy   = stars[i].y - stars[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < connectDist) {
            const t  = 1 - dist / connectDist;
            const la = t * t * 0.19 * intensity;
            const gr = ctx.createLinearGradient(stars[i].x, stars[i].y, stars[j].x, stars[j].y);
            gr.addColorStop(0,   rgba(stars[i].color, la));
            gr.addColorStop(0.5, rgba(GOLD, la * 1.3));
            gr.addColorStop(1,   rgba(stars[j].color, la));
            ctx.beginPath();
            ctx.strokeStyle = gr;
            ctx.lineWidth   = 0.38 + t * 0.28;
            ctx.moveTo(stars[i].x, stars[i].y);
            ctx.lineTo(stars[j].x, stars[j].y);
            ctx.stroke();
          }
        }
      }

      // Stars
      stars.forEach(s => {
        s.phase += s.speed;
        s.x += s.drift.x;  s.y += s.drift.y;
        if (s.x < -8) s.x = W + 8;
        if (s.x > W + 8) s.x = -8;
        if (s.y < -8) s.y = H + 8;
        if (s.y > H + 8) s.y = -8;

        const twinkle = 0.5 + 0.5 * Math.sin(s.phase);
        const a = s.alpha * (0.35 + 0.65 * twinkle);

        const halo = ctx.createRadialGradient(s.x, s.y, 0, s.x, s.y, s.r * 4.2);
        halo.addColorStop(0, rgba(s.color, a * 0.4));
        halo.addColorStop(1, rgba(s.color, 0));
        ctx.fillStyle = halo;
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.r * 4.2, 0, Math.PI * 2);
        ctx.fill();

        ctx.fillStyle = rgba(s.color, a);
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
        ctx.fill();

        if (s.sparkle && twinkle > 0.6) {
          drawSparkle(s.x, s.y, s.sparkleSize * twinkle, a * 0.8, s.color);
        }
      });

      // Shooting stars
      if (frame % 300 === 0 && Math.random() > 0.3) spawnShooter();
      shooters = shooters.filter(ss => ss.life < ss.maxLife);
      shooters.forEach(ss => {
        ss.life++;
        ss.x += ss.vx;  ss.y += ss.vy;
        const t = ss.life / ss.maxLife;
        ss.alpha = t < 0.2 ? t / 0.2 : t > 0.72 ? 1 - (t - 0.72) / 0.28 : 1;

        const hyp  = Math.hypot(ss.vx, ss.vy);
        const tailX = ss.x - (ss.vx / hyp) * ss.len;
        const tailY = ss.y - (ss.vy / hyp) * ss.len;

        const gr = ctx.createLinearGradient(tailX, tailY, ss.x, ss.y);
        gr.addColorStop(0,   rgba(GOLD, 0));
        gr.addColorStop(0.6, rgba(GOLD, ss.alpha * 0.48));
        gr.addColorStop(1,   rgba([255, 245, 200], ss.alpha));

        ctx.save();
        ctx.strokeStyle = gr;
        ctx.lineWidth   = 1.4;
        ctx.shadowColor = rgba(GOLD, ss.alpha * 0.5);
        ctx.shadowBlur  = 5;
        ctx.beginPath();
        ctx.moveTo(tailX, tailY);
        ctx.lineTo(ss.x, ss.y);
        ctx.stroke();

        const hg = ctx.createRadialGradient(ss.x, ss.y, 0, ss.x, ss.y, 4);
        hg.addColorStop(0, rgba([255, 250, 215], ss.alpha));
        hg.addColorStop(1, rgba(GOLD, 0));
        ctx.fillStyle = hg;
        ctx.beginPath();
        ctx.arc(ss.x, ss.y, 4, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      });

      requestAnimationFrame(draw);
    }

    // Keep canvas in sync when the section resizes
    const ro = new ResizeObserver(() => buildAll());
    ro.observe(container);

    buildAll();
    draw();

    if (withShooting) {
      setTimeout(spawnShooter, 2600);
      setTimeout(spawnShooter, 6200);
    }
  }


  // ─── ATTACH TO SPECIFIC DARK SECTIONS ─────────────────
  // Only dark-background sections — no white/cream pages affected.
  const constellationTargets = [
    // Page header on inner pages (Catálogo, Carrito)
    {
      selector: '.page-header',
      opts: { starCount: 70, intensity: 0.8, withShooting: true },
    },
    // Product breadcrumb bar
    {
      selector: '.product-breadcrumb-bar',
      opts: { starCount: 40, intensity: 0.55, withShooting: false },
    },
    // Contact card (dark panel in cart)
    {
      selector: '.contact-card',
      opts: { starCount: 38, connectDist: 110, intensity: 0.55, withShooting: false },
    },
    // Featured products band (dark ink)
    {
      selector: '#destacados',
      opts: { starCount: 80, intensity: 0.9, withShooting: true },
    },
    // CTA full-bleed dark section
    {
      selector: '.cta-section',
      opts: { starCount: 110, intensity: 1.15, withShooting: true },
    },
  ];

  constellationTargets.forEach(({ selector, opts }) => {
    const el = document.querySelector(selector);
    if (el) createConstellation(el, opts);
  });


  // ─── HEADER SCROLL ───────────────────────────────────
  const header = document.getElementById('mainHeader');
  if (header) {
    const onScroll = () => header.classList.toggle('scrolled', window.scrollY > 60);
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  // ─── HERO SLIDER ──────────────────────────────────────
  const slides = document.querySelectorAll('.hero-slide');
  const dots   = document.querySelectorAll('.hero-dot');
  let current = 0, heroInterval;

  function goToSlide(idx) {
    slides[current]?.classList.remove('active');
    dots[current]?.classList.remove('active');
    current = idx;
    slides[current]?.classList.add('active');
    dots[current]?.classList.add('active');
  }

  if (slides.length > 1) {
    heroInterval = setInterval(() => goToSlide((current + 1) % slides.length), 5500);
    dots.forEach((dot, i) => {
      dot.addEventListener('click', () => {
        clearInterval(heroInterval);
        goToSlide(i);
        heroInterval = setInterval(() => goToSlide((current + 1) % slides.length), 5500);
      });
    });
  }

  // ─── SCROLL REVEAL ────────────────────────────────────
  const revealEls = document.querySelectorAll('.reveal');
  if (revealEls.length) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const siblings = Array.from(entry.target.parentElement?.children || []);
          const delay = Math.min(siblings.indexOf(entry.target) * 80, 320);
          setTimeout(() => entry.target.classList.add('visible'), delay);
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });
    revealEls.forEach(el => io.observe(el));
  }

  // ─── CART FORM VALIDATION ────────────────────────────
  const phoneInput  = document.getElementById('inputTelefono');
  const phoneError  = document.getElementById('phoneError');
  const nombreInput = document.getElementById('inputNombre');
  const correoInput = document.getElementById('inputCorreo');
  const submitBtn   = document.getElementById('btnSubmit');

  function checkForm() {
    if (!submitBtn) return;
    const nombre  = nombreInput?.value.trim();
    const correo  = correoInput?.value.trim();
    const tel     = phoneInput?.value.trim();
    const phoneOk = /^\+58\d{10}$/.test(tel);
    const emailOk = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(correo);
    const ready   = nombre && emailOk && phoneOk;
    submitBtn.disabled = !ready;
    submitBtn.querySelector('span').textContent = ready ? 'Enviar Solicitud' : 'Completa los datos';
    submitBtn.querySelector('i').className = ready ? 'fas fa-arrow-right' : 'fas fa-lock';
  }

  phoneInput?.addEventListener('input', () => {
    const ok = /^\+58\d{10}$/.test(phoneInput.value.trim());
    phoneError.style.display = phoneInput.value && !ok ? 'block' : 'none';
    checkForm();
  });
  nombreInput?.addEventListener('input', checkForm);
  correoInput?.addEventListener('input', checkForm);

  // ─── SMOOTH ANCHOR SCROLL ─────────────────────────────
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', e => {
      const target = document.querySelector(anchor.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

});