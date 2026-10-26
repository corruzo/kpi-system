/* Carga rápida: el jefe de área (o el administrador) elige indicador y período, digita los datos y envía. */
SIGT.modulos.carga = () => ({
    f: { indicador_id: '', periodo: '', valores: {}, analisis: '', plan_mejora: '', tocado: false },
    periodosInd: [], calc: null, _seq: 0, fichaAbierta: false,

    // Ganchos: el núcleo los invoca al ingresar, al entrar a una vista y al salir.
    ganchos: {
      entrar: {
        async carga() {   // sin selección previa: abrir el primer pendiente (o el primer indicador)
          if (this.f.indicador_id || !this.indicadoresCarga.length) return;
          const p = this.listaPendientes()[0];
          if (p) await this.elegirPendiente(p);
          else { this.f.indicador_id = this.indicadoresCarga[0].id; await this.cambiarIndicador(); }
        },
      },
      salida() { this.f = { indicador_id: '', periodo: '', valores: {}, analisis: '', plan_mejora: '', tocado: false }; this.periodosInd = []; },
    },

    get ind() { return this.indicadores.find(i => i.id === this.f.indicador_id); },
    get medActual() { return this.periodosInd.find(p => p.periodo === this.f.periodo)?.medicion || null; },
    get gruposPeriodos() {
      const g = []; for (const p of this.periodosInd) { let x = g.find(y => y.etiqueta === p.ejercicio); if (!x) g.push(x = { etiqueta: p.ejercicio, periodos: [] }); x.periodos.push(p); } return g;
    },
    get periodoCerrado() { return !!this.periodosInd.find(p => p.periodo === this.f.periodo)?.cerrado; },
    get bloqueado() { return this.periodoCerrado || (!!this.medActual && this.medActual.estado !== 'observado'); },
    get indicadoresCarga() { return this.indicadores.filter(i => i.activo); },
    pendientesTotal() { return this.indicadoresCarga.reduce((n, i) => n + (i.pendientes?.length || 0), 0); },
    listaPendientes() { return this.indicadoresCarga.flatMap(i => (i.pendientes || []).map(p => ({ ind: i, ...p }))); },
    async elegirPendiente(p) { this.f.indicador_id = p.ind.id; await this.cambiarIndicador(p.periodo); },
    async cambiarIndicador(periodo) {
      this.calc = null; this.periodosInd = [];
      if (!this.f.indicador_id) return;
      await this.refrescarPeriodos();
      this.f.periodo = periodo || this._sugerido || this.periodosInd[0].periodo;
      this.cambiarPeriodo();
    },
    async refrescarPeriodos() {
      const r = await this.api(`/api/indicadores/${this.f.indicador_id}/periodos`);
      this.periodosInd = r.periodos; this._sugerido = r.sugerido;
    },
    cambiarPeriodo() {
      const m = this.medActual;
      this.f.valores = m ? { ...m.valores } : {};
      this.f.analisis = m?.analisis || ''; this.f.plan_mejora = m?.plan_mejora || ''; this.f.tocado = false;
      this.calc = m && m.estado !== 'observado' ? { ok: true, resultado: m.resultado, semaforo: m.semaforo, requiere_analisis: m.semaforo !== 'verde' } : null;
      if (m?.estado === 'observado') this.calcular();
    },
    async calcular() {
      this.f.tocado = true;
      const vals = {}; let completo = true;
      for (const v of this.ind.variables) {
        const x = this.f.valores[v.clave];
        if (x === '' || x === undefined || x === null) { vals[v.clave] = null; if (!v.opcional) completo = false; } else vals[v.clave] = Number(x);
      }
      if (!completo) { this.calc = null; return; }
      const n = ++this._seq;
      try { const r = await this.api('/api/calcular', { method: 'POST', body: { indicador_id: this.ind.id, valores: vals } }, true); if (n === this._seq) this.calc = r; }
      catch { }
    },
    analisisOk() { return this.f.analisis.trim().length >= 10 && this.f.plan_mejora.trim().length >= 10; },
    puedeEnviar() { return !this.bloqueado && this.calc?.ok && (!this.calc.requiere_analisis || this.analisisOk()); },
    async enviar() {
      this.busy = true;
      try {
        const vals = Object.fromEntries(this.ind.variables.map(v => { const x = this.f.valores[v.clave]; return [v.clave, x === '' || x === undefined || x === null ? null : Number(x)]; }));
        await this.api('/api/mediciones', { method: 'POST', body: { indicador_id: this.ind.id, periodo: this.f.periodo, valores: vals, analisis: this.f.analisis, plan_mejora: this.f.plan_mejora } });
        this.avisar('Carga enviada correctamente.');
        const per = this.f.periodo;
        await this.cargarIndicadores(); await this.refrescarPeriodos(); this.f.periodo = per; this.cambiarPeriodo();
      } catch { }
      this.busy = false;
    },
});
