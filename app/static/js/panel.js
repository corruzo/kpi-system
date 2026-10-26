/* Panel de análisis: indicadores clave, atención requerida, mapa de calor y gráficos del ejercicio. */
SIGT.modulos.panel = () => ({
    dash: null, panelArea: '', tendInd: null,

    // Ganchos: el núcleo los invoca al ingresar, al entrar a una vista y al salir.
    ganchos: {
      entrar: { panel() { return this.cargarPanel(); } },
    },

    kpis() {
      const r = this.dash.resumen, ant = this.dash.anterior, d = ant && r.sin_datos < r.total ? Math.round((r.cumplimiento - ant.cumplimiento) * 10) / 10 : null;
      return [
        { t: 'Indicadores', v: r.total, c: NAVY },
        { t: 'Cumplimiento', v: r.cumplimiento + '%', c: BRAND, sub: d === null ? (r.sin_datos === r.total ? 'Aún sin mediciones' : 'Sin ejercicio anterior') : `${d > 0 ? '▲' : d < 0 ? '▼' : '='} ${nf(Math.abs(d), 1)} pts vs ${ant.etiqueta}`, subc: d > 0 ? 'text-green-700' : d < 0 ? 'text-red-700' : 'text-slate-500' },
        { t: 'En verde', v: r.verde, c: SEM.verde }, { t: 'En alerta', v: r.amarillo, c: SEM.amarillo }, { t: 'Críticos', v: r.rojo, c: SEM.rojo },
        { t: 'Carga al día', v: r.carga_al_dia + '%', c: '#7c3aed', sub: r.faltantes ? `${r.faltantes} período(s) sin cargar` : 'Todo cargado', subc: r.faltantes ? 'text-amber-700' : 'text-green-700' }];
    },
    celdaClase: c => c ? ({ verde: 'bg-green-500 text-white', amarillo: 'bg-amber-400 text-slate-900', rojo: 'bg-red-500 text-white' }[c.semaforo]) : 'bg-slate-100 text-slate-300',
    tendTxt(t) { return !t ? '—' : `${t.delta > 0 ? '▲' : t.delta < 0 ? '▼' : '='} ${nf(Math.abs(t.delta), 2)}`; },
    tendClase(t) { return !t || t.mejora === null ? 'text-slate-400' : t.mejora ? 'text-green-700' : 'text-red-700'; },
    async cargarPanel() {
      const q = new URLSearchParams(); if (this.ejSel) q.set('ejercicio', this.ejSel); if (this.panelArea) q.set('area_id', this.panelArea);
      this.dash = await this.api('/api/dashboard?' + q);
      if (!this.dash.indicadores.some(i => i.id === this.tendInd)) this.tendInd = this.dash.indicadores.find(i => i.serie.length)?.id || this.dash.indicadores[0]?.id;
      this.$nextTick(() => this.dibujar());
    },
    dibujar() {
      if (!this.dash || typeof Chart === 'undefined') return;
      const nuevo = (id, cfg) => { const c = document.getElementById(id); if (!c) return; Chart.getChart(c)?.destroy(); new Chart(c, cfg); };
      Chart.defaults.font.family = 'ui-sans-serif, system-ui, "Segoe UI", sans-serif'; Chart.defaults.color = '#5f5d52'; Chart.defaults.borderColor = '#e8e5da';
      const r = this.dash.resumen, i = this.dash.indicadores.find(x => x.id === this.tendInd);
      if (i && i.serie.length) {
        const s = i.serie;
        nuevo('ch-tend', {
          type: 'line',
          data: {
            labels: s.map(p => p.etiqueta), datasets: [
              { label: 'Resultado', data: s.map(p => p.resultado), borderColor: BRAND, backgroundColor: BRAND, pointBackgroundColor: s.map(p => SEM[p.semaforo]), pointRadius: 6, pointBorderColor: '#fff', borderWidth: 2.5, tension: .25 },
              { label: 'Meta', data: s.map(p => p.meta), borderColor: NAVY, borderDash: [6, 4], pointRadius: 0, borderWidth: 2 },
              { label: 'Límite crítico', data: s.map(p => p.limite), borderColor: SEM.rojo, borderDash: [2, 4], pointRadius: 0, borderWidth: 1.5 }]
          },
          options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { usePointStyle: true, boxWidth: 8 } }, tooltip: { callbacks: { label: c => `${c.dataset.label}: ${this.fmt(c.parsed.y, i.unidad, i.decimales)}` } } }, scales: { y: { title: { display: true, text: i.unidad } }, x: { grid: { display: false } } } }
        });
      } else Chart.getChart(document.getElementById('ch-tend'))?.destroy();
      nuevo('ch-dist', {
        type: 'doughnut',
        data: { labels: ['Cumple', 'Alerta', 'Crítico', 'Sin datos'], datasets: [{ data: [r.verde, r.amarillo, r.rojo, r.sin_datos], backgroundColor: [SEM.verde, SEM.amarillo, SEM.rojo, SEM.sin_datos], borderWidth: 3, borderColor: '#fff' }] },
        options: { responsive: true, maintainAspectRatio: false, cutout: '68%', plugins: { legend: { position: 'bottom', labels: { usePointStyle: true, boxWidth: 8 } } } }
      });
      const A = this.dash.por_area, pct = k => A.map(a => Math.round(1000 * a[k] / a.total) / 10);
      const ds = [['Cumple', 'verde'], ['Alerta', 'amarillo'], ['Crítico', 'rojo']].map(([l, k]) => ({ type: 'bar', label: l, data: pct(k), backgroundColor: SEM[k], borderRadius: 6, borderSkipped: false }));
      if (this.dash.anterior) ds.push({ type: 'line', label: 'Cumplimiento ' + this.dash.anterior.etiqueta, data: A.map(a => a.cumplimiento_anterior), showLine: false, pointStyle: 'rectRot', pointRadius: 7, pointBackgroundColor: NAVY, pointBorderColor: '#fff', pointBorderWidth: 2 });
      nuevo('ch-area', {
        data: { labels: A.map(a => a.area), datasets: ds },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { usePointStyle: true, boxWidth: 8 } }, tooltip: { callbacks: { label: c => `${c.dataset.label}: ${c.parsed.y}%` } } }, scales: { x: { stacked: true, grid: { display: false } }, y: { stacked: true, max: 100, ticks: { callback: v => v + '%' } } } }
      });
    },
});
