/* Indicadores: lista según el rol y administración de fichas técnicas (alta, edición, fórmula, probador). */
SIGT.modulos.indicadores = () => ({
    indicadores: [],                                                     // los que el usuario puede cargar (selector de «Cargar datos»)
    fichas: [],                                                          // página de la lista «Indicadores»
    opcionesUsuarios: [],                                                // personas a las que puede asignar (él mismo y quienes están debajo)
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
    // Quien carga datos recibe aquí SUS indicadores (aquellos de los que es cargador); los demás ven la lista en «Indicadores».
    async cargarIndicadores() {
      if (!this.user || !this.puede('cargas.cargar')) { this.indicadores = []; return; }
      this.indicadores = await this.api('/api/indicadores?cargables=true' + (this.ejSel ? '&ejercicio=' + this.ejSel : ''));
    },
    // Lista de gestión: el servidor filtra y entrega solo la página pedida (incluye archivados)
    async cargarFichas(pagina = 1) {
      const q = new URLSearchParams({ gestion: 'true' });
      if (this.ejSel) q.set('ejercicio', this.ejSel);
      if (this.fq.q.trim()) q.set('q', this.fq.q.trim());
      if (this.fq.area) q.set('nodo_id', this.fq.area);
      if (this.fq.frecuencia) q.set('frecuencia', this.fq.frecuencia);
      if (this.fq.estado) q.set('activo', this.fq.estado === 'activo');
      this.fichas = await this.pedirPagina('fichas', '/api/indicadores?' + q, pagina);
    },
    // Personas a las que se puede asignar. Se piden de nuevo al abrir cada ficha: si alguien se creó o se reasignó en «Personas»,
    // aparece de inmediato (antes quedaban en memoria toda la sesión y había que recargar la página).
    async cargarOpcionesUsuarios(forzar = false) {
      if ((forzar || !this.opcionesUsuarios.length) && this.puedeAlguno(['indicadores.crear', 'indicadores.asignar'])) this.opcionesUsuarios = await this.api('/api/usuarios/opciones', {}, true);
    },
    // Tras crear, editar o eliminar: se refresca la página actual y la lista de carga
    async refrescarIndicadores() { await Promise.all([this.cargarFichas(this.pg('fichas').pagina), this.cargarIndicadores()]); },
    codigoSugerido: '',
    get etiquetaNC() { return (this.params.codigo_formato || 'NC-16').split('-').slice(0, 2).join('-'); },
    // Asignación: nodo de la estructura, responsable (el «dueño», único que modifica la ficha) y quienes cargan el dato.
    // Primero quienes están en la rama del nodo elegido (el nodo, sus superiores o lo que cuelga de él); el resto, al final y marcado
    get ramaDelNodo() {
      const porId = Object.fromEntries(this.areas.map(a => [a.id, a])), objetivo = this.ficha.nodo_id, rama = new Set();
      for (let n = porId[objetivo]; n; n = porId[n.padre_id]) rama.add(n.id);
      for (const a of this.areas) for (let n = a; n; n = porId[n.padre_id]) if (n.id === objetivo) { rama.add(a.id); break; }
      return rama;
    },
    get opcionesOrdenadas() {
      const rama = this.ramaDelNodo;
      return this.opcionesUsuarios.map(u => ({ ...u, lejos: !u.yo && ![...u.ambito, ...u.miembro].some(n => rama.has(n)) }))
        .sort((a, b) => a.lejos - b.lejos || a.nombre.localeCompare(b.nombre));
    },
    nodoEtiqueta(a) { return '\u2003'.repeat(a.profundidad || 0) + a.nombre + ' · ' + (NIVEL_ETIQUETA[a.nivel] || ''); },
    get puedeEditarFicha() { return !this.ficha.id || (this.ficha.puede_modificar && this.puede('indicadores.editar')); },
    get puedeAsignarFicha() { return !this.ficha.id || (this.puede('indicadores.asignar') && this.ficha.puede_modificar); },
    get asignacionCambio() { return !!this.ficha.id && JSON.stringify([this.ficha.nodo_id, this.ficha.responsable_id, this.ficha.suplente_id || null]) !== this.ficha._asig; },
    cambioDeNodo() { this.pedirCodigo(); this.proponerAsignacion(); },
    // En cascada: al elegir el nodo se propone solo quién lo lleva. Responsable principal y suplente son dos personas que pueden cargar:
    // primero quienes trabajan en el nodo (o más arriba en su rama), luego quienes lo tienen en su ámbito; si no hay nadie, quien crea.
    proponerAsignacion() {
      if (this.ficha.id) return;
      const porId = Object.fromEntries(this.areas.map(a => [a.id, a])), cadena = [];
      for (let n = porId[this.ficha.nodo_id]; n; n = porId[n.padre_id]) cadena.push(n.id);   // el nodo y sus superiores
      const opc = this.opcionesUsuarios.filter(u => u.puede_cargar);
      const aqui = opc.filter(u => u.miembro.some(m => cadena.includes(m)));
      const jefes = opc.filter(u => !u.yo && u.ambito.some(a => cadena.includes(a)) && !aqui.includes(u));
      const lista = [...aqui, ...jefes], yo = opc.find(u => u.yo);
      const quienes = lista.length ? lista : (yo ? [yo] : []);
      this.ficha.responsable_id = quienes[0]?.id ?? null;
      this.ficha.suplente_id = quienes[1]?.id ?? null;
    },
    puedeEditarI(i) { return this.puede('indicadores.editar') && i.puede_modificar; },
    puedeAsignarI(i) { return this.puede('indicadores.asignar') && i.puede_modificar; },
    async pedirCodigo() {
      if (this.ficha.id || !this.ficha.nodo_id) { this.codigoSugerido = ''; return; }
      try { this.codigoSugerido = (await this.api(`/api/indicadores/codigo-sugerido?nodo_id=${this.ficha.nodo_id}`)).codigo; } catch { this.codigoSugerido = ''; }
    },
    nuevaFicha() {
      this.ficha = { codigo: '', nombre: '', objetivo: '', nodo_id: (this.areas.find(a => a.nivel === 'jefatura') || this.areas[0])?.id, responsable_id: null, suplente_id: null, unidad: '%', frecuencia: 'mensual', decimales: 2, sentido: 'mayor', nivel_optimo: 90, limite: 80, nivel_optimo_tope: null, limite_tope: null, formula: '', seguimiento: 'proceso', ref_nombre: '', ref_detalle: '', sigla: '', gerencia: '', lider: '', resp_medicion: '', resp_registro: '', resp_analisis: '', variables: [{ clave: '', etiqueta: '' }, { clave: '', etiqueta: '' }], constantes: [], fuente: '', notas: '', activo: true, n_mediciones: 0 };
      this.abrirFicha('Escriba la fórmula con las claves de las variables; use los botones «i» como ayuda.');
      this.pedirCodigo(); this.cargarOpcionesUsuarios(true).then(() => this.proponerAsignacion());
    },
    editarFicha(i) {
      this.ficha = JSON.parse(JSON.stringify(i)); this.ficha.constantes ||= [];
      this.ficha._asig = JSON.stringify([i.nodo_id, i.responsable_id, i.suplente_id || null]);
      [...this.ficha.variables, ...this.ficha.constantes].forEach(v => v._manual = true);
      this.abrirFicha(''); this.validarFormula(); this.codigoSugerido = ''; this.cargarOpcionesUsuarios(true);
    },
    duplicarFicha(i) {
      this.ficha = { ...JSON.parse(JSON.stringify(i)), id: undefined, codigo: '', nombre: i.nombre + ' (copia)', n_mediciones: 0, activo: true, responsable_id: null, suplente_id: null, puede_modificar: true, en_ambito: true };
      this.ficha.constantes ||= [];
      [...this.ficha.variables, ...this.ficha.constantes].forEach(v => v._manual = true);
      this.abrirFicha('Ficha duplicada: el sistema le asignará un código nuevo.'); this.validarFormula(); this.pedirCodigo(); this.cargarOpcionesUsuarios(true).then(() => this.proponerAsignacion());
    },
    abrirFicha(msg) { this.formulaMsg = { ok: true, txt: msg }; this.prueba = { valores: {}, res: null }; this.ay = ''; this.modal = true; },
    get fichaBloqueada() { return (this.ficha.n_mediciones || 0) > 0; },
    slug: t => t.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '').replace(/^(\d)/, 'v$1').slice(0, 30),
    autoClave(v) { if (!this.fichaBloqueada && !v._manual) { v.clave = this.slug(v.etiqueta); this.validarFormula(); } },
    mover(idx, d) { const a = this.ficha.variables, j = idx + d; if (j < 0 || j >= a.length) return; [a[idx], a[j]] = [a[j], a[idx]]; },
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
      if (!this.ficha.formula || !this.puede('formulas.probar')) return;   // sin ese permiso no se valida en vivo
      try {
        const r = await this.api('/api/formula/validar', { method: 'POST', body: { formula: this.ficha.formula, claves: this.nombresFormula, variables: this.ficha.variables.map(v => v.clave).filter(Boolean) } }, true);
        this.formulaMsg = !r.ok ? { ok: false, txt: r.error } : r.sin_usar.length ? { ok: true, aviso: true, txt: '✔ Válida, pero no usa: ' + r.sin_usar.join(', ') } : { ok: true, txt: '✔ Fórmula válida' };
        if (r.ok) this.probar();
      } catch { }
    },
    async probar() {
      if (!this.puede('formulas.probar')) return;
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
        codigo: f.id ? f.codigo : '', nodo_id: f.nodo_id, responsable_id: f.responsable_id || null, suplente_id: f.suplente_id || null, nombre: f.nombre, objetivo: f.objetivo, unidad: f.unidad, frecuencia: f.frecuencia, sentido: f.sentido, formula: f.formula,
        variables: f.variables.map(v => ({ clave: v.clave, etiqueta: v.etiqueta, ayuda: v.ayuda || '', unidad: v.unidad || '', opcional: !!v.opcional, defecto: Number(v.defecto || 0), negativo: !!v.negativo })),
        constantes: (f.constantes || []).map(c => ({ clave: c.clave, etiqueta: c.etiqueta, valor: Number(c.valor) })),
        decimales: Number(f.decimales ?? 2), fuente: f.fuente || '', notas: f.notas || '', nivel_optimo: f.nivel_optimo, limite: f.limite,
        nivel_optimo_tope: f.nivel_optimo_tope === '' ? null : f.nivel_optimo_tope, limite_tope: f.limite_tope === '' ? null : f.limite_tope,
        seguimiento: f.seguimiento || 'proceso', ref_nombre: f.ref_nombre || '', ref_detalle: f.ref_detalle || '', sigla: f.sigla || '', gerencia: f.gerencia || '',
        lider: f.lider || '', resp_medicion: f.resp_medicion || '', resp_registro: f.resp_registro || '', resp_analisis: f.resp_analisis || ''
      };
    },
    async guardarFicha() {
      this.busy = true;
      try {
        const f = this.ficha, id = f.id;
        let nuevo = null;
        if (!id) nuevo = await this.api('/api/indicadores', { method: 'POST', body: this.cuerpoFicha(f) });
        else {
          if (this.puedeEditarFicha) await this.api(`/api/indicadores/${id}`, { method: 'PUT', body: this.cuerpoFicha(f) });
          if (this.puedeAsignarFicha && this.asignacionCambio) await this.api(`/api/indicadores/${id}/asignacion`, { method: 'PUT', body: { nodo_id: f.nodo_id, responsable_id: f.responsable_id, suplente_id: f.suplente_id || null } });
        }
        this.modal = false; await this.refrescarIndicadores();
        // En cascada: un indicador nuevo necesita su meta; si quien lo crea puede fijarla, se abre directamente en «Período y metas»
        if (nuevo && this.puede('metas.cargar')) { this.avisar('Indicador creado. Ahora fije su meta.'); this.metaDestacada = nuevo.id; return this.go('meta'); }
        this.avisar(id ? 'Ficha actualizada.' : 'Indicador creado.');
      } catch { }
      this.busy = false;
    },
    async alternarActivo(i) {
      const archivar = i.activo;
      if (archivar && !confirm(`¿Archivar ${i.codigo}? Dejará de aparecer para cargar datos; el historial se conserva.`)) return;
      try { await this.api(`/api/indicadores/${i.id}/${archivar ? 'archivar' : 'restaurar'}`, { method: 'POST' }); this.avisar(`Indicador ${archivar ? 'archivado' : 'restaurado'}.`); await this.refrescarIndicadores(); } catch { }
    },
    async eliminarFicha(i) {
      if (i.n_mediciones) { this.avisar(`${i.codigo} tiene ${i.n_mediciones} carga(s) registradas: no puede eliminarse sin perder la trazabilidad. Archívelo.`, true); return; }
      if (!confirm(`¿Eliminar definitivamente el indicador ${i.codigo}?`)) return;
      try { await this.api(`/api/indicadores/${i.id}`, { method: 'DELETE' }); this.avisar('Indicador eliminado.'); await this.refrescarIndicadores(); } catch { }
    },
    get sugerenciasPersonas() { return [...new Set(this.opcionesUsuarios.map(u => u.nombre.split(' (')[0]))]; },

    // Opciones de las listas desplegables de la ficha (ver js/combo.js)
    get opcionesNodos() { return this.areas.map(a => ({ valor: a.id, etiqueta: a.nombre, detalle: a.ruta !== a.nombre ? a.ruta : '', chip: NIVEL_ETIQUETA[a.nivel] || '', nivel: a.profundidad || 0 })); },
    // Responsable principal y suplente cargan datos: solo se ofrecen personas cuyo rol lo permite (y el suplente, otra distinta)
    get opcionesResponsable() { return this.opcionesDeCarga(null); },
    get opcionesSuplente() { return [{ valor: '', etiqueta: 'Sin suplente', tenue: true }, ...this.opcionesDeCarga(this.ficha.responsable_id)]; },
    opcionesDeCarga(excepto) {
      return this.opcionesOrdenadas.filter(u => u.puede_cargar && u.id !== excepto)
        .map(u => ({ valor: u.id, etiqueta: u.nombre + (u.yo ? ' (usted)' : ''), detalle: [u.rol, u.lejos ? 'otra área' : ''].filter(Boolean).join(' · '), tenue: u.lejos }));
    },
    get opcionesNombres() { return this.sugerenciasPersonas.map(n => ({ valor: n, etiqueta: n })); },
    opcSeguimiento: [{ valor: 'proceso', etiqueta: 'Desempeño de proceso' }, { valor: 'objetivo', etiqueta: 'Objetivo organizacional' }, { valor: 'proveedor', etiqueta: 'Desempeño de proveedor externo' }],
    opcFrecuencia: [['mensual', 'Mensual'], ['bimestral', 'Bimestral'], ['trimestral', 'Trimestral'], ['cuatrimestral', 'Cuatrimestral'], ['semestral', 'Semestral'], ['anual', 'Anual'], ['eventual', 'Eventual (cuando ocurra)']].map(([valor, etiqueta]) => ({ valor, etiqueta })),
    opcSentido: [{ valor: 'mayor', etiqueta: 'Mayor es mejor (ej. cumplimiento)' }, { valor: 'menor', etiqueta: 'Menor es mejor (ej. obsolescencia, tiempo)' }],
    opcUnidad: ['%', 'días', 'horas', 'TM', 'kg', 'USD', 'cantidad'].map(u => ({ valor: u, etiqueta: u })),
});
