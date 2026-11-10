/* Indicadores: lista según el rol y administración de fichas técnicas (alta, edición, fórmula, probador). */
SIGT.modulos.indicadores = () => ({
    indicadores: [],                                                     // los que el usuario puede cargar (selector de «Cargar datos»)
    fichas: [],                                                          // página de la lista «Indicadores» (gestión de fichas)
    opcionesUsuarios: [],                                                // usuarios activos para elegir encargado
    fq: { q: '', area: '', frecuencia: '', estado: 'activo' },           // filtros de la lista
    ficha: { variables: [], constantes: [] }, modal: false,              // ficha en edición
    formulaMsg: { ok: true, txt: '' }, prueba: { valores: {}, res: null }, // validación y probador de fórmulas

    // Ganchos: el núcleo los invoca al ingresar, al entrar a una vista y al salir.
    ganchos: {
      entrar: { fichas() { return Promise.all([this.cargarFichas(1), this.cargarOpcionesUsuarios()]); } },
      ejercicio() { return Promise.all([this.cargarIndicadores(), this.view === 'fichas' ? this.cargarFichas(this.pg('fichas').pagina) : null]); },
      salida() { this.indicadores = []; this.fichas = []; this.opcionesUsuarios = []; },
    },

    // Los pendientes de cada indicador corresponden al ejercicio elegido; los de otros ejercicios vienen aparte.
    // Quienes cargan datos (encargado y administrador) reciben sus indicadores al ingresar; el gerente / auditor no los necesita ahí.
    async cargarIndicadores() {
      if (this.user && this.user.rol === 'gerente') { this.indicadores = []; return; }
      this.indicadores = await this.api('/api/indicadores' + (this.ejSel ? '?ejercicio=' + this.ejSel : ''));
    },
    // Lista de gestión: el servidor filtra y entrega solo la página pedida (incluye archivados)
    async cargarFichas(pagina = 1) {
      const q = new URLSearchParams({ gestion: 'true' });
      if (this.ejSel) q.set('ejercicio', this.ejSel);
      if (this.fq.q.trim()) q.set('q', this.fq.q.trim());
      if (this.fq.area) q.set('area_id', this.fq.area);
      if (this.fq.frecuencia) q.set('frecuencia', this.fq.frecuencia);
      if (this.fq.estado) q.set('activo', this.fq.estado === 'activo');
      this.fichas = await this.pedirPagina('fichas', '/api/indicadores?' + q, pagina);
    },
    async cargarOpcionesUsuarios() { if (!this.opcionesUsuarios.length) this.opcionesUsuarios = await this.api('/api/usuarios/opciones'); },
    // Tras crear, editar o eliminar: se refresca la página actual y la lista de carga
    async refrescarIndicadores() { await Promise.all([this.cargarFichas(this.pg('fichas').pagina), this.cargarIndicadores()]); },
    codigoSugerido: '',
    get etiquetaNC() { return (this.params.codigo_formato || 'NC-16').split('-').slice(0, 2).join('-'); },
    get encargadosDelArea() { return this.opcionesUsuarios.filter(u => u.rol === 'jefe' && u.activo && u.area_id === this.ficha.area_id); },
    async cambioDeArea() {
      if (!this.encargadosDelArea.some(u => u.id === this.ficha.encargado_id)) this.ficha.encargado_id = this.encargadosDelArea.length === 1 ? this.encargadosDelArea[0].id : null;
      await this.pedirCodigo();
    },
    async pedirCodigo() {
      if (this.ficha.id || !this.ficha.area_id) { this.codigoSugerido = ''; return; }
      try { this.codigoSugerido = (await this.api(`/api/indicadores/codigo-sugerido?area_id=${this.ficha.area_id}`)).codigo; } catch { this.codigoSugerido = ''; }
    },
    nuevaFicha() {
      this.ficha = { codigo: '', nombre: '', objetivo: '', area_id: this.areas[0]?.id, unidad: '%', frecuencia: 'mensual', decimales: 2, sentido: 'mayor', nivel_optimo: 90, limite: 80, nivel_optimo_tope: null, limite_tope: null, formula: '', seguimiento: 'proceso', ref_nombre: '', ref_detalle: '', sigla: '', gerencia: '', lider: '', resp_medicion: '', resp_registro: '', resp_analisis: '', variables: [{ clave: '', etiqueta: '' }, { clave: '', etiqueta: '' }], constantes: [], fuente: '', notas: '', activo: true, n_mediciones: 0 };
      this.abrirFicha('Escriba la fórmula con las claves de las variables; use los botones «i» y los atajos de la fórmula como ayuda.');
      this.cambioDeArea();
    },
    editarFicha(i) {
      this.ficha = JSON.parse(JSON.stringify(i)); this.ficha.constantes ||= [];
      [...this.ficha.variables, ...this.ficha.constantes].forEach(v => v._manual = true);
      this.abrirFicha(''); this.validarFormula(); this.codigoSugerido = '';
    },
    duplicarFicha(i) {
      this.ficha = { ...JSON.parse(JSON.stringify(i)), id: undefined, codigo: '', nombre: i.nombre + ' (copia)', n_mediciones: 0, activo: true };
      this.ficha.constantes ||= [];
      [...this.ficha.variables, ...this.ficha.constantes].forEach(v => v._manual = true);
      this.abrirFicha('Ficha duplicada: el sistema le asignará un código nuevo.'); this.validarFormula(); this.pedirCodigo();
    },
    abrirFicha(msg) { this.formulaMsg = { ok: true, txt: msg }; this.prueba = { valores: {}, res: null }; this.ay = ''; this.modal = true; },
    get fichaBloqueada() { return (this.ficha.n_mediciones || 0) > 0; },
    slug: t => t.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '').replace(/^(\d)/, 'v$1').slice(0, 30),
    autoClave(v) { if (!this.fichaBloqueada && !v._manual) { v.clave = this.slug(v.etiqueta); this.validarFormula(); } },
    mover(idx, d) { const a = this.ficha.variables, j = idx + d; if (j < 0 || j >= a.length) return; [a[idx], a[j]] = [a[j], a[idx]]; },
    semaforoAyuda() {
      const f = this.ficha, u = f.unidad;
      return f.sentido === 'mayor' ? `Verde: ≥ ${f.nivel_optimo} · Amarillo: entre ${f.limite} y ${f.nivel_optimo} · Rojo: < ${f.limite} (${u})`
        : `Verde: ≤ ${f.nivel_optimo} · Amarillo: entre ${f.nivel_optimo} y ${f.limite} · Rojo: > ${f.limite} (${u})`;
    },
    insertar(t, atras = 0) {
      const el = this.$refs.formula, f = this.ficha.formula || '';
      const a = el ? el.selectionStart : f.length, b = el ? el.selectionEnd : f.length;
      const pre = f.slice(0, a), sep = pre && !/[\s(]$/.test(pre) && /^[a-z0-9_(]/i.test(t) ? ' ' : '';
      this.ficha.formula = pre + sep + t + f.slice(b);
      this.$nextTick(() => { if (el) { el.focus(); const p = (pre + sep + t).length - atras; el.setSelectionRange(p, p); } });
      this.validarFormula();
    },
    get nombresFormula() { return [...this.ficha.variables, ...(this.ficha.constantes || [])].map(v => v.clave).filter(Boolean); },
    async validarFormula() {
      if (!this.ficha.formula) return;
      try {
        const r = await this.api('/api/formula/validar', { method: 'POST', body: { formula: this.ficha.formula, claves: this.nombresFormula, variables: this.ficha.variables.map(v => v.clave).filter(Boolean) } }, true);
        this.formulaMsg = !r.ok ? { ok: false, txt: r.error } : r.sin_usar.length ? { ok: true, aviso: true, txt: '✔ Válida, pero no usa: ' + r.sin_usar.join(', ') } : { ok: true, txt: '✔ Fórmula válida' };
        if (r.ok) this.probar();
      } catch { }
    },
    async probar() {
      const f = this.ficha, valores = {};
      for (const v of f.variables.filter(v => v.clave)) {
        const x = this.prueba.valores[v.clave];
        if (x === '' || x === undefined || x === null) { if (!v.opcional) { this.prueba.res = null; return; } valores[v.clave] = Number(v.defecto || 0); } else valores[v.clave] = Number(x);
      }
      const constantes = Object.fromEntries((f.constantes || []).filter(c => c.clave).map(c => [c.clave, Number(c.valor)]));
      try { this.prueba.res = await this.api('/api/formula/probar', { method: 'POST', body: { formula: f.formula, valores, constantes, decimales: Number(f.decimales), nivel_optimo: Number(f.nivel_optimo), limite: Number(f.limite), nivel_optimo_tope: f.nivel_optimo_tope === '' ? null : f.nivel_optimo_tope, limite_tope: f.limite_tope === '' ? null : f.limite_tope, sentido: f.sentido } }, true); } catch { }
    },
    cuerpoFicha(f) {
      return {
        codigo: f.id ? f.codigo : '', encargado_id: f.encargado_id || null, nombre: f.nombre, objetivo: f.objetivo, area_id: f.area_id, unidad: f.unidad, frecuencia: f.frecuencia, sentido: f.sentido, formula: f.formula,
        variables: f.variables.map(v => ({ clave: v.clave, etiqueta: v.etiqueta, ayuda: v.ayuda || '', unidad: v.unidad || '', opcional: !!v.opcional, defecto: Number(v.defecto || 0), negativo: !!v.negativo })),
        constantes: (f.constantes || []).map(c => ({ clave: c.clave, etiqueta: c.etiqueta, valor: Number(c.valor) })),
        decimales: Number(f.decimales ?? 2), fuente: f.fuente || '', notas: f.notas || '', nivel_optimo: f.nivel_optimo, limite: f.limite,
        nivel_optimo_tope: f.nivel_optimo_tope === '' ? null : f.nivel_optimo_tope, limite_tope: f.limite_tope === '' ? null : f.limite_tope, activo: f.activo,
        seguimiento: f.seguimiento || 'proceso', ref_nombre: f.ref_nombre || '', ref_detalle: f.ref_detalle || '', sigla: f.sigla || '', gerencia: f.gerencia || '',
        lider: f.lider || '', resp_medicion: f.resp_medicion || '', resp_registro: f.resp_registro || '', resp_analisis: f.resp_analisis || ''
      };
    },
    async guardarFicha() {
      this.busy = true;
      try {
        const f = this.ficha, id = f.id;
        await this.api(id ? `/api/indicadores/${id}` : '/api/indicadores', { method: id ? 'PUT' : 'POST', body: this.cuerpoFicha(f) });
        this.modal = false; this.avisar(id ? 'Ficha actualizada.' : 'Indicador creado.'); await this.refrescarIndicadores();
      } catch { }
      this.busy = false;
    },
    async alternarActivo(i) {
      const accion = i.activo ? 'archivar' : 'restaurar';
      if (i.activo && !confirm(`¿Archivar ${i.codigo}? Dejará de aparecer para cargar datos; el historial se conserva.`)) return;
      try { await this.api(`/api/indicadores/${i.id}`, { method: 'PUT', body: this.cuerpoFicha({ ...i, activo: !i.activo }) }); this.avisar(`Indicador ${i.activo ? 'archivado' : 'restaurado'}.`); await this.refrescarIndicadores(); } catch { }
    },
    async eliminarFicha(i) {
      const msg = i.n_mediciones ? `${i.codigo} tiene ${i.n_mediciones} carga(s) registradas: no se borrará, se archivará para conservar la trazabilidad. ¿Continuar?` : `¿Eliminar definitivamente el indicador ${i.codigo}?`;
      if (!confirm(msg)) return;
      try { const r = await this.api(`/api/indicadores/${i.id}`, { method: 'DELETE' }); this.avisar(r.archivado ? 'Indicador archivado (tiene historial de cargas).' : 'Indicador eliminado.'); await this.refrescarIndicadores(); } catch { }
    },
    elegirRef() {
      const c = this.catalogos.find(c => c.tipo === 'proceso' && c.valor === this.ficha.ref_nombre);
      if (c && c.detalle && !this.ficha.ref_detalle) this.ficha.ref_detalle = c.detalle;
    },
    get sugerenciasPersonas() { return [...new Set(this.opcionesUsuarios.map(u => u.nombre.split(' (')[0]))]; },
});
