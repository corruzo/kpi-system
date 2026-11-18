/* Importación de fichas históricas desde Excel (vista previa editable y confirmación). */
SIGT.modulos.importacion = () => ({
    imp: { prev: null, sel: {}, res: null, crearAreas: true, cargando: false },

    async analizarExcel(ev) {
      const f = ev.target.files[0]; if (!f) return;
      this.imp = { prev: null, sel: {}, res: null, crearAreas: true, cargando: true };
      try {
        const fd = new FormData(); fd.append('archivo', f);
        const r = await fetch('/api/importar/excel', { method: 'POST', body: fd, credentials: 'same-origin' });
        const d = await r.json(); if (!r.ok) throw new Error(typeof d.detail === 'string' ? d.detail : 'No se pudo leer el archivo.');
        this.imp.prev = d; this.imp.sel = Object.fromEntries(d.indicadores.map((_, k) => [k, !!d.indicadores[k].formula]));
      } catch (e) { this.avisar(e.message, true); }
      this.imp.cargando = false; ev.target.value = '';
    },
    get impInicioDistinto() { const p = this.imp.prev; return !!p && p.indicadores.some(i => i.frecuencia !== 'mensual' && i.frecuencia !== 'eventual' && i.mediciones.length) && p.inicio_ejercicio && p.inicio_ejercicio !== p.inicio_actual; },
    get impSeleccion() { return this.imp.prev ? this.imp.prev.indicadores.filter((_, k) => this.imp.sel[k]) : []; },
    async confirmarImportacion() {
      const p = this.imp.prev; this.busy = true;
      try {
        const inds = this.impSeleccion;
        const nuevas = new Set(inds.filter(i => !i.area_existe).map(i => i.area));
        if (this.imp.crearAreas) (p.areas || []).forEach(a => nuevas.add(a));
        const cuerpo = { archivo: p.archivo, inicio_ejercicio: p.inicio_ejercicio, indicadores: inds.map(i => ({ ...i, objetivo: i.objetivo || '' })), areas_nuevas: [...nuevas] };
        this.imp.res = await this.api('/api/importar/confirmar', { method: 'POST', body: cuerpo });
        this.imp.prev = null; await this.cargarIndicadores(); await this.refrescarUnidades(); this.avisar('Importación completada.');
      } catch { }
      this.busy = false;
    },
});
