/* Estructura de la empresa: árbol de gerencias → departamentos → jefaturas (de él depende quién ve qué). */
SIGT.modulos.estructura = () => ({
    arbol: [], ultimoNodo: null, nodoForm: { id: null, nombre: '', nivel: 'gerencia', padre_id: null }, moverForm: { id: null, padre_id: '' }, estructuraCargada: false,

    ganchos: {
      entrar: { estructura() { return this.cargarEstructura(); } },
      salida() { this.arbol = []; this.areas = []; },
    },

    async cargarEstructura() {
      this.arbol = await this.api('/api/unidades'); this.areas = this.arbol; this.estructuraCargada = true;
      this.nodoForm = { id: null, nombre: '', nivel: 'gerencia', padre_id: null }; this.moverForm = { id: null, padre_id: '' };
    },
    // Con permiso de ver la estructura se pide el árbol completo; si no, las unidades que ya traía el arranque.
    async refrescarUnidades() {
      if (this.puede('estructura.ver')) { this.arbol = await this.api('/api/unidades'); this.areas = this.arbol; }
      else this.areas = (await this.api('/api/arranque')).unidades || [];
    },
    get puedeGestionarEstructura() { return this.puede('estructura.gestionar'); },
    nivelSiguiente: n => ({ gerencia: 'departamento', departamento: 'jefatura' }[n] || null),
    etiquetaNivel: n => NIVEL_ETIQUETA[n] || n,
    // «Nueva gerencia», «Nuevo departamento», «Nueva jefatura»
    nuevo: n => (n === 'departamento' ? 'Nuevo ' : 'Nueva ') + (NIVEL_ETIQUETA[n] || n).toLowerCase(),
    nuevoHijo(n) { this.nodoForm = { id: null, nombre: '', nivel: this.nivelSiguiente(n.nivel), padre_id: n.id }; this.$nextTick(() => document.getElementById('nodo-nombre')?.focus()); },
    otroDelMismoNivel() { const u = this.ultimoNodo; if (u) this.nodoForm = { id: null, nombre: '', nivel: u.nivel, padre_id: u.padre_id }; this.$nextTick(() => document.getElementById('nodo-nombre')?.focus()); },
    nuevaGerencia() { this.nodoForm = { id: null, nombre: '', nivel: 'gerencia', padre_id: null }; },
    renombrar(n) { this.nodoForm = { id: n.id, nombre: n.nombre, nivel: n.nivel, padre_id: n.padre_id }; this.$nextTick(() => document.getElementById('nodo-nombre')?.focus()); },
    get tituloNodoForm() {
      const f = this.nodoForm, padre = this.arbol.find(a => a.id === f.padre_id);
      return f.id ? `Renombrar ${this.etiquetaNivel(f.nivel).toLowerCase()}` : f.padre_id ? `${this.nuevo(f.nivel)} en «${padre?.nombre || ''}»` : 'Nueva gerencia';
    },
    async guardarNodo() {
      const f = this.nodoForm; this.busy = true;
      try {
        let creado = null;
        if (f.id) await this.api(`/api/unidades/${f.id}`, { method: 'PUT', body: { nombre: f.nombre } });
        else creado = await this.api('/api/unidades', { method: 'POST', body: { nombre: f.nombre, nivel: f.nivel, padre_id: f.padre_id } });
        await this.cargarEstructura();
        // En cascada: tras crear, el formulario queda listo para el nivel de abajo («Nuevo departamento en «Gerencia X»»)
        if (creado) {
          this.ultimoNodo = creado;
          if (this.nivelSiguiente(creado.nivel)) this.nuevoHijo(creado);
          this.avisar(`«${creado.nombre}» creado. ${this.nivelSiguiente(creado.nivel) ? 'Siga con lo que cuelga de él' : 'Puede agregar otro del mismo nivel'}.`);
        } else this.avisar('Estructura actualizada.');
      } catch { }
      this.busy = false;
    },
    // Posibles nuevos padres de un nodo: los del nivel que le corresponde, salvo su padre actual
    padresPosibles(n) {
      const nivelPadre = { departamento: 'gerencia', jefatura: 'departamento' }[n.nivel];
      return this.arbol.filter(a => a.nivel === nivelPadre && a.id !== n.padre_id);
    },
    puedeMover: n => n.nivel !== 'gerencia',
    abrirMover(n) { this.moverForm = { id: this.moverForm.id === n.id ? null : n.id, padre_id: '' }; },
    async confirmarMover(n) {
      if (!this.moverForm.padre_id) return;
      this.busy = true;
      try { await this.api(`/api/unidades/${n.id}/mover`, { method: 'POST', body: { padre_id: Number(this.moverForm.padre_id) } }); this.avisar('«' + n.nombre + '» y todo lo que cuelga de él se movieron.'); await this.cargarEstructura(); } catch { }
      this.busy = false;
    },
    async eliminarNodo(n) {
      if (!confirm(`¿Eliminar «${n.nombre}»? Solo se puede si no tiene nodos debajo, personas ni indicadores.`)) return;
      try { await this.api(`/api/unidades/${n.id}`, { method: 'DELETE' }); this.avisar('Nodo eliminado.'); await this.cargarEstructura(); } catch { }
    },
});
