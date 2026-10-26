/* Organización: áreas, usuarios y listas de apoyo de la ficha (gerencias, procesos, objetivos, cargos). */
SIGT.modulos.organizacion = () => ({
    areas: [], usuarios: [], catalogos: [],
    usuario: {}, modalUsuario: false, areaForm: { id: null, nombre: '' },
    catTab: 'proceso', catForm: { id: null, valor: '', detalle: '' },

    // Ganchos: el núcleo los invoca al ingresar, al entrar a una vista y al salir.
    ganchos: {
      async ingreso() {
        if (this.user.rol !== 'jefe') await this.cargarAreas();
        if (this.user.rol === 'admin') { this.catalogos = await this.api('/api/catalogos'); this.usuarios = await this.api('/api/usuarios'); }
      },
      entrar: { async org() { await this.cargarAreas(); this.usuarios = await this.api('/api/usuarios'); this.catalogos = await this.api('/api/catalogos'); } },
    },

    async cargarAreas() { this.areas = await this.api('/api/areas'); },
    setup() {
      const pasos = [
        { n: 1, t: 'Crear las áreas de la empresa', ok: this.areas.length > 0, v: 'org' },
        { n: 2, t: 'Registrar usuarios (jefes de área y gerente / auditor)', ok: this.usuarios.some(u => u.rol === 'jefe') && this.usuarios.some(u => u.rol === 'gerente'), v: 'org' },
        { n: 3, t: 'Crear las fichas de indicadores', ok: this.indicadores.length > 0, v: 'fichas' }];
      return { pasos, completo: pasos.every(p => p.ok) };
    },
    async guardarArea() {
      this.busy = true;
      try {
        const id = this.areaForm.id;
        await this.api(id ? `/api/areas/${id}` : '/api/areas', { method: id ? 'PUT' : 'POST', body: { nombre: this.areaForm.nombre } });
        this.areaForm = { id: null, nombre: '' }; this.areas = await this.api('/api/areas'); this.usuarios = await this.api('/api/usuarios'); this.avisar('Área guardada.');
      } catch { }
      this.busy = false;
    },
    async eliminarArea(a) {
      if (!confirm(`¿Eliminar el área «${a.nombre}»?`)) return;
      try { await this.api(`/api/areas/${a.id}`, { method: 'DELETE' }); this.areas = await this.api('/api/areas'); this.avisar('Área eliminada.'); } catch { }
    },
    nuevoUsuario() { this.usuario = { username: '', nombre: '', rol: 'jefe', area_id: '', password: '', activo: true }; this.modalUsuario = true; },
    editarUsuario(x) { this.usuario = { ...x, area_id: x.area_id || '', password: '' }; this.modalUsuario = true; },
    async guardarUsuario() {
      this.busy = true;
      try {
        const u = this.usuario, id = u.id;
        const body = { nombre: u.nombre, rol: u.rol, area_id: u.rol === 'jefe' ? (u.area_id || null) : null };
        if (id) { body.activo = u.activo; if (u.password) body.password = u.password; } else { body.username = u.username; body.password = u.password; }
        await this.api(id ? `/api/usuarios/${id}` : '/api/usuarios', { method: id ? 'PUT' : 'POST', body });
        this.modalUsuario = false; this.usuarios = await this.api('/api/usuarios'); this.avisar('Usuario guardado.');
      } catch { }
      this.busy = false;
    },
    get catActual() { return this.catalogos.filter(c => c.tipo === this.catTab); },
    async guardarCat() {
      this.busy = true;
      try {
        const f = this.catForm, id = f.id;
        await this.api(id ? `/api/catalogos/${id}` : '/api/catalogos', { method: id ? 'PUT' : 'POST', body: { tipo: this.catTab, valor: f.valor, detalle: f.detalle } });
        this.catForm = { id: null, valor: '', detalle: '' }; this.catalogos = await this.api('/api/catalogos'); this.avisar('Lista actualizada.');
      } catch { }
      this.busy = false;
    },
    async eliminarCat(c) {
      if (!confirm(`¿Quitar «${c.valor}» de la lista? Las fichas que ya lo usan conservan el texto.`)) return;
      try { await this.api(`/api/catalogos/${c.id}`, { method: 'DELETE' }); this.catalogos = await this.api('/api/catalogos'); } catch { }
    },
    lista(tipo) { return this.catalogos.filter(c => c.tipo === tipo); },
});
