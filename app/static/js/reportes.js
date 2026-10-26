/* Reportes en Excel: informe general y fichas técnicas. */
SIGT.modulos.reportes = () => ({
    rep: { anio: '', area_id: '', estado: '' }, repFicha: { area_id: '', indicador_id: '' },

    // Ganchos: el núcleo los invoca al ingresar, al entrar a una vista y al salir.
    ganchos: {
      entrar: { async reportes() { if (this.user.rol !== 'jefe' && !this.areas.length) await this.cargarAreas(); } },
    },

    descargarFichas() {
      const q = new URLSearchParams(); if (this.rep.anio) q.set('ejercicio', this.rep.anio);
      for (const [k, v] of Object.entries(this.repFicha)) if (v) q.set(k, v);
      if (this.user.rol !== 'jefe' && this.rep.area_id && !this.repFicha.area_id) q.set('area_id', this.rep.area_id);
      return this.descargar('/api/reportes/fichas.xlsx?' + q, 'fichas_sigt.xlsx');
    },
    descargarReporte() {
      const q = new URLSearchParams(); for (const [k, v] of Object.entries(this.rep)) if (v) q.set(k, v);
      return this.descargar('/api/reportes/general.xlsx?' + q, 'reporte_sigt.xlsx');
    },
});
