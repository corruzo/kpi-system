/* Panel de control: todo el sistema por rango de fechas y granularidad (mes, trimestre…), con filtros, gráficos, rankings,
   mapa de calor y tabla exportable. Los datos los calcula el servidor (/api/tablero); aquí solo se pintan. */
const PANEL_PRESETS = [['mes', 'Este mes'], ['3m', 'Últimos 3 meses'], ['6m', 'Últimos 6 meses'], ['ejercicio', 'Ejercicio elegido'], ['anterior', 'Ejercicio anterior'], ['todo', 'Todo (5 años)']];
const PANEL_GRANOS = [['mes', 'Mensual'], ['bimestre', 'Bimestral'], ['trimestre', 'Trimestral'], ['cuatrimestre', 'Cuatrimestral'], ['semestre', 'Semestral'], ['anio', 'Anual']];
const PANEL_FREC = [['', 'Todas las frecuencias'], ['mensual', 'Mensual'], ['bimestral', 'Bimestral'], ['trimestral', 'Trimestral'], ['cuatrimestral', 'Cuatrimestral'], ['semestral', 'Semestral'], ['anual', 'Anual'], ['eventual', 'Eventual']];
const PANEL_DIM = [['area', 'Área'], ['gerencia', 'Gerencia'], ['seguimiento', 'Tipo de seguimiento'], ['frecuencia', 'Frecuencia'], ['proceso', 'Proceso / objetivo']];
const AZ = '#006bff', MAG = '#e55cff', GRIS = '#a6bbd1';

