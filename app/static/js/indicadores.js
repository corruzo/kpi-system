/* Indicadores: lista según el rol y administración de fichas técnicas (alta, edición, fórmula, probador). */
SIGT.modulos.indicadores = () => ({
    indicadores: [],
    fq: { q: '', area: '', frecuencia: '', estado: 'activo' },           // filtros de la lista
    ficha: { variables: [], constantes: [] }, modal: false,              // ficha en edición
    formulaMsg: { ok: true, txt: '' }, prueba: { valores: {}, res: null }, // validación y probador de fórmulas
    verGuiaFormulas: false, ejemplos: EJEMPLOS, funcDoc: FUNC_DOC,

    // Ganchos: el núcleo los invoca al ingresar, al entrar a una vista y al salir.
    ganchos: {
      ingreso() { return this.cargarIndicadores(); },
      entrar: { fichas() { return this.cargarIndicadores(); } },
      ejercicio() { return this.cargarIndicadores(); },
      salida() { this.indicadores = []; },
    },

    // Los pendientes de cada indicador corresponden al ejercicio elegido; los de otros ejercicios vienen aparte.
    async cargarIndicadores() { this.indicadores = await this.api('/api/indicadores' + (this.ejSel ? '?ejercicio=' + this.ejSel : '')); },
    get fichasFiltradas() {
      const q = this.fq.q.trim().toLowerCase();
      return this.indicadores.filter(i =>
        (!q || (i.codigo + ' ' + i.nombre + ' ' + i.area).toLowerCase().includes(q)) &&
        (!this.fq.area || i.area_id === Number(this.fq.area)) &&
        (!this.fq.frecuencia || i.frecuencia === this.fq.frecuencia) &&
        (this.fq.estado === '' || (this.fq.estado === 'activo') === i.activo));
    },
    nuevaFicha() {
      this.ficha = { codigo: '', nombre: '', objetivo: '', area_id: this.areas[0]?.id, unidad: '%', frecuencia: 'mensual', decimales: 2, sentido: 'mayor', meta: 90, limite: 80, meta_tope: null, limite_tope: null, formula: '', seguimiento: 'proceso', ref_nombre: '', ref_detalle: '', sigla: '', gerencia: '', lider: '', resp_medicion: '', resp_registro: '', resp_analisis: '', variables: [{ clave: '', etiqueta: '' }, { clave: '', etiqueta: '' }], constantes: [], fuente: '', notas: '', activo: true, n_mediciones: 0 };
      this.abrirFicha('Escriba la fórmula con las claves de las variables. Pulse «Guía de fórmulas» para ver funciones y ejemplos.');
    },
    editarFicha(i) {
      this.ficha = JSON.parse(JSON.stringify(i)); this.ficha.constantes ||= [];
      [...this.ficha.variables, ...this.ficha.constantes].forEach(v => v._manual = true);
      this.abrirFicha(''); this.validarFormula();
    },
    duplicarFicha(i) {
      this.ficha = { ...JSON.parse(JSON.stringify(i)), id: undefined, codigo: '', nombre: i.nombre + ' (copia)', n_mediciones: 0, activo: true };
      this.ficha.constantes ||= [];
      [...this.ficha.variables, ...this.ficha.constantes].forEach(v => v._manual = true);
      this.abrirFicha('Ficha duplicada: asigne un código nuevo.'); this.validarFormula();
    },
    abrirFicha(msg) { this.formulaMsg = { ok: true, txt: msg }; this.prueba = { valores: {}, res: null }; this.ay = ''; this.verGuiaFormulas = false; this.modal = true; },
    get fichaBloqueada() { return (this.ficha.n_mediciones || 0) > 0; },
    slug: t => t.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '').replace(/^(\d)/, 'v$1').slice(0, 30),
    autoClave(v) { if (!this.fichaBloqueada && !v._manual) { v.clave = this.slug(v.etiqueta); this.validarFormula(); } },
    mover(idx, d) { const a = this.ficha.variables, j = idx + d; if (j < 0 || j >= a.length) return; [a[idx], a[j]] = [a[j], a[idx]]; },
    semaforoAyuda() {
      const f = this.ficha, u = f.unidad;
      return f.sentido === 'mayor' ? `Verde: ≥ ${f.meta} · Amarillo: entre ${f.limite} y ${f.meta} · Rojo: < ${f.limite} (${u})`
        : `Verde: ≤ ${f.meta} · Amarillo: entre ${f.meta} y ${f.limite} · Rojo: > ${f.limite} (${u})`;
    },
    insertar(t, atras = 0) {
      const el = this.$refs.formula, f = this.ficha.formula || '';
      const a = el ? el.selectionStart : f.length, b = el ? el.selectionEnd : f.length;
      const pre = f.slice(0, a), sep = pre && !/[\s(]$/.test(pre) && /^[a-z0-9_(]/i.test(t) ? ' ' : '';
      this.ficha.formula = pre + sep + t + f.slice(b);
      this.$nextTick(() => { if (el) { el.focus(); const p = (pre + sep + t).length - atras; el.setSelectionRange(p, p); } });
      this.validarFormula();
    },
    usarEjemplo(e) {
      if (this.fichaBloqueada) { this.avisar('Este indicador tiene cargas: no se pueden cambiar las variables.', true); return; }
      this.ficha.variables = e.vars.map(([clave, etiqueta]) => ({ clave, etiqueta, _manual: true }));
      this.ficha.constantes = (e.consts || []).map(([clave, etiqueta, valor]) => ({ clave, etiqueta, valor, _manual: true }));
      this.ficha.formula = e.f; this.ficha.unidad = e.unidad; this.verGuiaFormulas = false; this.validarFormula(); this.avisar('Ejemplo cargado: ajuste nombres, meta y límite.');
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
      try { this.prueba.res = await this.api('/api/formula/probar', { method: 'POST', body: { formula: f.formula, valores, constantes, decimales: Number(f.decimales), meta: Number(f.meta), limite: Number(f.limite), meta_tope: f.meta_tope === '' ? null : f.meta_tope, limite_tope: f.limite_tope === '' ? null : f.limite_tope, sentido: f.sentido } }, true); } catch { }
    },
    cuerpoFicha(f) {
      return {
        codigo: f.codigo, nombre: f.nombre, objetivo: f.objetivo, area_id: f.area_id, unidad: f.unidad, frecuencia: f.frecuencia, sentido: f.sentido, formula: f.formula,
        variables: f.variables.map(v => ({ clave: v.clave, etiqueta: v.etiqueta, ayuda: v.ayuda || '', unidad: v.unidad || '', opcional: !!v.opcional, defecto: Number(v.defecto || 0), negativo: !!v.negativo })),
        constantes: (f.constantes || []).map(c => ({ clave: c.clave, etiqueta: c.etiqueta, valor: Number(c.valor) })),
        decimales: Number(f.decimales ?? 2), fuente: f.fuente || '', notas: f.notas || '', meta: f.meta, limite: f.limite,
        meta_tope: f.meta_tope === '' ? null : f.meta_tope, limite_tope: f.limite_tope === '' ? null : f.limite_tope, activo: f.activo,
        seguimiento: f.seguimiento || 'proceso', ref_nombre: f.ref_nombre || '', ref_detalle: f.ref_detalle || '', sigla: f.sigla || '', gerencia: f.gerencia || '',
        lider: f.lider || '', resp_medicion: f.resp_medicion || '', resp_registro: f.resp_registro || '', resp_analisis: f.resp_analisis || ''
      };
    },
    async guardarFicha() {
      this.busy = true;
      try {
        const f = this.ficha, id = f.id;
        await this.api(id ? `/api/indicadores/${id}` : '/api/indicadores', { method: id ? 'PUT' : 'POST', body: this.cuerpoFicha(f) });
        this.modal = false; this.avisar(id ? 'Ficha actualizada.' : 'Indicador creado.'); await this.cargarIndicadores();
      } catch { }
      this.busy = false;
    },
    async alternarActivo(i) {
      const accion = i.activo ? 'archivar' : 'restaurar';
      if (i.activo && !confirm(`¿Archivar ${i.codigo}? Dejará de aparecer para cargar datos; el historial se conserva.`)) return;
      try { await this.api(`/api/indicadores/${i.id}`, { method: 'PUT', body: this.cuerpoFicha({ ...i, activo: !i.activo }) }); this.avisar(`Indicador ${i.activo ? 'archivado' : 'restaurado'}.`); await this.cargarIndicadores(); } catch { }
    },
    async eliminarFicha(i) {
      const msg = i.n_mediciones ? `${i.codigo} tiene ${i.n_mediciones} carga(s) registradas: no se borrará, se archivará para conservar la trazabilidad. ¿Continuar?` : `¿Eliminar definitivamente el indicador ${i.codigo}?`;
      if (!confirm(msg)) return;
      try { const r = await this.api(`/api/indicadores/${i.id}`, { method: 'DELETE' }); this.avisar(r.archivado ? 'Indicador archivado (tiene historial de cargas).' : 'Indicador eliminado.'); await this.cargarIndicadores(); } catch { }
    },
    elegirRef() {
      const c = this.catalogos.find(c => c.tipo === 'proceso' && c.valor === this.ficha.ref_nombre);
      if (c && c.detalle && !this.ficha.ref_detalle) this.ficha.ref_detalle = c.detalle;
    },
    get sugerenciasPersonas() { return [...new Set(this.usuarios.map(u => u.nombre.split(' (')[0]))]; },
});
