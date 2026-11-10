/* Roles y permisos: lista de roles y editor con la matriz de permisos agrupada por módulo. El alcance de cada permiso es fijo
   (lo aplica el servidor); aquí solo se elige el NIVEL: Ninguno · Ver · Ver y modificar (o Ninguno · Sí). Nunca muestra permisos técnicos. */
SIGT.modulos.roles = () => ({
    roles: [], catalogoP: { grupos: [], permisos: [] }, rolForm: null, rolQ: '', rolCopia: { id: null, nombre: '' },

    ganchos: {
      entrar: { roles() { return this.cargarRoles(); } },
      salida() { this.roles = []; this.rolForm = null; },
    },

    async cargarRoles() {
      const [roles, cat] = await Promise.all([this.api('/api/roles'), this.api('/api/permisos')]);
      this.roles = roles; this.catalogoP = cat; this.rolForm = null; this.rolCopia = { id: null, nombre: '' };
    },
    nuevoRol() { this.rolForm = { id: null, nombre: '', descripcion: '', permisos: {}, editable: true, de_sistema: false, motivo: '' }; this.rolQ = ''; this.$nextTick(() => document.getElementById('rol-nombre')?.focus()); },
    editarRol(r) { this.rolForm = { id: r.id, nombre: r.nombre, descripcion: r.descripcion, permisos: { ...r.permisos }, editable: r.editable, de_sistema: r.de_sistema, motivo: r.motivo, usuarios: r.usuarios }; this.rolQ = ''; this.$nextTick(() => document.getElementById('rol-editor')?.scrollIntoView({ behavior: 'smooth', block: 'start' })); },
    // Niveles que ofrece cada permiso, hasta el máximo que quien edita puede conceder (nadie concede lo que no tiene)
    opcionesNivel(p) {
      const todos = p.niveles.length === 1 && p.niveles[0] === 'modificar' ? [['', 'Ninguno'], ['modificar', 'Sí']] : p.niveles.length === 1 ? [['', 'Ninguno'], ['ver', 'Sí']] : [['', 'Ninguno'], ['ver', 'Ver'], ['modificar', 'Ver y modificar']];
      const orden = { ver: 1, modificar: 2 }, tope = p.tope ? orden[p.tope] : 0;
      return todos.filter(([v]) => !v || orden[v] <= tope);
    },
    nivelDe(p) { return this.rolForm?.permisos[p.codigo] || ''; },
    setNivel(p, v) {
      const m = this.rolForm.permisos;
      if (!v) delete m[p.codigo]; else m[p.codigo] = v;
      if (v) this.agregarImplicados(p);
    },
    // Lo que un permiso necesita para servir se concede junto con él (el servidor hace lo mismo al guardar)
    agregarImplicados(p) {
      for (const c of p.implica) { const q = this.catalogoP.permisos.find(x => x.codigo === c); if (q && !this.rolForm.permisos[c]) { this.rolForm.permisos[c] = q.niveles[0]; this.agregarImplicados(q); } }
    },
    esImplicado(p) { return Object.keys(this.rolForm?.permisos || {}).some(c => this.catalogoP.permisos.find(x => x.codigo === c)?.implica.includes(p.codigo)); },
    permisosDe(grupo) {
      const q = this.rolQ.trim().toLowerCase();
      return this.catalogoP.permisos.filter(p => p.grupo === grupo && (!q || (p.etiqueta + ' ' + p.descripcion + ' ' + p.codigo).toLowerCase().includes(q)));
    },
    gruposVisibles() { return this.catalogoP.grupos.filter(g => this.permisosDe(g).length); },
    // Resumen en lenguaje natural de lo que el rol permite (una frase por módulo)
    get resumenRol() {
      if (!this.rolForm) return [];
      const frases = [];
      for (const g of this.catalogoP.grupos) {
        const en = this.catalogoP.permisos.filter(p => p.grupo === g && this.rolForm.permisos[p.codigo]);
        if (en.length) frases.push(`${g}: ` + en.map(p => p.etiqueta.toLowerCase() + (this.rolForm.permisos[p.codigo] === 'modificar' && p.niveles.length > 1 ? ' (puede modificar)' : '')).join(', ') + '.');
      }
      return frases.length ? frases : ['Este rol no puede hacer nada todavía.'];
    },
    get puedeLeerTodo() { return !!this.rolForm && ['indicadores.ver'].every(c => this.rolForm.permisos[c]); },
    async guardarRol() {
      const f = this.rolForm; this.busy = true;
      try {
        const body = { nombre: f.nombre, descripcion: f.descripcion, permisos: f.permisos };
        await this.api(f.id ? `/api/roles/${f.id}` : '/api/roles', { method: f.id ? 'PUT' : 'POST', body });
        this.avisar('Rol guardado. Rige desde la siguiente petición de cada persona.'); await this.cargarRoles();
      } catch { }
      this.busy = false;
    },
    abrirDuplicar(r) { this.rolCopia = { id: r.id, nombre: r.nombre + ' (copia)' }; },
    async duplicarRol() {
      this.busy = true;
      try { await this.api(`/api/roles/${this.rolCopia.id}/duplicar`, { method: 'POST', body: { nombre: this.rolCopia.nombre } }); this.avisar('Rol duplicado.'); await this.cargarRoles(); } catch { }
      this.busy = false;
    },
    async eliminarRol(r) {
      if (!confirm(`¿Eliminar el rol «${r.nombre}»?`)) return;
      try { await this.api(`/api/roles/${r.id}`, { method: 'DELETE' }); this.avisar('Rol eliminado.'); await this.cargarRoles(); } catch { }
    },
});
