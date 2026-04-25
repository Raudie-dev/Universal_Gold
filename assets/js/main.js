document.addEventListener('DOMContentLoaded', () => {

  // ─── UTILIDADES ───────────────────────────────────────
  const isMobile = () => window.matchMedia('(max-width: 768px)').matches;

  function debounce(fn, ms) {
    let t;
    return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
  }

  // ─── LOOP GLOBAL COMPARTIDO ───────────────────────────
  // Un único requestAnimationFrame itera todas las instancias activas.
  // Se pausa automáticamente cuando la pestaña no es visible.
  const activeInstances = new Set();
  let rafId = null;
  let pageVisible = true;

  function globalLoop() {
    if (pageVisible && activeInstances.size > 0) {
      activeInstances.forEach(inst => inst.draw());
    }
    rafId = requestAnimationFrame(globalLoop);
  }

  document.addEventListener('visibilitychange', () => {
    pageVisible = document.visibilityState === 'visible';
  });

  function startGlobalLoop() {
    if (!rafId) rafId = requestAnimationFrame(globalLoop);
  }

  // ─── CONSTELLATION ENGINE ─────────────────────────────
  function createConstellation(container, opts = {}) {
    const mobile = isMobile();
    const {
      starCount    = mobile ? 40 : 90,
      connectDist  = 150,
      withShooting = !mobile,   // sin meteoros en móvil
      intensity    = 1,
    } = opts;

    const canvas = document.createElement('canvas');
    canvas.className = 'constellation-canvas';
    Object.assign(canvas.style, {
      position: 'absolute', inset: '0',
      width: '100%', height: '100%',
      pointerEvents: 'none', zIndex: '0',
    });
    if (getComputedStyle(container).position === 'static') {
      container.style.position = 'relative';
    }
    container.prepend(canvas);

    const ctx    = canvas.getContext('2d', { alpha: true });
    const GOLD   = [184, 150, 46];
    const SILVER = [220, 210, 190];
    let W = 0, H = 0, frame = 0;
    let stars = [], shooters = [], nebulae = [];
    let isVisible = false;   // controlado por IntersectionObserver

    function rgba(rgb, a) {
      return `rgba(${rgb[0]},${rgb[1]},${rgb[2]},${Math.max(0, Math.min(1, a))})`;
    }

    function buildAll() {
      W = canvas.width  = container.offsetWidth  || 1;
      H = canvas.height = container.offsetHeight || 1;

      nebulae = Array.from({ length: 3 }, () => ({
        x:     Math.random() * W,
        y:     Math.random() * H,
        rx:    90 + Math.random() * 180,
        ry:    60 + Math.random() * 120,
        alpha: (0.014 + Math.random() * 0.018) * intensity,
        hue:   Math.random() > 0.5 ? GOLD : SILVER,
      }));

      const count = Math.round(starCount * intensity);
      stars = Array.from({ length: count }, () => {
        const bright = Math.random() > 0.75;
        return {
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
        };
      });

      shooters = [];
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
        len: 70 + Math.random() * 100,
        alpha: 0, life: 0,
        maxLife: 55 + Math.random() * 50,
      });
    }

    function drawSparkle(x, y, size, a, color) {
      ctx.save();
      ctx.strokeStyle = rgba(color, a);
      ctx.lineWidth = 0.65;
      ctx.beginPath();
      ctx.moveTo(x, y - size); ctx.lineTo(x, y + size);
      ctx.moveTo(x - size, y); ctx.lineTo(x + size, y);
      const d = size * 0.48;
      ctx.moveTo(x - d, y - d); ctx.lineTo(x + d, y + d);
      ctx.moveTo(x + d, y - d); ctx.lineTo(x - d, y + d);
      ctx.stroke();
      ctx.restore();
    }

    // ── Spatial grid para reducir comparaciones O(n²) ──
    // Solo busca vecinos en la celda adyacente, no en todas las estrellas.
    function buildGrid() {
      const cell = connectDist;
      const cols = Math.ceil(W / cell) + 1;
      const grid = new Map();
      stars.forEach((s, i) => {
        const cx = Math.floor(s.x / cell);
        const cy = Math.floor(s.y / cell);
        const key = cx + ',' + cy;
        if (!grid.has(key)) grid.set(key, []);
        grid.get(key).push(i);
      });
      return { grid, cols, cell };
    }

    function drawLines({ grid, cell }) {
      const cellRange = 1;
      const drawn = new Set();

      stars.forEach((s, i) => {
        const cx = Math.floor(s.x / cell);
        const cy = Math.floor(s.y / cell);

        for (let dx = -cellRange; dx <= cellRange; dx++) {
          for (let dy = -cellRange; dy <= cellRange; dy++) {
            const neighbors = grid.get((cx + dx) + ',' + (cy + dy));
            if (!neighbors) continue;

            neighbors.forEach(j => {
              if (j <= i) return;
              const pairKey = i * 10000 + j;
              if (drawn.has(pairKey)) return;
              drawn.add(pairKey);

              const ddx  = s.x - stars[j].x;
              const ddy  = s.y - stars[j].y;
              const dist = Math.sqrt(ddx * ddx + ddy * ddy);
              if (dist >= connectDist) return;

              const t  = 1 - dist / connectDist;
              const la = t * t * 0.19 * intensity;
              const gr = ctx.createLinearGradient(s.x, s.y, stars[j].x, stars[j].y);
              gr.addColorStop(0,   rgba(s.color, la));
              gr.addColorStop(0.5, rgba(GOLD, la * 1.3));
              gr.addColorStop(1,   rgba(stars[j].color, la));
              ctx.beginPath();
              ctx.strokeStyle = gr;
              ctx.lineWidth   = 0.38 + t * 0.28;
              ctx.moveTo(s.x, s.y);
              ctx.lineTo(stars[j].x, stars[j].y);
              ctx.stroke();
            });
          }
        }
      });
    }

    // ── draw() — llamado desde el loop global ────────────
    const instance = {
      draw() {
        if (!isVisible || W === 0) return;
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

        // Líneas con spatial grid
        const gridData = buildGrid();
        drawLines(gridData);

        // Stars
        stars.forEach(s => {
          s.phase += s.speed;
          s.x += s.drift.x; s.y += s.drift.y;
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
          ss.x += ss.vx; ss.y += ss.vy;
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
      },
    };

    // ── Visibilidad — pausa cuando sale de pantalla ───────
    const io = new IntersectionObserver(entries => {
      isVisible = entries[0].isIntersecting;
    }, { threshold: 0.01 });
    io.observe(container);

    // ── ResizeObserver con debounce ───────────────────────
    const ro = new ResizeObserver(debounce(() => buildAll(), 200));
    ro.observe(container);

    buildAll();
    activeInstances.add(instance);
    startGlobalLoop();

    if (withShooting) {
      setTimeout(spawnShooter, 2600);
      setTimeout(spawnShooter, 6200);
    }
  }


  // ─── ATTACH TO DARK SECTIONS ──────────────────────────
  const mobile = isMobile();
  const constellationTargets = [
    {
      selector: '.page-header',
      opts: { starCount: mobile ? 35 : 70, intensity: 0.8, withShooting: !mobile },
    },
    {
      selector: '.product-breadcrumb-bar',
      opts: { starCount: mobile ? 20 : 40, intensity: 0.55, withShooting: false },
    },
    {
      selector: '.contact-card',
      opts: { starCount: mobile ? 18 : 38, connectDist: 110, intensity: 0.55, withShooting: false },
    },
    {
      selector: '#destacados',
      opts: { starCount: mobile ? 40 : 80, intensity: 0.9, withShooting: !mobile },
    },
    {
      selector: '.cta-section',
      opts: { starCount: mobile ? 50 : 110, intensity: mobile ? 0.8 : 1.15, withShooting: !mobile },
    },
  ];

  constellationTargets.forEach(({ selector, opts }) => {
    const el = document.querySelector(selector);
    if (el) createConstellation(el, opts);
  });


  // ─── HEADER SCROLL ────────────────────────────────────
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

  // Precargar el segundo slide (el primero ya se muestra en CSS)
  if (slides.length > 1) {
    const second = slides[1];
    const bgUrl  = second.style.backgroundImage.replace(/url\(["']?(.+?)["']?\)/, '$1');
    if (bgUrl) {
      const link = document.createElement('link');
      link.rel = 'prefetch'; link.as = 'image'; link.href = bgUrl;
      document.head.appendChild(link);
    }
  }

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

  // ─── CART FORM VALIDATION ─────────────────────────────
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

  // ─── CUSTOM CAROUSEL (PERSONALIZADO SECTION) ─────────
  function initCustomCarousel() {
    const container = document.querySelector('.custom-carousel-container');
    if (!container) return;

    const carousel = container.querySelector('.custom-carousel');
    const slides = carousel.querySelectorAll('.carousel-slide');
    const prevBtn = container.querySelector('.carousel-prev');
    const nextBtn = container.querySelector('.carousel-next');
    const dots = container.querySelectorAll('.carousel-dot');

    if (!slides.length) return;

    let currentIndex = 0;
    let autoplayTimer = null;

    function updateSlide(index) {
      // Asegurar que el índice esté dentro del rango
      currentIndex = (index + slides.length) % slides.length;

      // Actualizar slides
      slides.forEach((slide, i) => {
        slide.classList.toggle('active', i === currentIndex);
      });

      // Actualizar dots
      dots.forEach((dot, i) => {
        dot.classList.toggle('active', i === currentIndex);
      });
    }

    function nextSlide() {
      updateSlide(currentIndex + 1);
      resetAutoplay();
    }

    function prevSlide() {
      updateSlide(currentIndex - 1);
      resetAutoplay();
    }

    function goToSlide(index) {
      updateSlide(index);
      resetAutoplay();
    }

    function startAutoplay() {
      autoplayTimer = setInterval(nextSlide, 5000); // Cambiar cada 5 segundos
    }

    function resetAutoplay() {
      clearInterval(autoplayTimer);
      startAutoplay();
    }

    // Event listeners
    prevBtn.addEventListener('click', prevSlide);
    nextBtn.addEventListener('click', nextSlide);
    dots.forEach((dot, index) => {
      dot.addEventListener('click', () => goToSlide(index));
    });

    // Keyboard navigation
    document.addEventListener('keydown', (e) => {
      if (document.activeElement === container || container.contains(document.activeElement)) {
        if (e.key === 'ArrowLeft') prevSlide();
        if (e.key === 'ArrowRight') nextSlide();
      }
    });

    // Pausar autoplay cuando el mouse está sobre el carrusel
    container.addEventListener('mouseenter', () => {
      clearInterval(autoplayTimer);
    });

    container.addEventListener('mouseleave', () => {
      startAutoplay();
    });

    // Iniciar autoplay
    startAutoplay();
  }

  // Inicializar carrusel cuando DOM esté listo
  initCustomCarousel();

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

