/* Animaciones con Motion (la librería de animación vanilla de Framer Motion, servida desde /static/vendor/motion.js).
   Aporta: entrada escalonada de cada pantalla, rebote al pulsar botones y mosaicos, e indicador deslizante en los menús.
   Si el navegador pide «reducir movimiento», o Motion no cargó, la interfaz funciona igual sin animar. */
window.SIGT_ANIM = (() => {
  const M = window.Motion;
  const reducido = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
  const activo = () => !!M && !reducido();
  const MUELLE = { type: 'spring', stiffness: 420, damping: 32 };

  /** Entrada de una pantalla: sus bloques aparecen en cascada, subiendo y creciendo con un muelle. */
  function pantalla(raiz) {
    if (!activo() || !raiz) return;
    const bloques = [...raiz.querySelectorAll(':scope > *')].filter(e => e.getClientRects().length).slice(0, 14);
    if (!bloques.length) return;
    M.animate(bloques, { opacity: [0, 1], y: [22, 0], scale: [.985, 1] }, { ...MUELLE, delay: M.stagger(.055) });
    const mosaicos = [...raiz.querySelectorAll('.tile, .paso')].filter(e => e.getClientRects().length).slice(0, 24);
    if (mosaicos.length) M.animate(mosaicos, { opacity: [0, 1], y: [16, 0] }, { ...MUELLE, delay: M.stagger(.045, { startDelay: .12 }) });
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
    for (const t of ['pointerup', 'pointercancel', 'pointerleave', 'dragend']) addEventListener(t, soltar, { passive: true });
  }

  /** Indicador que se desliza hacia la opción activa (barra inferior móvil y menú de tabletas). */
  function indicadores() {
    for (const cont of document.querySelectorAll('[data-slide]')) {
      const ind = cont.querySelector(':scope > .slide-ind'); if (!ind) continue;
      const on = cont.querySelector('[data-activo="true"]');
      if (!on) { ind.style.opacity = 0; continue; }
      const dest = { x: on.offsetLeft, y: on.offsetTop, width: on.offsetWidth, height: on.offsetHeight };
      if (!activo() || ind.dataset.listo !== '1') { Object.assign(ind.style, { transform: `translate(${dest.x}px, ${dest.y}px)`, width: dest.width + 'px', height: dest.height + 'px', opacity: 1 }); ind.dataset.listo = '1'; continue; }
      ind.style.opacity = 1;
      M.animate(ind, { x: dest.x, y: dest.y, width: dest.width, height: dest.height }, { type: 'spring', stiffness: 380, damping: 30 });
    }
  }

  if (M) pulsacion();
  addEventListener('resize', () => indicadores());
  return { pantalla, indicadores };
})();
