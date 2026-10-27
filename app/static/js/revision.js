/* Revisión: historial de cargas, bandeja de aprobación del gerente/auditor, reapertura y notas de auditoría. */
SIGT.modulos.revision = () => ({
    historial: [], filtro: { indicador_id: '', estado: '' }, filtro2: { semaforo: '', periodo: '', area_id: '' },
    histMas: false, notasHist: {}, reabrirNota: {},
    bandejaTotal: [], notas: {}, histTodos: false,

    // Ganchos: el núcleo los invoca al ingresar, al entrar a una vista y al salir.
    ganchos: {
      async ingreso() { if (['gerente', 'admin'].includes(this.user.rol)) await this.cargarBandeja(); },
      ejercicio() { this.filtro2.periodo = ''; },
      entrar: { historial() { return this.cargarHistorial(); }, bandeja() { return this.cargarBandeja(); } },
    },

    async cargarHistorial(reset = true) {
      const q = new URLSearchParams({ limite: 50, desde: reset ? 0 : this.historial.length });
      if (this.ejSel && !this.histTodos) q.set('ejercicio', this.ejSel);     // por defecto, solo el ejercicio elegido
      for (const [k, v] of Object.entries({ ...this.filtro, ...this.filtro2 })) if (v) q.set(k, v);
      const r = await this.api('/api/mediciones?' + q);
      this.historial = reset ? r : [...this.historial, ...r]; this.histMas = r.length === 50;
    },
    detalleHtml(m) {
      const et = Object.fromEntries(m.variables.map(v => [v.clave, v.etiqueta]));
      const filas = Object.entries(m.valores).map(([k, val]) => `<tr><td class="pr-4 text-slate-500">${esc(et[k] || k)}</td><td class="font-semibold">${esc(nf(val, 2))}</td></tr>`).join('');
      const bloque = (t, x) => x ? `<div class="mt-2"><div class="text-xs font-semibold uppercase text-slate-500">${t}</div><div class="text-sm whitespace-pre-line">${esc(x)}</div></div>` : '';
      const notas = m.notas.map(n => `<div class="text-sm bg-brand-light border border-brand/20 rounded p-2 mt-1"><b>${esc(n.usuario.split(' (')[0])}</b> · ${esc(this.fecha(n.fecha))}<br>${esc(n.texto)}</div>`).join('');
      return `<div class="text-sm"><table class="text-sm">${filas}</table>
        ${bloque('Resultados del análisis', m.analisis)}${bloque('Correcciones / plan de mejora', m.plan_mejora)}
        <div class="text-xs text-slate-500 mt-2">Cargado por ${esc(m.cargado_por)} · ${esc(this.fecha(m.cargado_en))} · versión ${m.version}
        ${m.revisado_por ? ` · Revisado por ${esc(m.revisado_por.split(' (')[0])} · ${esc(this.fecha(m.revisado_en))}` : ''}</div>
        ${m.nota_revision ? `<div class="text-sm bg-amber-50 border border-amber-200 rounded p-2 mt-2"><b>Nota de revisión:</b> ${esc(m.nota_revision)}</div>` : ''}
        ${notas ? `<div class="mt-2 text-xs font-semibold uppercase text-slate-500">Notas de auditoría</div>${notas}` : ''}</div>`;
    },
    async agregarNota(m) {
      const t = (this.notasHist[m.id] || '').trim(); if (t.length < 3) return;
      this.busy = true;
      try { await this.api(`/api/mediciones/${m.id}/notas`, { method: 'POST', body: { texto: t } }); this.notasHist[m.id] = ''; this.avisar('Nota registrada.'); await this.cargarHistorial(); } catch { }
      this.busy = false;
    },
    async reabrir(m) {
      const nota = (this.reabrirNota[m.id] || '').trim();
      if (nota.length < 5) { this.avisar('Indique el motivo de la reapertura.', true); return; }
      this.busy = true;
      try { await this.api(`/api/mediciones/${m.id}/reabrir`, { method: 'POST', body: { accion: 'observar', nota } }); this.avisar('Carga devuelta al jefe de área.'); await this.cargarHistorial(); } catch { }
      this.busy = false;
    },
    // La bandeja trae todas las cargas por aprobar (ninguna se pierde), pero se muestran las del ejercicio elegido;
    // las de otros ejercicios se avisan aparte.
    async cargarBandeja() { this.bandejaTotal = await this.api('/api/mediciones?estado=enviado'); },
    get bandeja() { return this.bandejaTotal.filter(m => m.ejercicio === this.ejSel); },
    get bandejaOtros() {
      const t = {};
      for (const m of this.bandejaTotal) if (m.ejercicio !== this.ejSel) (t[m.ejercicio] ||= { ejercicio: m.ejercicio, etiqueta: m.ejercicio_etiqueta, n: 0 }).n++;
      return Object.values(t).sort((a, b) => b.ejercicio - a.ejercicio);
    },
    // Separador cuando el historial mezcla ejercicios («todos los ejercicios»): marca dónde empieza cada uno
    nuevoEjercicio(i) { return this.histTodos && (i === 0 || this.historial[i].ejercicio !== this.historial[i - 1].ejercicio); },
    async revisar(m, accion) {
      const nota = (this.notas[m.id] || '').trim();
      if (accion === 'observar' && nota.length < 5) { this.avisar('Indique el motivo de la devolución.', true); return; }
      this.busy = true;
      try {
        await this.api(`/api/mediciones/${m.id}/revision`, { method: 'POST', body: { accion, nota } });
        this.avisar(accion === 'aprobar' ? 'Carga aprobada.' : 'Carga devuelta al jefe de área.');
        await this.cargarBandeja();
      } catch { }
      this.busy = false;
    },
});
