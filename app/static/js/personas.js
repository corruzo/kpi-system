/* Personas: asignación de rol, ámbito (uno o varios nodos del árbol) e indicadores, con la vista «qué ve esta persona»;
   y, para el Desarrollador, cuentas (crear, inhabilitar, eliminar, clave temporal) y soporte técnico. */
SIGT.modulos.personas = () => ({
    usuarios: [], usrQ: '', soporte: null, claveTemporal: '', usuario: {}, modalUsuario: false,
    asig: null, previa: null, rolesLista: [], indPersona: null, indOpciones: [], indQ: '', desig: { abierto: false, x: null, password: '' },

    ganchos: {
      entrar: { async personas() {
        await this.cargarUsuarios(1);
        if (this.puede('usuarios.asignar') && !this.estructuraCargada) await this.cargarEstructura();
        if (this.puedeAlguno(['usuarios.asignar', 'roles.gestionar'])) this.rolesLista = await this.api('/api/roles');
      } },
      salida() { this.usuarios = []; this.asig = null; this.previa = null; },
    },

    async cargarUsuarios(pagina = 1) {
      const q = new URLSearchParams(); if (this.usrQ.trim()) q.set('q', this.usrQ.trim());
      this.usuarios = await this.pedirPagina('usuarios', '/api/usuarios?' + q, pagina);
    },
    ultimoIngreso(x) { return x.ultimo_ingreso ? 'Último ingreso: ' + this.fecha(x.ultimo_ingreso) : 'Nunca ha ingresado'; },
    nombreNodo(id) { const n = this.areas.find(a => a.id === id); return n ? n.nombre : '#' + id; },
    resumenPosicion(x) {
      if (x.pendiente) return 'Pendiente de asignación';
      if (x.rol_clave) return 'Alcance total: ve todo lo funcional (rol de sistema)';
      const p = [];
      if (x.ambito_raiz) p.push('toda la empresa');
      if (x.ambito.length) p.push('ve: ' + x.ambito.map(i => this.nombreNodo(i)).join(', '));
      if (x.miembro.length) p.push('trabaja en: ' + x.miembro.map(i => this.nombreNodo(i)).join(', '));
      if (x.responsable_de || x.cargador_de) p.push(`${x.responsable_de} a su cargo · ${x.cargador_de} que carga`);
      return p.join(' · ') || 'Sin ámbito: solo ve lo que se le asigne';
    },

    // ------------------------------------------------------------ rol y posición
    abrirAsignacion(x) {
      this.asig = { id: x.id, nombre: x.nombre, rol_id: x.rol_id || '', raiz: !!x.ambito_raiz, ambito: [...x.ambito], miembro: [...x.miembro] }; this.previa = null;
    },
    get rolesAsignables() { return this.rolesLista.filter(r => r.clave !== 'desarrollador'); },
    modoNodo(id) { return this.asig.ambito.includes(id) ? 'ambito' : this.asig.miembro.includes(id) ? 'miembro' : ''; },
    setModoNodo(id, modo) {
      this.asig.ambito = this.asig.ambito.filter(i => i !== id); this.asig.miembro = this.asig.miembro.filter(i => i !== id);
      if (modo === 'ambito') this.asig.ambito.push(id); else if (modo === 'miembro') this.asig.miembro.push(id);
      this.previa = null;
    },
    cuerpoAsignacion() { const a = this.asig; return { rol_id: a.rol_id ? Number(a.rol_id) : null, raiz: !!a.raiz, ambito: a.ambito, miembro: a.miembro }; },
    async verAlcance() {
      this.busy = true;
      try { this.previa = await this.api(`/api/usuarios/${this.asig.id}/alcance`, { method: 'POST', body: this.cuerpoAsignacion() }); } catch { }
      this.busy = false;
    },
    async guardarAsignacion() {
      this.busy = true;
      try { await this.api(`/api/usuarios/${this.asig.id}/asignacion`, { method: 'PUT', body: this.cuerpoAsignacion() }); this.asig = null; this.avisar('Asignación guardada.'); await this.cargarUsuarios(this.pg('usuarios').pagina); } catch { }
      this.busy = false;
    },

    // ------------------------------------------------------------ indicadores de la persona
    async abrirIndicadores(x) {
      this.busy = true;
      try {
        const [actual, todos] = await Promise.all([this.api(`/api/usuarios/${x.id}/indicadores`), this.api('/api/indicadores?gestion=true&limite=500')]);
        this.indOpciones = todos;
        this.indPersona = { id: x.id, nombre: x.nombre, puedeCargar: !!x.rol && (x.rol_clave || this.rolesLista.find(r => r.id === x.rol_id)?.permisos['cargas.cargar']),
          responsable: actual.responsable.map(i => i.id), cargador: actual.cargador.map(i => i.id), r0: actual.responsable.map(i => i.id) };
      } catch { }
      this.busy = false;
    },
    get indFiltrados() { const q = this.indQ.trim().toLowerCase(); return this.indOpciones.filter(i => !q || (i.codigo + ' ' + i.nombre).toLowerCase().includes(q)); },
    alternarInd(lista, id) { const l = this.indPersona[lista], k = l.indexOf(id); if (k >= 0) l.splice(k, 1); else l.push(id); },
    async guardarIndicadores() {
      this.busy = true;
      try {
        const p = this.indPersona;
        await this.api(`/api/usuarios/${p.id}/indicadores`, { method: 'PUT', body: { responsable: p.responsable, cargador: p.cargador } });
        this.indPersona = null; this.avisar('Indicadores asignados.'); await this.cargarUsuarios(this.pg('usuarios').pagina);
      } catch { }
      this.busy = false;
    },

    // ------------------------------------------------------------ cuentas (Desarrollador)
    nuevoUsuario() { this.claveTemporal = ''; this.usuario = { username: '', nombre: '', email: '', password: '', activo: true }; this.modalUsuario = true; },
    editarUsuario(x) { this.claveTemporal = ''; this.usuario = { ...x, password: '' }; this.modalUsuario = true; },
    async guardarUsuario() {
      this.busy = true;
      try {
        const u = this.usuario, id = u.id;
        const body = { nombre: u.nombre, email: (u.email || '').trim() };
        if (id) { body.activo = u.activo; if (u.password) body.password = u.password; } else { body.username = u.username; body.password = u.password; }
        await this.api(id ? `/api/usuarios/${id}` : '/api/usuarios', { method: id ? 'PUT' : 'POST', body });
        this.modalUsuario = false; await this.cargarUsuarios(this.pg('usuarios').pagina); this.avisar(id ? 'Cuenta guardada.' : 'Cuenta creada: queda pendiente de asignación.');
      } catch { }
      this.busy = false;
    },
    // Inhabilitar: no puede ingresar y su historial se conserva (siempre disponible). Se revierte con «Habilitar».
    async alternarUsuario(x) {
      if (x.activo && !confirm(`¿Inhabilitar a «${x.nombre}»? No podrá ingresar al sistema (su historial se conserva y puede habilitarlo de nuevo).`)) return;
      this.busy = true;
      try { await this.api(`/api/usuarios/${x.id}`, { method: 'PUT', body: { nombre: x.nombre, activo: !x.activo } }); await this.cargarUsuarios(this.pg('usuarios').pagina); this.avisar(`Usuario ${x.activo ? 'inhabilitado' : 'habilitado'}.`); } catch { }
      this.busy = false;
    },
    // Eliminar: definitivo; solo para quien nunca tuvo actividad (creado por error). Con historial, el servidor lo rechaza.
    async eliminarUsuario(x) {
      if (!confirm(`¿Eliminar definitivamente a «${x.nombre}»? Esta acción no se puede deshacer.`)) return;
      this.busy = true;
      try { await this.api(`/api/usuarios/${x.id}`, { method: 'DELETE' }); await this.cargarUsuarios(this.pg('usuarios').pagina); this.avisar('Usuario eliminado.'); } catch { }
      this.busy = false;
    },
    abrirSoporte(x) { this.soporte = this.soporte === x.id ? null : x.id; },
    async cerrarSesiones(x) {
      if (!confirm(`¿Cerrar las sesiones abiertas de «${x.nombre}» en todos sus dispositivos? Deberá volver a ingresar.`)) return;
      this.busy = true;
      try { await this.api(`/api/usuarios/${x.id}/cerrar-sesiones`, { method: 'POST' }); this.avisar('Sesiones cerradas.'); } catch { }
      this.busy = false;
    },
    async desbloquearAccesos() {
      if (!confirm('¿Levantar el bloqueo por intentos fallidos de ingreso? Los usuarios bloqueados podrán volver a intentarlo ya.')) return;
      this.busy = true;
      try { await this.api('/api/sistema/desbloquear-accesos', { method: 'POST' }); this.avisar('Accesos desbloqueados.'); } catch { }
      this.busy = false;
    },
    async verActividad(x) { this.bitUsuario = x.nombre; this.bitAccion = ''; await this.go('bitacora'); },
    // Clave temporal: aleatoria (criptográfica), de 14 caracteres sin letras ambiguas; quien la crea la comunica a la persona
    generarClave() {
      const abc = 'abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789', r = crypto.getRandomValues(new Uint32Array(14));
      this.usuario.password = Array.from(r, n => abc[n % abc.length]).join(''); this.claveTemporal = this.usuario.password;
    },
    // Procedimiento explícito entre Desarrolladores (pide la contraseña de quien lo ejecuta)
    abrirDesignar(x) { this.desig = { abierto: true, x, password: '' }; },
    async confirmarDesignar() {
      const d = this.desig, activar = d.x.rol_clave !== 'desarrollador'; this.busy = true;
      try { await this.api(`/api/usuarios/${d.x.id}/desarrollador`, { method: 'POST', body: { activar, password: d.password } }); this.desig.abierto = false; this.avisar(activar ? 'Cuenta designada como Desarrollador.' : 'Rol Desarrollador retirado.'); await this.cargarUsuarios(this.pg('usuarios').pagina); } catch { }
      this.busy = false;
    },
});
