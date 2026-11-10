/* Revisión: historial de cargas, bandeja de aprobación del gerente/auditor, reapertura y notas de auditoría. */
SIGT.modulos.revision = () => ({
    historial: [], filtro: { indicador_id: '', estado: '' }, filtro2: { semaforo: '', periodo: '', area_id: '' },
    notasHist: {}, reabrirNota: {},
    bandeja: [], bandejaN: 0, bandejaEj: [], notas: {}, histTodos: false,   // bandejaN y bandejaEj: cantidades (todas las cargas por aprobar)

    // Ganchos: el núcleo los invoca al ingresar, al entrar a una vista y al salir.
    ganchos: {
      ejercicio() { this.filtro2.periodo = ''; },
      entrar: { historial() { return this.cargarHistorial(); }, bandeja() { return this.cargarBandeja(); } },
    },

    async cargarHistorial(pagina = 1) {
      const q = new URLSearchParams();
      if (this.ejSel && !this.histTodos) q.set('ejercicio', this.ejSel);     // por defecto, solo el ejercicio elegido
      for (const [k, v] of Object.entries({ ...this.filtro, ...this.filtro2 })) if (v) q.set(k, v);
      this.historial = await this.pedirPagina('historial', '/api/mediciones?' + q, pagina);
    },
    detalleHtml(m) {
      const et = Object.fromEntries(m.variables.map(v => [v.clave, v.etiqueta]));
      const filas = Object.entries(m.valores).map(([k, val]) => `<tr><td class="pr-4 text-slate-500">${esc(et[k] || k)}</td><td class="font-semibold">${esc(nf(val, 2))}</td></tr>`).join('');
      const bloque = (t, x) => x ? `<div class="mt-2"><div class="text-xs font-semibold uppercase text-slate-500">${t}</div><div class="text-sm whitespace-pre-line">${esc(x)}</div></div>` : '';
      const notas = m.notas.map(n => `<div class="text-sm bg-brand-light border border-brand/20 rounded p-2 mt-1"><b>${esc(n.usuario.split(' (')[0])}</b> · ${esc(this.fecha(n.fecha))}<br>${esc(n.texto)}</div>`).join('');
      const pr = m.vs_meta ? `<div class="mt-2 rounded-xl bg-slate-100 px-3 py-2 text-sm"><b>Meta:</b> ${esc(this.fmt(m.meta, m.unidad, m.decimales))} · <b>Diferencia:</b> ${m.vs_meta.desviacion > 0 ? '+' : ''}${esc(nf(m.vs_meta.desviacion, m.decimales))}${m.vs_meta.porcentaje !== null ? ` (${esc(nf(m.vs_meta.porcentaje, 1))}%)` : ''} · <b class="${m.vs_meta.cumple ? 'text-green-700' : 'text-red-700'}">${m.vs_meta.cumple ? 'Cumple' : 'No alcanza'}</b></div>` : '';
      return `<div class="text-sm"><table class="text-sm">${filas}</table>${pr}
        ${bloque(m.semaforo === 'verde' ? 'Observación' : 'Resultados del análisis', m.analisis)}${bloque('Correcciones / plan de mejora', m.plan_mejora)}
        <div class="text-xs text-slate-500 mt-2">Cargado por ${esc(m.cargado_por)} · ${esc(this.fecha(m.cargado_en))} · versión ${m.version}
        ${m.revisado_por ? ` · Revisado por ${esc(m.revisado_por.split(' (')[0])} · ${esc(this.fecha(m.revisado_en))}` : ''}</div>
        ${m.nota_revision ? `<div class="text-sm bg-amber-50 border border-amber-200 rounded p-2 mt-2"><b>Nota de revisión:</b> ${esc(m.nota_revision)}</div>` : ''}
        ${notas ? `<div class="mt-2 text-xs font-semibold uppercase text-slate-500">Notas de auditoría</div>${notas}` : ''}</div>`;
    },
    async agregarNota(m) {
      const t = (this.notasHist[m.id] || '').trim(); if (t.length < 3) return;
      this.busy = true;
      try { await this.api(`/api/mediciones/${m.id}/notas`, { method: 'POST', body: { texto: t } }); this.notasHist[m.id] = ''; this.avisar('Nota registrada.'); await this.cargarHistorial(this.pg('historial').pagina); } catch { }
      this.busy = false;
    },
    async reabrir(m) {
      const nota = (this.reabrirNota[m.id] || '').trim();
      if (nota.length < 5) { this.avisar('Indique el motivo de la reapertura.', true); return; }
      this.busy = true;
      try { await this.api(`/api/mediciones/${m.id}/reabrir`, { method: 'POST', body: { accion: 'observar', nota } }); this.avisar('Carga devuelta al encargado de proceso.'); await this.cargarHistorial(this.pg('historial').pagina); } catch { }
      this.busy = false;
    },
    // La bandeja pide por páginas solo las cargas por aprobar del ejercicio elegido; de las de otros ejercicios solo se
    // conoce la cantidad (bandejaEj, que viene en el arranque y se refresca aquí) para avisarlas aparte.
    async cargarBandeja(pagina = 1) {
      const q = new URLSearchParams({ estado: 'enviado' }); if (this.ejSel) q.set('ejercicio', this.ejSel);
      const [lista, resumen] = await Promise.all([this.pedirPagina('bandeja', '/api/mediciones?' + q, pagina), this.api('/api/mediciones/resumen-ejercicios?estado=enviado')]);
      this.bandeja = lista; this.bandejaEj = resumen; this.bandejaN = resumen.reduce((s, e) => s + e.n, 0);
    },
    get bandejaDelEjercicio() { return this.bandejaEj.find(e => e.ejercicio === this.ejSel)?.n || 0; },
    get bandejaOtros() { return this.bandejaEj.filter(e => e.ejercicio !== this.ejSel).sort((a, b) => b.ejercicio - a.ejercicio); },
    // Separador cuando el historial mezcla ejercicios («todos los ejercicios»): marca dónde empieza cada uno
    nuevoEjercicio(i) { return this.histTodos && (i === 0 || this.historial[i].ejercicio !== this.historial[i - 1].ejercicio); },
    async revisar(m, accion) {
      const nota = (this.notas[m.id] || '').trim();
      if (accion === 'observar' && nota.length < 5) { this.avisar('Indique el motivo de la devolución.', true); return; }
      this.busy = true;
      try {
        await this.api(`/api/mediciones/${m.id}/revision`, { method: 'POST', body: { accion, nota } });
        this.avisar(accion === 'aprobar' ? 'Carga aprobada.' : 'Carga devuelta al encargado de proceso.');
        await this.cargarBandeja(this.pg('bandeja').pagina);
      } catch { }
      this.busy = false;
    },
});
