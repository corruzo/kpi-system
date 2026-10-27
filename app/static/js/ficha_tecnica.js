/* Ficha técnica en pantalla: el mismo contenido de la ficha en papel, por ejercicio fiscal. */
SIGT.modulos.ficha_tecnica = () => ({
    fv: { id: null, ejercicio: '', data: null },

    async verFicha(id, ejercicio = this.ejSel || '') {
      this.fv = { id, ejercicio, data: null, volver: this.view };
      await this.go('ficha'); await this.cargarFicha();
    },
    async cargarFicha() {
      this.fv.data = await this.api(`/api/indicadores/${this.fv.id}/ficha` + (this.fv.ejercicio ? `?ejercicio=${this.fv.ejercicio}` : ''));
      this.fv.ejercicio = this.fv.data.ejercicio;
      this.$nextTick(() => this.dibujarFicha());
    },
    fichaDescargar() { return this.descargar(`/api/reportes/fichas.xlsx?indicador_id=${this.fv.id}&ejercicio=${this.fv.ejercicio}`, 'ficha_sgc_tripoliven.xlsx'); },
    valorFicha(p, clave) { const m = p.medicion; return m && m.estado !== 'observado' && m.valores[clave] !== undefined ? nf(m.valores[clave], 2) : ''; },
    semaforoFranjas(i) {
      const f = x => (x === null || x === undefined) ? '' : this.fmt(x, i.unidad, i.decimales), mayor = i.sentido === 'mayor';
      return [{ n: 'Verde', c: 'verde', min: mayor ? f(i.meta) : f(i.meta_tope), max: mayor ? f(i.meta_tope) : f(i.meta) },
      { n: 'Amarillo', c: 'amarillo', min: mayor ? f(i.limite) : f(i.limite_tope), max: mayor ? f(i.limite_tope) : f(i.limite) },
      { n: 'Rojo', c: 'rojo', min: mayor ? '< ' + f(i.limite) : (i.limite_tope !== null ? '< ' + f(i.limite_tope) : ''), max: mayor ? (i.limite_tope !== null ? '> ' + f(i.limite_tope) : '') : '> ' + f(i.limite) }];
    },
    formulaDoc(i) {
      let t = i.formula; const todos = [...i.variables, ...(i.constantes || [])];
      todos.sort((a, b) => b.clave.length - a.clave.length).forEach(v => t = t.replace(new RegExp('\\b' + v.clave + '\\b', 'g'), v.clave.toUpperCase()));
      return [`${i.sigla || 'IND'} = ${t}`, ...i.variables.map(v => `${v.clave.toUpperCase()} = ${v.etiqueta}`), ...(i.constantes || []).map(c => `${c.clave.toUpperCase()} = ${c.etiqueta} (${c.valor})`)].join('\n');
    },
    dibujarFicha() {
      const d = this.fv.data, c = document.getElementById('ch-ficha');
      if (!d || !c || typeof Chart === 'undefined') return;
      Chart.getChart(c)?.destroy();
      const i = d.indicador, ps = d.periodos.filter(p => p.medicion && p.medicion.estado !== 'observado'), mayor = i.sentido === 'mayor';
      const linea = (l, v, col) => ({ label: l, data: ps.map(() => v), borderColor: col, borderDash: [6, 4], pointRadius: 0, borderWidth: 2 });
      const ds = [{ label: 'Indicador', data: ps.map(p => p.medicion.resultado), borderColor: BRAND, backgroundColor: BRAND, pointBackgroundColor: ps.map(p => SEM[p.medicion.semaforo]), pointRadius: 6, borderWidth: 2, tension: 0 }];
      const mn = mayor ? i.meta : i.meta_tope, mx = mayor ? i.meta_tope : i.meta;
      if (mn !== null && mn !== undefined) ds.push(linea('Mín.', mn, SEM.verde)); if (mx !== null && mx !== undefined) ds.push(linea('Máx.', mx, SEM.rojo));
      new Chart(c, { type: 'line', data: { labels: ps.map(p => p.corta), datasets: ds }, options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } } });
    },
});
