/* Núcleo: arranque, comunicación con la API, avisos, descargas y navegación entre vistas. */
SIGT.modulos.nucleo = () => ({
    ready: false, view: '', busy: false, menu: false, mas: false,
    toast: { msg: '', error: false }, _toastT: null,

    // ------------------------------------------------------------ arranque
    async init() {
      try { this.marca = await (await fetch('/api/publico')).json(); } catch { }
      try { this.user = await this.api('/api/me', {}, true); await this.abrirSesion(); }
      catch { this.user = null; }
      this.ready = true;
    },
    // Tras ingresar: cada módulo carga sus datos (ganchos «ingreso»), se abre la vista inicial del rol y se avisa a «listo».
    async abrirSesion() {
      for (const cargar of this.ganchos.ingreso) await cargar.call(this);
      await this.go(VISTA_INICIAL);
      for (const f of this.ganchos.listo) await f.call(this);
    },

    // ------------------------------------------------------------ comunicación
    async api(url, opt = {}, silencioso = false) {
      const o = { credentials: 'same-origin', ...opt };
      if (o.body && typeof o.body !== 'string') { o.body = JSON.stringify(o.body); o.headers = { 'Content-Type': 'application/json' }; }
      const r = await fetch(url, o);
      if (!r.ok) {
        let d = {}; try { d = await r.json(); } catch { }
        let msg = d.detail || 'Error inesperado.';
        if (Array.isArray(msg)) msg = msg.map(e => e.msg).join('; ');
        if (r.status === 401 && this.user) { this.user = null; this.avisar('Su sesión expiró.', true); }
        else if (!silencioso) this.avisar(msg, true);
        throw new Error(msg);
      }
      return r.json();
    },
    avisar(msg, error = false) {
      this.toast = { msg, error }; clearTimeout(this._toastT);
      this._toastT = setTimeout(() => this.toast.msg = '', 4500);
    },
    async descargar(url, nombreDef) {
      this.busy = true;
      try {
        const r = await fetch(url, { credentials: 'same-origin' });
        if (!r.ok) { let d = {}; try { d = await r.json(); } catch { } throw new Error(d.detail || 'No se pudo generar el archivo.'); }
        const nombre = (r.headers.get('content-disposition') || '').match(/filename="?([^";]+)/)?.[1] || nombreDef;
        const a = document.createElement('a'); a.href = URL.createObjectURL(await r.blob()); a.download = nombre; document.body.appendChild(a); a.click(); a.remove();
        setTimeout(() => URL.revokeObjectURL(a.href), 4000); this.avisar('Reporte descargado.');
      } catch (e) { this.avisar(e.message, true); }
      this.busy = false;
    },

    // ------------------------------------------------------------ navegación
    // Menú por rol: fuente única de las secciones, su orden y sus insignias.
    nav() {
      const r = this.user.rol, ver = (id, label, corto, badge) => ({ id, label, corto, ...(badge ? { badge } : {}) });
      const secciones = {
        inicio: ver('inicio', 'Inicio', 'Inicio'),
        carga: ver('carga', r === 'admin' ? 'Cargar datos' : 'Carga rápida', 'Cargar', this.pendientesTotal()),
        historial: ver('historial', r === 'jefe' ? 'Mis cargas' : 'Todas las cargas', r === 'jefe' ? 'Historial' : 'Cargas'),
        reportes: ver('reportes', 'Reportes', 'Reportes'),
        panel: ver('panel', 'Panel de análisis', 'Panel'),
        bandeja: ver('bandeja', 'Bandeja de aprobación', 'Bandeja', this.bandeja.length),
        ejercicios: ver('ejercicios', 'Ejercicios fiscales', 'Ejercicios'),
        fichas: ver('fichas', 'Indicadores', 'Fichas'),
        org: ver('org', 'Organización', 'Equipo'),
        importar: ver('importar', 'Importar', 'Importar'),
        bitacora: ver('bitacora', 'Bitácora', 'Bitácora'),
      };
      return MENU_POR_ROL[r].map(id => secciones[id]);
    },
    // En móvil: 4 accesos + «Más» cuando hay más de 5 secciones
    navMovil() { const n = this.nav(); return n.length > 5 ? [...n.slice(0, 4), { id: '_mas', label: 'Más', corto: 'Más', badge: n.slice(4).reduce((a, x) => a + (x.badge || 0), 0) || '' }] : n; },
    navMas() { return this.nav().slice(4); },
    get masActivo() { return this.navMas().some(n => n.id === this.view); },
    async go(vista) {
      this.view = vista; this.menu = false; this.mas = false;
      window.scrollTo({ top: 0 });
      this.$nextTick(() => document.querySelector('.pill-on')?.scrollIntoView({ inline: 'nearest', block: 'nearest' }));   // el menú largo se desplaza hasta la sección activa
      for (const cargar of this.ganchos.entrar[vista] || []) await cargar.call(this);
    },
});
