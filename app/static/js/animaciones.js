/* Animaciones con Motion (la librería de animación vanilla de Framer Motion, servida desde /static/vendor/motion.js).
   Aporta: entrada escalonada de cada pantalla y rebote al pulsar botones y mosaicos (el indicador deslizante del menú móvil es una transición CSS).
   Si el navegador pide «reducir movimiento», o Motion no cargó, la interfaz funciona igual sin animar. */
window.SIGT_ANIM = (() => {
  const M = window.Motion;
  const reducido = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
  const activo = () => !!M && !reducido();
  const SUAVE = { duration: .18, ease: 'easeOut' };   // corta y sin cálculo de muelle: la pantalla aparece al instante

  /** Entrada de una pantalla: sus primeros bloques aparecen en cascada breve (solo opacidad y desplazamiento: no fuerzan re-maquetado). */
  function pantalla(raiz) {
    if (!activo() || !raiz) return;
    const bloques = [...raiz.children].filter(e => e.getClientRects().length).slice(0, 5);   // solo lo que se ve primero
    if (!bloques.length) return;
    M.animate(bloques, { opacity: [0, 1], y: [10, 0] }, { ...SUAVE, delay: M.stagger(.025) });   // en total ≈ 0,3 s (antes ≈ 1 s)
  }

  /** Rebote al pulsar: delegación global, sin tocar cada botón. */
  function pulsacion() {
    const objetivo = e => e.target.closest?.('.btn, .tile, .pill, .nav-item, .dock-item, .paso button');
    let actual = null;
    const soltar = () => { if (actual) { M.animate(actual, { scale: 1 }, { type: 'spring', stiffness: 500, damping: 18 }); actual = null; } };
    addEventListener('pointerdown', e => {
      if (!activo()) return;
      const el = objetivo(e); if (!el || el.disabled) return;
      actual = el; M.animate(el, { scale: .95 }, { type: 'spring', stiffness: 700, damping: 28 });
    }, { passive: true });
    for (const t of ['pointerup', 'pointercancel', 'dragend', 'scroll', 'blur']) addEventListener(t, soltar, { passive: true, capture: true });
  }

  /** Indicador que se desliza hacia la opción activa (barra inferior móvil). Se mueve con una transición CSS con
      rebote (ver .slide-ind): el estado final es siempre exacto, aunque se pida moverlo varias veces seguidas. */
  const medidor = new ResizeObserver(() => recalcular());         // si el menú o sus botones cambian de tamaño, el indicador los sigue
  function indicadores() {
    for (const cont of document.querySelectorAll('[data-slide]')) {
      const ind = cont.querySelector(':scope > .slide-ind'); if (!ind) continue;
      if (!cont.dataset.observado) { cont.dataset.observado = '1'; medidor.observe(cont); }
      for (const hijo of cont.children) if (!hijo.dataset.observado) { hijo.dataset.observado = '1'; medidor.observe(hijo); }
      const on = cont.querySelector('[data-activo="true"]');
      if (!on) { ind.style.opacity = 0; continue; }
      if (!on.offsetWidth) continue;                       // menú oculto (otro tamaño de pantalla): nada que posicionar
      const f = `${on.offsetLeft}|${on.offsetTop}|${on.offsetWidth}|${on.offsetHeight}`;
      if (ind.dataset.pos === f) continue;                 // ya está ahí
      if (!ind.dataset.pos) ind.classList.add('sin-transicion');           // primera colocación: sin viajar desde el borde
      ind.style.transform = `translate(${on.offsetLeft}px, ${on.offsetTop}px)`;
      ind.style.width = on.offsetWidth + 'px'; ind.style.height = on.offsetHeight + 'px'; ind.style.opacity = 1;
      if (!ind.dataset.pos) { ind.getBoundingClientRect(); ind.classList.remove('sin-transicion'); }
      ind.dataset.pos = f;
    }
  }

  if (M) pulsacion();
  // El indicador sigue solo a la opción activa: se recalcula al cambiar la sección, el tamaño, la orientación o al cargar la tipografía.
  let pendiente = false;
  function recalcular() { if (pendiente) return; pendiente = true; requestAnimationFrame(() => { pendiente = false; indicadores(); }); }
  addEventListener('resize', recalcular);
  addEventListener('orientationchange', recalcular);
  document.fonts?.ready.then(recalcular);
  new MutationObserver(recalcular).observe(document.documentElement, { subtree: true, attributes: true, attributeFilter: ['data-activo'] });   // solo atributos: no se dispara con cada cambio del DOM
  return { pantalla, indicadores };
})();
