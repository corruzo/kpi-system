/* Reportes en Excel: informe general y fichas técnicas. */
SIGT.modulos.reportes = () => ({
    rep: { anio: '', area_id: '', estado: '' }, repFicha: { area_id: '', indicador_id: '' },

    // Ganchos: el núcleo los invoca al ingresar, al entrar a una vista y al salir.
    ganchos: {
      ejercicio() { this.rep.anio = this.ejSel || ''; },
      ingreso() { this.rep.anio = this.ejSel || ''; },
      entrar: { async reportes() { if (this.user.rol !== 'jefe' && !this.areas.length) await this.cargarAreas(); } },
    },

    descargarFichas() {
      const q = new URLSearchParams(); if (this.rep.anio) q.set('ejercicio', this.rep.anio);
      for (const [k, v] of Object.entries(this.repFicha)) if (v) q.set(k, v);
      if (this.user.rol !== 'jefe' && this.rep.area_id && !this.repFicha.area_id) q.set('area_id', this.rep.area_id);
      return this.descargar('/api/reportes/fichas.xlsx?' + q, 'fichas_sgc_tripoliven.xlsx');
    },
    verif: null,
    async verificarArchivo(ev) {
      const f = ev.target.files[0]; ev.target.value = ''; if (!f) return;
      const fd = new FormData(); fd.append('archivo', f); this.busy = true; this.verif = null;
      try { this.verif = await this.api('/api/reportes/verificar', { method: 'POST', body: fd }); } catch { }
      this.busy = false;
    },
    descargarReporte() {
      const q = new URLSearchParams(); for (const [k, v] of Object.entries(this.rep)) if (v) q.set(k, v);
      return this.descargar('/api/reportes/general.xlsx?' + q, 'reporte_sgc_tripoliven.xlsx');
    },
});
