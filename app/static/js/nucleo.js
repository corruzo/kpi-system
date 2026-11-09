/* Núcleo: arranque, comunicación con la API, avisos, descargas y navegación entre vistas. */
SIGT.modulos.nucleo = () => ({
    ready: false, view: '', busy: false, menu: false, mas: false,
    pendientes: 0, cargando: false, _tc: null, sinConexion: !navigator.onLine, fallaArranque: '',
    toast: { msg: '', error: false }, _toastT: null,

    // ------------------------------------------------------------ arranque
    async init() {
      // Cualquier error no controlado se avisa al usuario (y se deja en la consola) en lugar de fallar en silencio.
      addEventListener('online', () => { this.sinConexion = false; this.avisar('Conexión restablecida.'); });
      addEventListener('offline', () => { this.sinConexion = true; });
      addEventListener('unhandledrejection', ev => { ev.preventDefault(); console.error(ev.reason); if (!ev.reason?.avisado) this.avisar('Ocurrió un error inesperado. Si continúa, recargue la página.', true); });
      // Una sola petición trae el usuario y todo lo que la interfaz necesita (en paralelo con la marca del ingreso).
      const marca = fetch('/api/publico').then(r => r.json()).then(m => { this.marca = m; }).catch(() => { });
      try { await this.abrirSesion(true); }
      catch (e) {
        this.user = null;
        if (e.estado !== 401) { this.fallaArranque = e.message; return; }   // sin sesión es normal (login); otra causa es una falla real
      }
      await marca;
      this.ready = true;
      this.$nextTick(() => { if (!this.user) SIGT_ANIM.pantalla(document.querySelector('[data-vista="login"]')); });
    },
    // Tras ingresar: cada módulo carga sus datos (ganchos «ingreso»), se abre la vista inicial del rol y se avisa a «listo».
    async abrirSesion(silencioso = false) {
      // UNA petición trae todo lo de ingreso (usuario, parámetros, ejercicios, indicadores, áreas, bandeja, listas…).
      let preferido = null; try { preferido = Number(localStorage.getItem('sigt_ej')) || null; } catch { }
      const d = await this.api('/api/arranque' + (preferido ? '?ejercicio=' + preferido : ''), {}, silencioso);
      this.user = d.usuario; this.params = d.parametros;
      this.aplicarEjercicios(d.ejercicios.ejercicios); this.ejVigente = d.ejercicios.vigente; this.ejSel = d.ejercicio;
      this.indicadores = d.indicadores; this.areas = d.areas || [];
      this.bandejaN = d.bandeja_total || 0; this.bandejaEj = d.bandeja_ejercicios || []; this.catalogos = d.catalogos || []; this.usuarios = [];
      this.marcha = d.marcha || null; this.resumenInicio = d.resumen || null; this._inicioListo = true;   // la pantalla de inicio ya tiene sus datos
      for (const cargar of this.ganchos.ingreso) await cargar.call(this);   // lo que no viene en el arranque (p. ej. valores por defecto)
      await this.go(VISTA_INICIAL);
      for (const f of this.ganchos.listo) await f.call(this);
    },

    // ------------------------------------------------------------ comunicación
    // Toda llamada a la API pasa por aquí: siempre termina en datos válidos o en un Error con un mensaje claro en español
    // (sin conexión, tiempo agotado, respuesta que no es JSON, error del servidor…), ya mostrado al usuario salvo `silencioso`.
    async api(url, opt = {}, silencioso = false) {
      const { conTotal, ...resto } = opt;   // conTotal: devuelve {items, total} con el total de `X-Total-Count`
      const o = { credentials: 'same-origin', ...resto };
      if (o.body && typeof o.body !== 'string' && !(o.body instanceof FormData)) { o.body = JSON.stringify(o.body); o.headers = { 'Content-Type': 'application/json' }; }
      const falla = (msg, estado) => { if (!silencioso) this.avisar(msg, true); return Object.assign(new Error(msg), { avisado: true, estado }); };
      const control = new AbortController(), plazo = setTimeout(() => control.abort(), 60000);
      this.iniciarCarga();
      let r;
      try { r = await fetch(url, { ...o, signal: control.signal }); }
      catch (e) { throw falla(e.name === 'AbortError' ? 'El servidor tardó demasiado en responder. Intente de nuevo.' : 'No hay conexión con el servidor. Revise su internet e intente de nuevo.'); }
      finally { clearTimeout(plazo); this.terminarCarga(); }
      if (!r.ok) {
        let d = {}; try { d = await r.json(); } catch { }
        let msg = d.detail || (r.status >= 500 ? `El servidor tuvo un problema (código ${r.status}). Intente de nuevo en unos segundos.` : 'Error inesperado.');
        if (Array.isArray(msg)) msg = msg.map(e => e.msg).join('; ');
        if (r.status === 401 && this.user) { this.user = null; this.avisar('Su sesión expiró.', true); throw Object.assign(new Error(msg), { avisado: true, estado: 401 }); }
        throw falla(msg, r.status);
      }
      try {
        const datos = await r.json();
        return conTotal ? { items: datos, total: Number(r.headers.get('X-Total-Count')) || datos.length } : datos;
      } catch { throw falla('La respuesta del servidor no es válida. Recargue la página.', r.status); }
    },
    // ------------------------------------------------------------ paginación (en el servidor)
    // Cada lista larga pide solo su página (`limite`/`desde`) y recibe el total en `X-Total-Count`: nunca se descarga todo.
    // El estado de cada lista vive en pag[clave] = {pagina, por, total}; el paginador (componentes/paginador.html) lo usa.
    pag: {},
    pg(k) { if (!this.pag[k]) this.pag[k] = { pagina: 1, por: 25, total: 0 }; return this.pag[k]; },   // siempre vía el proxy reactivo (con ||= la 1.ª vez devolvería el objeto crudo)
    // Pide la página `pagina` de la lista `k` en `url` (que puede traer ya otros filtros) y deja actualizado su estado.
    async pedirPagina(k, url, pagina = 1) {
      const p = this.pg(k), n = Math.max(1, pagina);
      const r = await this.api(url + (url.includes('?') ? '&' : '?') + `limite=${p.por}&desde=${(n - 1) * p.por}`, { conTotal: true });
      p.total = r.total;
      const ultima = this.totalPaginas(k);
      if (r.items.length === 0 && n > 1 && n > ultima) return this.pedirPagina(k, url, ultima);   // la última página quedó vacía (se borraron registros)
      p.pagina = n; return r.items;
    },
    totalPaginas(k) { const p = this.pg(k); return Math.max(1, Math.ceil(p.total / p.por)); },
    rangoPagina(k) { const p = this.pg(k); return p.total ? `${(p.pagina - 1) * p.por + 1}–${Math.min(p.pagina * p.por, p.total)} de ${p.total}` : ''; },
    // Números de página a mostrar: primera, última y las vecinas de la actual, con «…» en los saltos
    botonesPagina(k) {
      const t = this.totalPaginas(k), a = this.pg(k).pagina, set = new Set([1, t, a - 1, a, a + 1]), r = [];
      let prev = 0;
      for (const n of [...set].filter(n => n >= 1 && n <= t).sort((x, y) => x - y)) { if (n - prev > 1) r.push({ key: 'e' + n, gap: true }); r.push({ key: 'n' + n, n }); prev = n; }
      return r;
    },
    irPagina(k, n) { if (n >= 1 && n <= this.totalPaginas(k) && n !== this.pg(k).pagina) return this[CARGADORES[k]](n); },
    cambiarPorPagina(k, v) { this.pg(k).por = Number(v); return this[CARGADORES[k]](1); },
    // Barra de progreso global: se muestra si alguna petición tarda más de 0,2 s
    iniciarCarga() { this.pendientes++; if (!this._tc) this._tc = setTimeout(() => { this.cargando = this.pendientes > 0; }, 200); },
    terminarCarga() { if (--this.pendientes <= 0) { this.pendientes = 0; clearTimeout(this._tc); this._tc = null; this.cargando = false; } },
    // Chart.js (200 KB) se baja solo cuando una pantalla necesita gráficos
    cargarGraficos() {
      if (window.Chart) return Promise.resolve();
      return this._graficos ||= new Promise((ok, no) => {
        const s = document.createElement('script'); s.src = document.querySelector('meta[name="sgc-chart"]').content;
        s.onload = ok; s.onerror = () => { this._graficos = null; no(Object.assign(new Error('No se pudieron cargar los gráficos. Revise su conexión.'), { avisado: false })); };
        document.head.appendChild(s);
      });
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
      const r = this.user.rol, ver = (id, label, corto, badge) => ({ id, label, corto, grupo: GRUPOS_NAV[id], ...(badge ? { badge } : {}) });
      const secciones = {
        inicio: ver('inicio', r === 'admin' ? 'Puesta en marcha' : 'Inicio', 'Inicio'),
        carga: ver('carga', r === 'admin' ? 'Cargar datos' : 'Carga del mes', 'Cargar', this.pendientesTotal()),
        historial: ver('historial', r === 'jefe' ? 'Mis cargas' : 'Todas las cargas', r === 'jefe' ? 'Historial' : 'Cargas'),
        reportes: ver('reportes', 'Reportes', 'Reportes'),
        panel: ver('panel', 'Panel de control', 'Panel'),
        bandeja: ver('bandeja', 'Bandeja de aprobación', 'Bandeja', this.bandejaN),
        recordatorios: ver('recordatorios', 'Recordatorios de carga', 'Avisos'),
        ejercicios: ver('ejercicios', 'Cierre de años', 'Cierre'),
        presupuesto: ver('presupuesto', 'Período y presupuesto', 'Presup.'),
        fichas: ver('fichas', 'Indicadores', 'Fichas'),
        org: ver('org', 'Organización y equipo', 'Equipo'),
        importar: ver('importar', 'Importar', 'Importar'),
        bitacora: ver('bitacora', 'Bitácora', 'Bitácora'),
      };
      return MENU_POR_ROL[r].map(id => secciones[id]);
    },
    // Menú agrupado (barra lateral): [{grupo, items}] respetando el orden del flujo
    navGrupos() {
      const g = [];
      for (const n of this.nav()) { let x = g.find(y => y.grupo === (n.grupo || '')); if (!x) g.push(x = { grupo: n.grupo || '', items: [] }); x.items.push(n); }
      return g;
    },
    // En móvil: 4 accesos + «Más» cuando hay más de 5 secciones
    navMovil() { const n = this.nav(); return n.length > 5 ? [...n.slice(0, 4), { id: '_mas', label: 'Más', corto: 'Más', badge: n.slice(4).reduce((a, x) => a + (x.badge || 0), 0) || '' }] : n; },
    navMas() { return this.nav().slice(4); },
    navMasGrupos() {
      const g = [];
      for (const n of this.navMas()) { let x = g.find(y => y.grupo === (n.grupo || '')); if (!x) g.push(x = { grupo: n.grupo || '', items: [] }); x.items.push(n); }
      return g;
    },
    dockActivo(n) { return n.id === '_mas' ? (this.masActivo || this.mas) : (this.view === n.id && !this.mas); },
    get masActivo() { return this.navMas().some(n => n.id === this.view); },
    async go(vista) {
      this.view = vista; this.menu = false; this.mas = false;
      window.scrollTo({ top: 0 });
      this.$nextTick(() => { document.querySelector('.pill-on')?.scrollIntoView({ inline: 'nearest', block: 'nearest' }); SIGT_ANIM.indicadores(); });   // el menú largo se desplaza hasta la sección activa
      for (const cargar of this.ganchos.entrar[vista] || []) await cargar.call(this);
      this.$nextTick(() => SIGT_ANIM.pantalla(document.querySelector(`[data-vista="${vista}"]`)));
    },
});
