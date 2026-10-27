/* Guía de bienvenida: recorrido paso a paso, según el rol, que explica cada botón y sección. */
SIGT.modulos.guia = () => ({
    tour: { on: false, i: 0, pasos: [], hole: null, pop: { top: 0, left: 0, w: 340 } },

    // Ganchos: el núcleo los invoca al ingresar, al entrar a una vista y al salir.
    ganchos: {
      listo() { if (!this.user.tour_visto) setTimeout(() => this.iniciarTour(), 900); },
    },

    pasosBase() {
      const r = this.user.rol, nav = (id, t, d) => ({ sel: `[data-tour="nav-${id}"]`, alt: '[data-tour="nav-_mas"]', t, d });
      const ini = { t: '¡Bienvenido al SGC • TRIPOLIVEN!', d: 'Este sistema reúne los indicadores de gestión de Tripoliven: cargar datos, aprobarlos, analizarlos y generar reportes. Le mostramos en un minuto para qué sirve cada parte. Puede omitir la guía cuando quiera y repetirla desde el menú de su perfil.' };
      const ej = { sel: '[data-tour="ej-selector"]', t: 'Ejercicio fiscal', d: 'Todo el sistema se organiza por ejercicio fiscal (por ejemplo 2025-2026). Aquí elige cuál ver: así los registros de años distintos no se mezclan. Los ejercicios cerrados quedan de solo lectura.' };
      const menu = { sel: '[data-tour="menu-usuario"]', t: 'Su perfil', d: 'Desde aquí cambia su contraseña, vuelve a ver esta guía o cierra la sesión.' };
      const info = { sel: '.info', t: 'Botones «i»', d: 'Cada vez que vea un botón con una «i», tóquelo: explica el campo o el concepto en lenguaje sencillo.' };
      const fin = { t: '¡Listo!', d: 'Ya conoce lo esencial. Si tiene dudas, use los botones «i» o repita esta guía desde su perfil.' };
      if (r === 'jefe') return [ini,
        { sel: '[data-tour="carga-selectores"]', t: 'Elija indicador y período', d: 'Seleccione el indicador de su área y el período a reportar. Los pendientes aparecen resaltados arriba.' },
        { sel: '[data-tour="carga-resultado"]', t: 'Resultado y semáforo automáticos', d: 'Digite solo los datos base: el sistema calcula el resultado y el semáforo. Si queda en alerta o crítico, deberá escribir el análisis y el plan de mejora.' },
        nav('inicio', 'Inicio', 'Su punto de partida: muestra lo que tiene pendiente y da acceso directo a cada sección.'),
        nav('carga', 'Carga rápida', 'Aquí registra mes a mes los datos de sus indicadores. Tarda menos de 2 minutos por indicador.'),
        nav('historial', 'Mis cargas', 'Consulte lo que ha enviado, su estado (en revisión, aprobado, devuelto) y las observaciones del auditor.'),
        nav('reportes', 'Reportes', 'Descargue en Excel las cargas y las fichas técnicas de su área.'), ej, info, menu, fin];
      if (r === 'gerente') return [ini,
        { sel: '[data-tour="panel-resumen"]', t: 'Estado del ejercicio', d: 'Resume el ejercicio elegido: avance del tiempo, cumplimiento y si ya está cerrado.' },
        { sel: '[data-tour="panel-atencion"]', t: 'Requiere atención', d: 'Indicadores críticos, en alerta y empeorando, o con cargas pendientes. Toque uno para abrir su ficha.' },
        { sel: '[data-tour="panel-mapa"]', t: 'Mapa de calor', d: 'Cada fila es un indicador y cada columna un mes del ejercicio: de un vistazo ve dónde están los problemas.' },
        nav('inicio', 'Inicio', 'Su punto de partida: muestra lo que tiene pendiente y da acceso directo a cada sección.'),
        nav('panel', 'Panel de análisis', 'Resultados, tendencias, comparativo con el año anterior y cumplimiento por departamento.'),
        nav('bandeja', 'Bandeja de aprobación', 'Las cargas enviadas por los jefes esperan aquí su aprobación o devolución con observaciones.'),
        nav('historial', 'Todas las cargas', 'Historial completo con filtros. Desde aquí puede agregar notas de auditoría o reabrir una carga aprobada con un error.'),
        nav('reportes', 'Reportes', 'Informe general en Excel y fichas técnicas en el formato del SGC.'),
        nav('ejercicios', 'Ejercicios fiscales', 'Consulte el estado de cada ejercicio y sus resultados finales.'), ej, info, menu, fin];
      return [ini,
        { sel: '[data-tour="fichas-nuevo"]', t: 'Crear indicadores', d: 'Aquí define cada indicador: proceso, responsables, fórmula, metas y semáforo. Los botones «i» y la guía de fórmulas le ayudan.' },
        nav('inicio', 'Inicio', 'Su punto de partida: muestra lo que tiene pendiente y da acceso directo a cada sección.'),
        nav('fichas', 'Indicadores', 'Fichas técnicas: cree, edite, duplique, archive y vea cada indicador.'),
        nav('panel', 'Panel de análisis', 'Resumen del ejercicio, mapa de calor, atención requerida y comparativo con el año anterior.'),
        nav('bandeja', 'Bandeja de aprobación', 'Cargas pendientes de revisión.'),
        nav('carga', 'Cargar datos', 'Como administrador puede cargar datos de cualquier área.'),
        nav('historial', 'Todas las cargas', 'Historial con filtros, notas de auditoría y reapertura de cargas.'),
        nav('reportes', 'Reportes', 'Excel del informe general y de las fichas técnicas.'),
        nav('ejercicios', 'Ejercicios fiscales', 'Cierre cada ejercicio cuando termine: queda archivado en solo lectura y el siguiente empieza limpio.'),
        nav('org', 'Organización', 'Áreas, usuarios, listas de apoyo y parámetros: ejercicio fiscal y logo de la empresa.'),
        nav('importar', 'Importar', 'Traiga al sistema las fichas de años anteriores desde Excel.'),
        nav('bitacora', 'Bitácora', 'Registro inalterable de todo lo que ocurre en el sistema. Solo usted puede verlo.'), ej, info, menu, fin];
    },
    visible(sel) { return [...document.querySelectorAll(sel)].find(e => e.getClientRects().length > 0 && getComputedStyle(e).visibility !== 'hidden'); },
    async iniciarTour() {
      if (this.tour.on) return;
      this.menu = false; this.mas = false;
      const inicial = { jefe: 'carga', gerente: 'panel', admin: 'fichas' }[this.user.rol];   // vista donde están los elementos explicados
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
