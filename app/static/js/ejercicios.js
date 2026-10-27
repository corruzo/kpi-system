/* Ejercicios fiscales: selector global, listado, verificación, cierre y reapertura. */
SIGT.modulos.ejercicios = () => ({
    ejLista: [], ejSel: null, ejVigente: null, ejVista: [],
    cierre: { abierto: false, e: null, v: null, nota: '', aceptar: false },
    reap: { abierto: false, e: null, nota: '' },

    // Ganchos: el núcleo los invoca al ingresar, al entrar a una vista y al salir.
    ganchos: {
      ingreso() { return this.cargarEjercicios(); },
      entrar: { ejercicios() { return this.cargarEjerciciosVista(); } },
    },

    async cargarEjercicios() {
      const r = await this.api('/api/ejercicios'); this.ejLista = r.ejercicios; this.ejVigente = r.vigente;
      let g = null; try { g = Number(localStorage.getItem('sigt_ej')); } catch { }
      this.ejSel = this.ejLista.some(e => e.anio === g) ? g : r.vigente;
    },
    get ejercicios() { return this.ejLista.map(e => ({ valor: e.anio, etiqueta: e.etiqueta })); },
    get ejActual() { return this.ejLista.find(e => e.anio === this.ejSel) || {}; },
    estadoEj: e => ({ vigente: 'Vigente', terminado: 'Terminado · por cerrar', cerrado: 'Cerrado', futuro: 'Próximo' }[e] || e),
    claseEj: e => ({ vigente: 'border-green-300 bg-green-50 text-green-800', terminado: 'border-amber-300 bg-amber-50 text-amber-800', cerrado: 'border-slate-300 bg-slate-100 text-slate-700', futuro: 'border-sky-300 bg-sky-50 text-sky-800' }[e] || ''),
    // El ejercicio elegido gobierna TODAS las pantallas de datos: cada módulo recarga lo suyo (gancho «ejercicio»)
    // y se vuelve a abrir la vista actual, de modo que nunca quede información de otro ejercicio en pantalla.
    async cambiarEjercicio() {
      try { localStorage.setItem('sigt_ej', String(this.ejSel)); } catch { }
      for (const recargar of this.ganchos.ejercicio) await recargar.call(this);
      if (this.view === 'ficha') { this.fv.ejercicio = this.ejSel; await this.cargarFicha(); }
      else if (!['ejercicios', 'org', 'importar', 'bitacora'].includes(this.view)) await this.go(this.view);
      this.avisar('Ejercicio ' + this.ejActual.etiqueta + (this.ejActual.estado === 'cerrado' ? ' (cerrado, solo lectura)' : ''));
    },
    volverAlVigente() { this.ejSel = this.ejVigente; return this.cambiarEjercicio(); },
    // ¿La pantalla muestra datos de un ejercicio distinto al vigente? (para el aviso de contexto)
    get viendoOtroEjercicio() { return this.ejVigente && this.ejSel !== this.ejVigente && !['ejercicios', 'org', 'importar', 'bitacora', 'fichas'].includes(this.view); },
    async cargarEjerciciosVista() { const r = await this.api('/api/ejercicios?detalle=1'); this.ejVista = r.ejercicios; this.ejLista = r.ejercicios; },
    get ejTerminados() { return this.ejLista.filter(e => e.estado === 'terminado'); },
    get anchoAmplio() { return window.innerWidth >= 640; },
    get ejPorCerrar() { return this.ejVista.filter(e => e.estado === 'terminado'); },
    async abrirCierre(e) {
      this.cierre = { abierto: true, e, v: null, nota: '', aceptar: false };
      try { this.cierre.v = await this.api(`/api/ejercicios/${e.anio}/verificacion`); } catch { this.cierre.abierto = false; }
    },
    async confirmarCierre() {
      this.busy = true;
      try { await this.api(`/api/ejercicios/${this.cierre.e.anio}/cerrar`, { method: 'POST', body: { nota: this.cierre.nota, aceptar_faltantes: this.cierre.aceptar } }); this.cierre.abierto = false; this.avisar('Ejercicio cerrado y archivado.'); await this.cargarEjerciciosVista(); } catch { }
      this.busy = false;
    },
    async confirmarReapertura() {
      this.busy = true;
      try { await this.api(`/api/ejercicios/${this.reap.e.anio}/reabrir`, { method: 'POST', body: { nota: this.reap.nota } }); this.reap.abierto = false; this.avisar('Ejercicio reabierto.'); await this.cargarEjerciciosVista(); } catch { }
      this.busy = false;
    },
    async verEjercicio(e) { this.ejSel = e.anio; await this.cambiarEjercicio(); return this.go('panel'); },
    descargarEjercicio(e) { return this.descargar('/api/reportes/general.xlsx?anio=' + e.anio, `reporte_${e.etiqueta}.xlsx`); },
    descargarFichasEjercicio(e) { return this.descargar('/api/reportes/fichas.xlsx?ejercicio=' + e.anio, `fichas_${e.etiqueta}.xlsx`); },
});
