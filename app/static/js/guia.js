/* Guía de bienvenida: recorrido paso a paso, según los permisos de cada persona, que explica cada botón y sección. */
SIGT.modulos.guia = () => ({
    tour: { on: false, i: 0, pasos: [], hole: null, pop: { top: 0, left: 0, w: 340 } },

    // Ganchos: el núcleo los invoca al ingresar, al entrar a una vista y al salir.
    ganchos: {
      listo() { if (!this.user.tour_visto) setTimeout(() => this.iniciarTour(), 900); },
    },

    pasosBase() {
      const nav = (id, t, d) => ({ sel: `[data-tour="nav-${id}"]`, alt: '[data-tour="nav-_mas"]', t, d }), P = p => this.puede(p);
      const ini = { t: '¡Bienvenido a SPE TPV!', d: 'Este sistema reúne los indicadores de gestión de Tripoliven. Le mostramos en un minuto para qué sirve cada parte que usted puede utilizar. Puede omitir la guía cuando quiera y repetirla desde el menú de su perfil.' };
      const ej = { sel: '[data-tour="ej-selector"]', t: 'Ejercicio fiscal', d: 'Todo el sistema se organiza por ejercicio fiscal (por ejemplo 2025-2026). Aquí elige cuál ver: así los registros de años distintos no se mezclan. Los ejercicios cerrados quedan de solo lectura.' };
      const menu = { sel: '[data-tour="menu-usuario"]', t: 'Su perfil', d: 'Desde aquí cambia su contraseña, vuelve a ver esta guía o cierra la sesión.' };
      const info = { sel: '.info', t: 'Botones «i»', d: 'Cada vez que vea un botón con una «i», tóquelo: explica el campo o el concepto en lenguaje sencillo.' };
      const fin = { t: '¡Listo!', d: 'Ya conoce lo esencial. Si tiene dudas, use los botones «i» o repita esta guía desde su perfil.' };
      const pasos = [ini];
      if (this.veMarcha) pasos.push({ sel: '[data-tour="marcha"]', t: 'Los pasos para arrancar', d: 'Cuentas, estructura, roles y personas, indicadores, período fiscal, meta y carga mensual. Cada paso muestra si ya está listo y el botón para hacerlo. Siga el orden.' });
      if (P('cargas.cargar')) pasos.push(
        { sel: '[data-tour="carga-selectores"]', t: 'Elija indicador y período', d: 'Seleccione el indicador que usted carga y el período a reportar. Los pendientes aparecen resaltados arriba.' },
        { sel: '[data-tour="carga-resultado"]', t: 'Resultado y semáforo automáticos', d: 'Digite solo los datos base: el sistema calcula el resultado y el semáforo. Si queda en alerta o crítico, deberá escribir el análisis y el plan de mejora.' });
      if (P('panel.ver')) pasos.push(
        { sel: '[data-tour="panel-rangos"]', t: 'Rango de fechas', d: 'Elija el período que quiere analizar. Solo incluye los indicadores que usted puede ver.' },
        { sel: '[data-tour="panel-atencion"]', t: 'Requiere atención', d: 'Indicadores críticos, en alerta y empeorando, o con cargas pendientes. Toque uno para abrir su ficha.' });
      const textos = {
        inicio: 'Su punto de partida: lo que tiene pendiente y el acceso directo a cada sección.', estructura: 'El árbol de gerencias, departamentos y jefaturas: de él depende quién ve qué.',
        roles: 'Cree roles y elija, con una matriz sencilla, qué puede hacer cada uno.', personas: 'Rol, posición en la estructura e indicadores de cada persona, con la vista de «qué ve».',
        fichas: 'Las fichas técnicas de los indicadores que usted puede ver; modifica solo las suyas.', meta: 'La meta de cada indicador por período.',
        carga: 'Registre mes a mes los datos de los indicadores que usted carga.', bandeja: 'Las cargas que le corresponde aprobar o devolver con observaciones.',
        recordatorios: 'Quién tiene cargas pendientes en su ámbito y un correo ya redactado para Outlook.', historial: 'Historial de las cargas que usted ve.',
        panel: 'Resultados, tendencias y mapa de calor de su ámbito.', reportes: 'Excel del informe general y de las fichas técnicas de lo que usted ve.',
        ejercicios: 'Al terminar el año, verifíquelo y ciérrelo: queda archivado en solo lectura.', importar: 'Traiga las fichas de años anteriores desde Excel.',
        config: 'Empresa, listas de apoyo, respaldo y soporte.', bitacora: 'Registro inalterable de todo lo que ocurre en el sistema.' };
      for (const n of this.nav()) pasos.push(nav(n.id, n.label, textos[n.id] || ''));
      return [...pasos, ej, info, menu, fin];
    },
    visible(sel) { return [...document.querySelectorAll(sel)].find(e => e.getClientRects().length > 0 && getComputedStyle(e).visibility !== 'hidden'); },
    async iniciarTour() {
      if (this.tour.on) return;
      this.menu = false; this.mas = false;
      const inicial = this.veMarcha ? 'inicio' : this.puede('cargas.cargar') ? 'carga' : this.puede('panel.ver') ? 'panel' : 'inicio';   // vista donde están los elementos explicados
      if (this.view !== inicial) await this.go(inicial);
      this.tour = { on: true, i: -1, pasos: this.pasosBase(), hole: null, pop: { top: 0, left: 0, w: 340 } };
      await this.pasoTour(1);
    },
    async pasoTour(dir) {
      let i = this.tour.i + dir; const P = this.tour.pasos;
      for (; i >= 0 && i < P.length; i += dir) {
        const p = P[i]; if (!p.sel) break;
        if (this.visible(p.sel) || (p.alt && this.visible(p.alt))) break;
      }
      if (i >= P.length) return this.terminarTour();
      return this.mostrarPaso(Math.max(0, i));
    },
    async mostrarPaso(i) {
      const p = this.tour.pasos[i], el = p.sel ? (this.visible(p.sel) || (p.alt && this.visible(p.alt))) : null;
      this.tour.i = i; this.tour.hole = null;
      if (el) {
        el.scrollIntoView({ block: 'center', inline: 'center' }); await new Promise(r => setTimeout(r, 80));
        const r = el.getBoundingClientRect(), m = 8; this.tour.hole = { top: r.top - m, left: r.left - m, w: r.width + 2 * m, h: r.height + 2 * m };
      }
      await this.$nextTick(); this.ubicarPopover();
    },
    ubicarPopover() {
      const W = Math.min(window.innerWidth - 24, 360), h = this.tour.hole, pop = this.$refs.tourpop, H = pop ? pop.offsetHeight : 200;
      let top, left;
      if (!h) { top = Math.max(12, (window.innerHeight - H) / 2); left = (window.innerWidth - W) / 2; }
      else {
        left = Math.min(Math.max(12, h.left + h.w / 2 - W / 2), window.innerWidth - W - 12);
        top = h.top + h.h + 14 + H < window.innerHeight ? h.top + h.h + 14 : Math.max(12, h.top - H - 14);
      }
      this.tour.pop = { top, left, w: W };
    },
    async terminarTour() {
      this.tour.on = false; this.tour.hole = null;
      if (!this.user.tour_visto) { try { await this.api('/api/tour', { method: 'POST', body: { visto: true } }, true); this.user.tour_visto = true; } catch { } }
    },
    get pasoTourActual() { return this.tour.pasos[this.tour.i] || { t: '', d: '' }; },
    get pasoEsUltimo() { return this.tour.i >= this.tour.pasos.length - 1; },
});