SIGT.modulos.panel = () => ({
    pf: { preset: 'ejercicio', desde: '', hasta: '', agrupar: 'mes', area_id: '', frecuencia: '', seguimiento: '', indicador_id: '', solo_aprobadas: false, dimension: 'area', metrica: 'semaforo' },
    tb: null, tendInd: null, filtrosAbiertos: false, cargandoTablero: false, orden: { col: 'pct_verde', asc: true },
    PANEL_PRESETS, PANEL_GRANOS, PANEL_FREC, PANEL_DIM,

    // Ganchos: el núcleo los invoca al ingresar, al entrar a una vista y al salir.
    ganchos: {
      entrar: { panel() { return this.iniciarPanel(); } },
      salida() { this.tb = null; },
    },

    // ------------------------------------------------------------ filtros y rangos
    iniciarPanel() {
      try { Object.assign(this.pf, JSON.parse(localStorage.getItem('sigt_panel') || '{}')); } catch { }
      if (!this.pf.desde || this.pf.preset !== 'personalizado') this.aplicarPreset(this.pf.preset === 'personalizado' ? 'ejercicio' : this.pf.preset, false);
      return this.cargarTablero();
    },
    ym: d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`,
    sumaMeses(ym, n) { const [y, m] = ym.split('-').map(Number), d = new Date(y, m - 1 + n, 1); return this.ym(d); },
    aplicarPreset(k, cargar = true) {
      const hoy = this.ym(new Date()), ej = this.ejActual, ini = (ej.desde || '').slice(0, 7), fin = (ej.hasta || '').slice(0, 7);
      const r = {
        mes: [hoy, hoy], '3m': [this.sumaMeses(hoy, -2), hoy], '6m': [this.sumaMeses(hoy, -5), hoy],
        ejercicio: [ini || this.sumaMeses(hoy, -11), fin || hoy],
        anterior: [ini ? this.sumaMeses(ini, -12) : this.sumaMeses(hoy, -23), fin ? this.sumaMeses(fin, -12) : this.sumaMeses(hoy, -12)],
        todo: [this.sumaMeses(fin || hoy, -59), fin || hoy],
      }[k] || [ini, fin];
      [this.pf.desde, this.pf.hasta] = r; this.pf.preset = k;
      if (k === 'todo' || k === 'ejercicio' || k === 'anterior') this.pf.agrupar = k === 'todo' ? 'anio' : this.pf.agrupar;
      return cargar ? this.cargarTablero() : null;
    },
    cambioFiltro(personalizado = false) { if (personalizado) this.pf.preset = 'personalizado'; return this.cargarTablero(); },
    restablecerPanel() { this.pf = { ...this.pf, area_id: '', frecuencia: '', seguimiento: '', indicador_id: '', solo_aprobadas: false, agrupar: 'mes', dimension: 'area', metrica: 'semaforo' }; return this.aplicarPreset('ejercicio'); },
    get hayFiltros() { const f = this.pf; return !!(f.area_id || f.frecuencia || f.seguimiento || f.indicador_id || f.solo_aprobadas); },
    get rangoTexto() { const r = this.tb?.rango; return r ? `${this.fechaCorta(r.desde)} – ${this.fechaCorta(r.hasta)} · ${r.meses} mes${r.meses === 1 ? '' : 'es'}` : ''; },

    async cargarTablero() {
      const f = this.pf, q = new URLSearchParams({ desde: f.desde, hasta: f.hasta, agrupar: f.agrupar, dimension: f.dimension });
      for (const k of ['area_id', 'frecuencia', 'seguimiento', 'indicador_id']) if (f[k]) q.set(k, f[k]);
      if (f.solo_aprobadas) q.set('solo_aprobadas', 'true');
      try { localStorage.setItem('sigt_panel', JSON.stringify(f)); } catch { }
      this.cargandoTablero = true;
      try {
        this.tb = await this.api('/api/tablero?' + q);
        if (!this.tb.indicadores.some(i => i.id === this.tendInd)) this.tendInd = (this.tb.indicadores.find(i => i.serie.length) || this.tb.indicadores[0])?.id ?? null;
        this.$nextTick(() => this.dibujar());
      } catch { }
      this.cargandoTablero = false;
    },

    // ------------------------------------------------------------ indicadores clave
    delta(k, mejorSube = true) {
      const a = this.tb.anterior, v = this.tb.kpis[k];
      if (!a || v === null || a[k] === null || a[k] === undefined) return null;
      const d = Math.round((v - a[k]) * 10) / 10;
      return { txt: `${d > 0 ? '▲' : d < 0 ? '▼' : '='} ${nf(Math.abs(d), 1)} vs. rango anterior`, clase: d === 0 ? 'text-slate-500' : (d > 0) === mejorSube ? 'text-green-700' : 'text-red-700' };
    },
    kpis() {
      const k = this.tb.kpis, p = v => v === null || v === undefined ? '—' : nf(v, 1) + '%';
      return [
        { t: 'Indicadores', v: k.indicadores, c: NAVY, sub: `${k.mediciones} mediciones en el rango` },
        { t: 'Cumplimiento', v: p(k.cumplimiento), c: BRAND, d: this.delta('cumplimiento'), sub: k.mediciones ? `${k.verde} cumplen · ${k.amarillo} alerta · ${k.rojo} críticos` : 'Sin mediciones' },
        { t: 'Cumplen la meta', v: p(k.cumplimiento_meta), c: MAG, d: this.delta('cumplimiento_meta'), sub: k.con_meta ? `${k.cumplen_meta} de ${k.con_meta} períodos con_meta` : 'Sin meta en el rango' },
        { t: 'Real vs. meta', v: p(k.real_vs_meta), c: '#7c3aed', sub: 'Promedio de real ÷ meta' },
        { t: 'Carga al día', v: p(k.carga_al_dia), c: '#004eba', d: this.delta('carga_al_dia'), sub: k.faltantes ? `${k.faltantes} de ${k.esperados} períodos sin cargar` : (k.esperados ? 'Todo cargado' : 'Nada por cargar aún'), subc: k.faltantes ? 'text-amber-700' : '' },
        { t: 'Cargas a tiempo', v: p(k.a_tiempo), c: '#0891b2', d: this.delta('a_tiempo'), sub: k.dias_retraso === null ? 'Sin cargas propias' : `Retraso promedio ${nf(k.dias_retraso, 1)} días (plazo ${this.tb.rango.plazo_dias})` },
        { t: 'Por aprobar', v: k.por_aprobar, c: SEM.amarillo, sub: `${k.devueltas} devuelta(s)` },
        { t: 'Tiempo de aprobación', v: k.horas_aprobacion === null ? '—' : (k.horas_aprobacion >= 48 ? nf(k.horas_aprobacion / 24, 1) + ' d' : nf(k.horas_aprobacion, 1) + ' h'), c: GRIS, sub: 'Del envío a la aprobación' },
      ];
    },
    celdaClase: c => c ? ({ verde: 'bg-green-500 text-white', amarillo: 'bg-amber-400 text-slate-900', rojo: 'bg-red-500 text-white' }[c.semaforo]) : 'bg-slate-100 text-slate-300',
    tendTxt(t) { return !t ? '—' : `${t.delta > 0 ? '▲' : t.delta < 0 ? '▼' : '='} ${nf(Math.abs(t.delta), 2)}`; },
    tendClase(t) { return !t || t.mejora === null ? 'text-slate-400' : t.mejora ? 'text-green-700' : 'text-red-700'; },
    pctTxt: v => v === null || v === undefined ? '—' : nf(v, 1) + '%',

    // ------------------------------------------------------------ rankings y tabla
    get conDatos() { return this.tb.indicadores.filter(i => i.n > 0); },
    get peores() { return [...this.conDatos].sort((a, b) => a.pct_verde - b.pct_verde || b.rojo - a.rojo).slice(0, 10); },
    get mejores() { return [...this.conDatos].sort((a, b) => b.pct_verde - a.pct_verde || b.n - a.n).slice(0, 10); },
    get desviados() { return this.tb.indicadores.filter(i => i.real_vs_meta !== null).sort((a, b) => Math.abs(b.real_vs_meta - 100) - Math.abs(a.real_vs_meta - 100)).slice(0, 10); },
    get tabla() {
      const { col, asc } = this.orden, v = i => col === 'ultimo' ? i.ultimo?.resultado : i[col];
      return [...this.tb.indicadores].sort((a, b) => {
        const x = v(a), y = v(b);
        if ((x ?? null) === null && (y ?? null) === null) return a.codigo.localeCompare(b.codigo);
        if ((x ?? null) === null) return 1; if ((y ?? null) === null) return -1;
        return (typeof x === 'string' ? x.localeCompare(y) : x - y) * (asc ? 1 : -1);
      });
    },
    ordenar(col) { this.orden = { col, asc: this.orden.col === col ? !this.orden.asc : true }; },
    flecha(col) { return this.orden.col === col ? (this.orden.asc ? '▲' : '▼') : ''; },
    exportarCsv() {
      const filas = [['Código', 'Indicador', 'Área', 'Frecuencia', 'Mediciones', 'Cumple', 'Alerta', 'Crítico', '% cumple', 'Cumplen meta', 'Con meta', 'Real vs meta %', 'Sin cargar', 'Último período', 'Último resultado', 'Último semáforo']];
      for (const i of this.tabla) filas.push([i.codigo, i.nombre, i.area, i.frecuencia, i.n, i.verde, i.amarillo, i.rojo, i.pct_verde ?? '', i.cumplen_meta, i.con_meta, i.real_vs_meta ?? '', i.faltantes, i.ultimo?.etiqueta ?? '', i.ultimo?.resultado ?? '', i.ultimo ? this.semTxt(i.ultimo.semaforo) : '']);
      const csv = '﻿' + filas.map(f => f.map(c => `"${String(c).replace(/"/g, '""')}"`).join(';')).join('\r\n');
      const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
      a.download = `panel_${this.pf.desde}_${this.pf.hasta}.csv`; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 4000);
    },

    // ------------------------------------------------------------ gráficos
    async dibujar() {
      if (!this.tb) return;
      try { await this.cargarGraficos(); } catch (e) { this.avisar(e.message, true); return; }
      Chart.defaults.font.family = 'Manrope, ui-sans-serif, system-ui, "Segoe UI", sans-serif'; Chart.defaults.color = '#476788'; Chart.defaults.borderColor = '#d4e0ed';
      const nuevo = (id, cfg) => { const c = document.getElementById(id); if (!c) return; Chart.getChart(c)?.destroy(); new Chart(c, cfg); };
      const leyenda = { legend: { position: 'bottom', labels: { usePointStyle: true, boxWidth: 8 } } };
      const base = { responsive: true, maintainAspectRatio: false, plugins: leyenda };
      const S = this.tb.serie, et = S.map(s => s.etiqueta), pct = (k, s) => s.total ? Math.round(1000 * s[k] / s.total) / 10 : null;

      // 1. evolución del semáforo (barras apiladas al 100 %)
      nuevo('ch-evol', { type: 'bar', data: { labels: et, datasets: [['Cumple', 'verde'], ['Alerta', 'amarillo'], ['Crítico', 'rojo']].map(([l, k]) => ({ label: l, data: S.map(s => pct(k, s)), backgroundColor: SEM[k], borderRadius: 4, borderSkipped: false, stack: 's' })) },
        options: { ...base, scales: { x: { stacked: true, grid: { display: false } }, y: { stacked: true, max: 100, title: { display: true, text: '% de las mediciones' } } },
          plugins: { ...leyenda, tooltip: { callbacks: { label: c => `${c.dataset.label}: ${c.parsed.y ?? 0}%`, footer: it => `${S[it[0].dataIndex].total} medición(es)` } } } } });
      // 2. meta por período
      nuevo('ch-meta', { data: { labels: et, datasets: [
        { type: 'bar', label: 'Cumplen', data: S.map(s => s.cumplen), backgroundColor: SEM.verde, borderRadius: 4, stack: 'p', yAxisID: 'y' },
        { type: 'bar', label: 'No alcanzan', data: S.map(s => s.con_meta - s.cumplen), backgroundColor: SEM.rojo, borderRadius: 4, stack: 'p', yAxisID: 'y' },
        { type: 'line', label: '% que cumple', data: S.map(s => s.cumplimiento_meta), borderColor: MAG, backgroundColor: MAG, pointStyle: 'rectRot', pointRadius: 5, tension: .25, spanGaps: true, yAxisID: 'y1' }] },
        options: { ...base, scales: { x: { stacked: true, grid: { display: false } }, y: { stacked: true, beginAtZero: true, title: { display: true, text: 'Períodos' }, ticks: { precision: 0 } }, y1: { position: 'right', min: 0, max: 100, grid: { drawOnChartArea: false }, title: { display: true, text: '%' } } } } });
      // 3. estado actual
      const a = this.tb.actual;
      nuevo('ch-actual', { type: 'doughnut', data: { labels: ['Cumple', 'Alerta', 'Crítico', 'Sin datos'], datasets: [{ data: [a.verde, a.amarillo, a.rojo, a.sin_datos], backgroundColor: [SEM.verde, SEM.amarillo, SEM.rojo, SEM.sin_datos], borderWidth: 3, borderColor: '#fff' }] }, options: { ...base, cutout: '66%' } });
      // 4. comparativo por dimensión
      const G = this.tb.por_dimension, meta = this.pf.metrica === 'meta';
      nuevo('ch-dim', { type: 'bar', data: { labels: G.map(g => g.nombre), datasets: meta
          ? [{ label: '% de períodos que cumplen la meta', data: G.map(g => g.cumplimiento_meta), backgroundColor: MAG, borderRadius: 6 }]
          : [['Cumple', 'verde'], ['Alerta', 'amarillo'], ['Crítico', 'rojo']].map(([l, k]) => ({ label: l, data: G.map(g => g.total ? Math.round(1000 * g[k] / g.total) / 10 : null), backgroundColor: SEM[k], borderRadius: 4, stack: 's' })) },
        options: { ...base, indexAxis: 'y', scales: { x: { stacked: !meta, max: 100, title: { display: true, text: '%' } }, y: { stacked: !meta, grid: { display: false } } } } });
      // 5. estado de las cargas
      nuevo('ch-carga', { type: 'bar', data: { labels: et, datasets: [
        { label: 'Aprobadas', data: S.map(s => s.aprobadas), backgroundColor: SEM.verde, stack: 'c', borderRadius: 3 }, { label: 'En revisión', data: S.map(s => s.en_revision), backgroundColor: AZ, stack: 'c' },
        { label: 'Devueltas', data: S.map(s => s.devueltas), backgroundColor: SEM.amarillo, stack: 'c' }, { label: 'Sin cargar', data: S.map(s => s.faltantes), backgroundColor: '#fca5a5', stack: 'c', borderRadius: 3 }] },
        options: { ...base, scales: { x: { stacked: true, grid: { display: false } }, y: { stacked: true, beginAtZero: true, ticks: { precision: 0 }, title: { display: true, text: 'Cargas' } } } } });
      // 6. puntualidad por responsable
      const R = this.tb.responsables.slice(0, 10);
      nuevo('ch-punt', { type: 'bar', data: { labels: R.map(r => r.nombre), datasets: [{ label: 'Retraso promedio (días)', data: R.map(r => r.retraso_promedio), backgroundColor: R.map(r => r.a_tiempo_pct >= 80 ? SEM.verde : r.a_tiempo_pct >= 50 ? SEM.amarillo : SEM.rojo), borderRadius: 6 }] },
        options: { ...base, indexAxis: 'y', plugins: { legend: { display: false }, tooltip: { callbacks: { afterLabel: c => `${R[c.dataIndex].a_tiempo_pct}% a tiempo · ${R[c.dataIndex].cargas} cargas` } } }, scales: { x: { beginAtZero: true, title: { display: true, text: 'Días después del cierre del período' } }, y: { grid: { display: false } } } } });
      // 7. tendencia de un indicador
      const i = this.tb.indicadores.find(x => x.id === this.tendInd);
      if (i && i.serie.length) {
        const s = i.serie, dec = i.decimales;
        nuevo('ch-tend', { type: 'line', data: { labels: s.map(p => p.etiqueta), datasets: [
          { label: 'Resultado', data: s.map(p => p.resultado), borderColor: AZ, backgroundColor: AZ, pointBackgroundColor: s.map(p => SEM[p.semaforo]), pointRadius: 6, pointBorderColor: '#fff', borderWidth: 2.5, tension: .25 },
          { label: 'Meta', data: s.map(p => p.meta), borderColor: MAG, backgroundColor: MAG, pointStyle: 'rectRot', pointRadius: 5, borderWidth: 2, tension: .25, spanGaps: true },
          { label: 'Nivel óptimo', data: s.map(p => p.nivel_optimo), borderColor: NAVY, borderDash: [6, 4], pointRadius: 0, borderWidth: 2 },
          { label: 'Límite crítico', data: s.map(p => p.limite), borderColor: SEM.rojo, borderDash: [2, 4], pointRadius: 0, borderWidth: 1.5 }] },
          options: { ...base, plugins: { ...leyenda, tooltip: { callbacks: { label: c => `${c.dataset.label}: ${this.fmt(c.parsed.y, i.unidad, dec)}` } } }, scales: { y: { title: { display: true, text: i.unidad } }, x: { grid: { display: false } } } } });
      } else Chart.getChart(document.getElementById('ch-tend'))?.destroy();
    },
});
