/* Período y presupuesto: crear el período fiscal (paso 1) y presupuestar cada indicador (paso 3). */
SIGT.modulos.presupuesto = () => ({
    pres: null, presAnio: null, presArea: '', presAbierto: null, ed: {}, rapido: {}, presFiltro: 'todos',
    nuevoAnio: null, nuevoNota: '',

    // Ganchos: el núcleo los invoca al ingresar, al entrar a una vista y al salir.
    ganchos: {
      entrar: { presupuesto() { this.presAnio = this.ejTodos.some(e => e.anio === this.ejSel && e.creado) ? this.ejSel : this.ejVigente; return this.cargarPresupuesto(); } },
      salida() { this.pres = null; this.ed = {}; this.rapido = {}; },
    },

    get presDesc() { return this.ejTodos.find(e => e.anio === this.presAnio) || {}; },
    get presEditable() { return ['admin', 'gerente'].includes(this.user.rol) && this.presDesc.creado && this.presDesc.estado !== 'cerrado'; },
    // Años que se pueden elegir: los creados y los que faltan por crear, del más reciente al más antiguo
    get presAnios() { return this.ejTodos.filter(e => e.creado || e.anio >= this.ejVigente - 1); },
    get presPct() { const r = this.pres?.resumen; return r && r.total ? Math.round(100 * r.completos / r.total) : 0; },
    get presLista() {
      if (!this.pres) return [];
      return this.pres.indicadores.filter(f => this.presFiltro === 'todos' || (this.presFiltro === 'pendientes') === !f.completo);
    },

    async cargarPresupuesto() {
      const r = await this.api('/api/ejercicios'); this.aplicarEjercicios(r.ejercicios);
      if (!this.presDesc.creado) { this.pres = null; return; }
      const q = this.presArea ? '?area_id=' + this.presArea : '';
      this.pres = await this.api(`/api/ejercicios/${this.presAnio}/presupuesto` + q);
      this.ed = {}; this.rapido = {};
      for (const f of this.pres.indicadores) {
        this.rapido[f.indicador_id] = { anual: '', reparto: f.sentido === 'menor' || f.unidad === '%' ? 'repetir' : 'igual' };
        for (const p of f.periodos) this.ed[this.k(f, p)] = p.valor === null ? '' : String(p.valor);
      }
    },
    k: (f, p) => f.indicador_id + ':' + p.periodo,
    async elegirAnioPres(a) { this.presAnio = a; this.presAbierto = null; await this.cargarPresupuesto(); },
    abrirPres(f) { this.presAbierto = this.presAbierto === f.indicador_id ? null : f.indicador_id; },

    async crearPeriodo(anio, nota = '') {
      this.busy = true;
      try {
        await this.api('/api/ejercicios', { method: 'POST', body: { anio, nota } });
        this.avisar('Período fiscal creado. Ahora ingrese el presupuesto de cada indicador.');
        await this.cargarEjercicios(); this.presAnio = anio; await this.cargarPresupuesto();
        if (this.view === 'inicio') await this.cargarInicio();
      } catch { }
      this.busy = false;
    },

    // «Aplicar» solo rellena las casillas; nada se guarda hasta pulsar «Guardar presupuesto»
    aplicarRapido(f) {
      const r = this.rapido[f.indicador_id], v = Number(r.anual);
      if (r.anual === '' || !isFinite(v)) { this.avisar('Escriba primero el valor anual.', true); return; }
      const n = f.periodos.filter(p => !p.bloqueado).length || 1;
      const x = r.reparto === 'igual' ? Math.round(v / f.periodos.length * 10 ** (f.decimales + 2)) / 10 ** (f.decimales + 2) : v;
      for (const p of f.periodos) if (!p.bloqueado) this.ed[this.k(f, p)] = String(x);
      this.avisar(n + ' período(s) rellenados: revise y pulse «Guardar presupuesto».');
    },
    cambios(f) {
      const out = {};
      for (const p of f.periodos) {
        const t = this.ed[this.k(f, p)];
        if (p.bloqueado || t === '' || t === undefined || !isFinite(Number(t))) continue;
        if (p.valor === null || Number(t) !== p.valor) out[p.periodo] = Number(t);
      }
      return out;
    },
    hayCambios(f) { return Object.keys(this.cambios(f)).length > 0; },
    async guardarPres(f) {
      const valores = this.cambios(f);
      if (!Object.keys(valores).length) return;
      this.busy = true;
      try {
        await this.api(`/api/ejercicios/${this.presAnio}/presupuesto/${f.indicador_id}`, { method: 'PUT', body: { valores } });
        this.avisar('Presupuesto de ' + f.codigo + ' guardado.');
        const abierto = this.presAbierto; await this.cargarPresupuesto(); this.presAbierto = abierto;
      } catch { }
      this.busy = false;
    },
    async copiarPresupuesto() {
      const origen = this.presAnio - 1;
      if (!confirm(`¿Copiar el presupuesto del ejercicio ${origen} a los indicadores que aún no tienen el de este?`)) return;
      this.busy = true;
      try {
        const r = await this.api(`/api/ejercicios/${this.presAnio}/presupuesto/copiar`, { method: 'POST', body: { desde: origen } });
        this.avisar(r.indicadores ? r.indicadores + ' indicador(es) copiados.' : 'No había nada que copiar.');
        await this.cargarPresupuesto();
      } catch { }
      this.busy = false;
    },
});
