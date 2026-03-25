/* ==========================================
   EDES VENEZUELA - Lógica de Interactividad
   ========================================== */

document.addEventListener("DOMContentLoaded", () => {
  const brandsTrackLTR = document.getElementById("brandsCarouselTrackLTR");

  // simple infinite auto-scroll for brands (continuous, no start/end pause)
  function createInfiniteCarousel(track) {
    if (!track) return;
    if (track.dataset.infiniteReady === "true") return;

    const originalItems = Array.from(track.children);
    const itemCount = originalItems.length;
    if (itemCount === 0) return;

    // clone once to ensure seamless loop
    originalItems.forEach(item => track.appendChild(item.cloneNode(true)));

    track.style.animation = "none";
    let offset = 0;
    const duration = 100000;
    let lastTime = Date.now();
    let paused = false;
    const dir = track.classList.contains("brands-carousel-rtl") ? 1 : -1;
    let singleSetWidth = 0;
    let autoResumeTimeout = null;
    let isDragging = false;
    let dragStartX = 0;
    let dragStartOffset = 0;
    let dragMoved = false;

    const wrapper = track.closest(".brands-carousel-wrapper") || track.parentElement;
    let lastCenterUpdate = 0;
    const centerUpdateInterval = 90;

    function updateCenteredItem() {
      if (!wrapper) return;
      const now = Date.now();
      if (now - lastCenterUpdate < centerUpdateInterval) return;
      lastCenterUpdate = now;

      const wrapperRect = wrapper.getBoundingClientRect();
      const centerX = wrapperRect.left + wrapperRect.width / 2;
      const items = Array.from(track.children);

      let closestItem = null;
      let closestDistance = Infinity;

      items.forEach((item) => {
        const rect = item.getBoundingClientRect();
        const itemCenter = rect.left + rect.width / 2;
        const distance = Math.abs(centerX - itemCenter);
        if (distance < closestDistance) {
          closestDistance = distance;
          closestItem = item;
        }
      });

      items.forEach((item) => {
        item.classList.toggle("is-centered", item === closestItem);
      });
    }
    function normalizeOffset(value) {
      if (!singleSetWidth) return value;
      if (dir < 0) {
        while (value <= -singleSetWidth) value += singleSetWidth;
        while (value > 0) value -= singleSetWidth;
      } else {
        while (value >= singleSetWidth) value -= singleSetWidth;
        while (value < 0) value += singleSetWidth;
      }
      return value;
    }

    if (wrapper) {
      // Mouse events - pause on hover, auto-resume after 1 seconds
      wrapper.addEventListener("mouseenter", () => {
        paused = true;
        clearTimeout(autoResumeTimeout);
      });
      wrapper.addEventListener("mouseleave", () => {
        // Auto-resume carousel after 1 seconds on desktop
        autoResumeTimeout = setTimeout(() => {
          paused = false;
          lastTime = Date.now();
        }, 500);
      });

      // Touch events - pause on touch, auto-resume after 3 seconds
      wrapper.addEventListener("touchstart", () => {
        paused = true;
        clearTimeout(autoResumeTimeout);
      }, { passive: true });

      wrapper.addEventListener("touchend", () => {
        // Auto-resume carousel after 3 seconds on mobile
        autoResumeTimeout = setTimeout(() => {
          paused = false;
          lastTime = Date.now();
        }, 3000);
      }, { passive: true });

      // Pointer drag to control carousel
      wrapper.addEventListener("pointerdown", (event) => {
        if (event.button !== undefined && event.button !== 0) return;
        if (!singleSetWidth) measure();
        isDragging = true;
        dragMoved = false;
        dragStartX = event.clientX;
        dragStartOffset = offset;
        paused = true;
        clearTimeout(autoResumeTimeout);
        wrapper.classList.add("is-dragging");
        if (wrapper.setPointerCapture) {
          wrapper.setPointerCapture(event.pointerId);
        }
      });

      wrapper.addEventListener("pointermove", (event) => {
        if (!isDragging) return;
        const delta = event.clientX - dragStartX;
        if (Math.abs(delta) > 2) dragMoved = true;
        offset = normalizeOffset(dragStartOffset + delta);
        track.style.transform = `translateX(${offset}px)`;
        updateCenteredItem();
      });

      function finishDrag(event) {
        if (!isDragging) return;
        isDragging = false;
        wrapper.classList.remove("is-dragging");
        if (event && wrapper.releasePointerCapture) {
          wrapper.releasePointerCapture(event.pointerId);
        }
        autoResumeTimeout = setTimeout(() => {
          paused = false;
          lastTime = Date.now();
        }, 800);
      }

      wrapper.addEventListener("pointerup", finishDrag);
      wrapper.addEventListener("pointercancel", finishDrag);
      wrapper.addEventListener("pointerleave", (event) => {
        if (isDragging) finishDrag(event);
      });
    }

    function measure() {
      const gap = parseInt(getComputedStyle(track).gap) || 48;
      const totalWidth = track.scrollWidth;
      if (totalWidth > 0) {
        singleSetWidth = totalWidth / 2;
        return;
      }

      const items = Array.from(track.children).slice(0, itemCount);
      const widths = items.map(item => item.getBoundingClientRect().width);
      const maxWidth = Math.max(0, ...widths);
      singleSetWidth = (maxWidth + gap) * itemCount;
    }

    function step() {
      const now = Date.now();
      const elapsed = now - lastTime;
      lastTime = now;
      if (paused) { requestAnimationFrame(step); return; }

      if (!singleSetWidth) {
        measure();
        if (!singleSetWidth) { requestAnimationFrame(step); return; }
      }

      offset += dir * (singleSetWidth / duration) * elapsed;

      offset = normalizeOffset(offset);

      track.style.transform = `translateX(${offset}px)`;
      updateCenteredItem();
      requestAnimationFrame(step);
    }

    // start immediately, then re-measure when images load
    measure();
    track.dataset.infiniteReady = "true";
    requestAnimationFrame(step);

    const images = Array.from(track.querySelectorAll("img"));
    images.forEach(img => {
      if (!img.complete) {
        img.addEventListener("load", () => measure(), { once: true });
        img.addEventListener("error", () => measure(), { once: true });
      }
    });

    window.addEventListener("resize", () => {
      measure();
      updateCenteredItem();
    });
  }

  createInfiniteCarousel(brandsTrackLTR);

  // 1. LÓGICA DEL CARRUSEL "ANTES Y DESPUÉS"
  const track = document.getElementById("baCarouselTrack");
  const prevBtn = document.getElementById("baPrev");
  const nextBtn = document.getElementById("baNext");
  const dots = document.querySelectorAll(".ba-dot");

  if (track && prevBtn && nextBtn) {
    const slides = Array.from(track.children);
    let currentIndex = 0;

    function updateCarousel(index) {
      // Mover el track
      track.style.transform = `translateX(-${index * 100}%)`;

      // Actualizar puntos
      dots.forEach((dot) => dot.classList.remove("active"));
      if (dots[index]) dots[index].classList.add("active");

      currentIndex = index;
    }

    // Eventos de botones
    nextBtn.addEventListener("click", () => {
      const index = (currentIndex + 1) % slides.length;
      updateCarousel(index);
      resetAuto();
    });

    prevBtn.addEventListener("click", () => {
      const index = (currentIndex - 1 + slides.length) % slides.length;
      updateCarousel(index);
      resetAuto();
    });

    // Eventos de puntos
    dots.forEach((dot, index) => {
      dot.addEventListener("click", () => {
        updateCarousel(index);
        resetAuto();
      });
    });

    // Autoplay controlado (permite pausa extra al reiniciar ciclo)
    const autoDelay = 7000; // ms entre slides
    const wrapPauseDelay = 2000; // ms extra cuando completa la vuelta
    let autoTimer = null;

    function scheduleAuto(delay = autoDelay) {
      if (autoTimer) clearTimeout(autoTimer);
      autoTimer = setTimeout(() => {
        advance();
      }, delay);
    }

    function advance() {
      const nextIndex = (currentIndex + 1) % slides.length;
      updateCarousel(nextIndex);
      const nextDelay = nextIndex === 0 ? wrapPauseDelay : autoDelay;
      scheduleAuto(nextDelay);
    }

    // Iniciar autoplay
    scheduleAuto();

    // Reiniciar autoplay después de interacción
    function resetAuto() {
      scheduleAuto(autoDelay);
    }
  }

  // 2. LÓGICA DEL HEADER (CAMBIO DE COLOR AL HACER SCROLL)
  const header = document.getElementById("mainHeader");

  if (header) {
    function checkScroll() {
      if (window.scrollY > 50) {
        header.classList.add("scrolled");
      } else {
        header.classList.remove("scrolled");
      }
    }

    // Ejecutar al cargar y al hacer scroll
    window.addEventListener("scroll", checkScroll);
    checkScroll();
  }

  // 3. INICIALIZACIÓN DE TOASTS (NOTIFICACIONES)
  // Nota: Requiere Bootstrap para funcionar. Si no tienes Bootstrap cargado, este código no hará nada.
  const toastElements = document.querySelectorAll(".toast");
  const bootstrap = window.bootstrap; // Declare the bootstrap variable

  if (toastElements.length > 0 && typeof bootstrap !== "undefined") {
    toastElements.forEach((toastEl) => {
      const toast = new bootstrap.Toast(toastEl, { delay: 5000 });
      toast.show();
    });
  }
});

document.addEventListener(
  "contextmenu",
  function (e) {
    if (e.target.nodeName === "IMG") {
      e.preventDefault();
    }
  },
  false
);

// Opcional: Evitar atajos de teclado como Ctrl+S o Ctrl+U (Ver código fuente)
document.addEventListener("keydown", function (e) {
  if (e.ctrlKey && (e.key === "s" || e.key === "u")) {
    e.preventDefault();
  }
});
