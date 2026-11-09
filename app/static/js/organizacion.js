/* Organización: áreas, usuarios y listas de apoyo de la ficha (gerencias, procesos, objetivos, cargos). */
SIGT.modulos.organizacion = () => ({
    areas: [], usuarios: [], usrQ: '', catalogos: [], orgTab: 'equipo',
    usuario: {}, modalUsuario: false, areaForm: { id: null, nombre: '' },
    soporte: null, claveTemporal: '',
    catTab: 'proceso', catForm: { id: null, valor: '', detalle: '' },
    reinicio: { abierto: false, frase: '', password: '' },

    // Ganchos: el núcleo los invoca al ingresar, al entrar a una vista y al salir.
    ganchos: {
      entrar: { async org() { await Promise.all([this.cargarAreas(), this.cargarUsuarios(1), this.api('/api/catalogos').then(c => { this.catalogos = c; })]); } },
    },

    async cargarAreas() { this.areas = await this.api('/api/areas'); },
    // Usuarios: solo la página pedida (con búsqueda por nombre o usuario); el total llega en la cabecera
    async cargarUsuarios(pagina = 1) {
      const q = new URLSearchParams(); if (this.usrQ.trim()) q.set('q', this.usrQ.trim());
      this.usuarios = await this.pedirPagina('usuarios', '/api/usuarios?' + q, pagina);
    },
    async guardarArea() {
      this.busy = true;
      try {
        const id = this.areaForm.id;
        await this.api(id ? `/api/areas/${id}` : '/api/areas', { method: id ? 'PUT' : 'POST', body: { nombre: this.areaForm.nombre } });
        this.areaForm = { id: null, nombre: '' }; this.areas = await this.api('/api/areas'); await this.cargarUsuarios(this.pg('usuarios').pagina); this.avisar('Área guardada.');
      } catch { }
      this.busy = false;
    },
    async eliminarArea(a) {
      if (!confirm(`¿Eliminar el área «${a.nombre}»?`)) return;
      try { await this.api(`/api/areas/${a.id}`, { method: 'DELETE' }); this.areas = await this.api('/api/areas'); this.avisar('Área eliminada.'); } catch { }
    },
    nuevoUsuario() { this.claveTemporal = ''; this.usuario = { username: '', nombre: '', email: '', rol: 'jefe', area_id: '', password: '', activo: true }; this.modalUsuario = true; },
    editarUsuario(x) { this.claveTemporal = ''; this.usuario = { ...x, area_id: x.area_id || '', password: '' }; this.modalUsuario = true; },
    async guardarUsuario() {
      this.busy = true;
      try {
        const u = this.usuario, id = u.id;
        const body = { nombre: u.nombre, email: (u.email || '').trim(), rol: u.rol, area_id: u.rol === 'jefe' ? (u.area_id || null) : null };
        if (id) { body.activo = u.activo; if (u.password) body.password = u.password; } else { body.username = u.username; body.password = u.password; }
        await this.api(id ? `/api/usuarios/${id}` : '/api/usuarios', { method: id ? 'PUT' : 'POST', body });
        this.modalUsuario = false; await this.cargarUsuarios(this.pg('usuarios').pagina); this.avisar('Usuario guardado.');
      } catch { }
      this.busy = false;
    },
    // Inhabilitar: el usuario no puede ingresar y su historial se conserva (siempre disponible). Se revierte con «Habilitar».
    async alternarUsuario(x) {
      const accion = x.activo ? 'inhabilitar' : 'habilitar';
      if (x.activo && !confirm(`¿Inhabilitar a «${x.nombre}»? No podrá ingresar al sistema (su historial se conserva y puede habilitarlo de nuevo).`)) return;
      this.busy = true;
      try {
        await this.api(`/api/usuarios/${x.id}`, { method: 'PUT', body: { nombre: x.nombre, rol: x.rol, area_id: x.area_id || null, activo: !x.activo } });
        await this.cargarUsuarios(this.pg('usuarios').pagina); this.avisar(`Usuario ${accion === 'inhabilitar' ? 'inhabilitado' : 'habilitado'}.`);
      } catch { }
      this.busy = false;
    },
    // Eliminar: definitivo; solo para quien nunca tuvo actividad (creado por error). Con historial, el servidor lo rechaza.
    async eliminarUsuario(x) {
      if (!confirm(`¿Eliminar definitivamente a «${x.nombre}»? Esta acción no se puede deshacer.`)) return;
      this.busy = true;
      try { await this.api(`/api/usuarios/${x.id}`, { method: 'DELETE' }); await this.cargarUsuarios(this.pg('usuarios').pagina); this.avisar('Usuario eliminado.'); } catch { }
      this.busy = false;
    },
    // ------------------------------------------------------------ soporte a usuarios (administrador)
    abrirSoporte(x) { this.soporte = this.soporte === x.id ? null : x.id; },
    async cerrarSesiones(x) {
      if (!confirm(`¿Cerrar las sesiones abiertas de «${x.nombre}» en todos sus dispositivos? Deberá volver a ingresar.`)) return;
      this.busy = true;
      try { await this.api(`/api/usuarios/${x.id}/cerrar-sesiones`, { method: 'POST' }); this.avisar('Sesiones cerradas.'); } catch { }
      this.busy = false;
    },
    respFrase: '', restaurar: { archivo: null, frase: '', password: '', confirmacion: '' },
    async restaurarRespaldo() {
      if (!confirm('Se reemplazarán TODOS los datos actuales por los del respaldo. ¿Continuar?')) return;
      this.busy = true;
      try {
        const f = new FormData(); const r = this.restaurar;
        f.append('archivo', r.archivo); f.append('frase', r.frase); f.append('password', r.password); f.append('confirmacion', r.confirmacion);
        await this.api('/api/respaldo/restaurar', { method: 'POST', body: f });
        this.restaurar = { archivo: null, frase: '', password: '', confirmacion: '' };
        this.avisar('Respaldo restaurado. Vuelva a ingresar.'); setTimeout(() => location.reload(), 1500);
      } catch { }
      this.busy = false;
    },
    async descargarRespaldo() {
      this.busy = true;
      try {
        const r = await fetch('/api/respaldo', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ frase: this.respFrase }) });
        if (!r.ok) { let d = {}; try { d = await r.json(); } catch { } throw new Error(typeof d.detail === 'string' ? d.detail : 'No se pudo generar el respaldo.'); }
        const nombre = (r.headers.get('content-disposition') || '').match(/filename="?([^";]+)/)?.[1] || 'respaldo.sigtbak';
        const a = document.createElement('a'); a.href = URL.createObjectURL(await r.blob()); a.download = nombre; document.body.appendChild(a); a.click(); a.remove();
        setTimeout(() => URL.revokeObjectURL(a.href), 4000); this.respFrase = ''; this.avisar('Respaldo cifrado descargado. Guárdelo fuera del servidor.');
      } catch (e) { this.avisar(e.message, true); }
      this.busy = false;
    },
    async desbloquearAccesos() {
      if (!confirm('¿Levantar el bloqueo por intentos fallidos de ingreso? Los usuarios bloqueados podrán volver a intentarlo ya.')) return;
      this.busy = true;
      try { await this.api('/api/sistema/desbloquear-accesos', { method: 'POST' }); this.avisar('Accesos desbloqueados.'); } catch { }
      this.busy = false;
    },
    async verActividad(x) { this.bitUsuario = x.nombre; this.bitAccion = ''; await this.go('bitacora'); },
    // Clave temporal: aleatoria (criptográfica), de 14 caracteres sin letras ambiguas; el administrador la comunica al usuario
    generarClave() {
      const abc = 'abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789', r = crypto.getRandomValues(new Uint32Array(14));
      this.usuario.password = Array.from(r, n => abc[n % abc.length]).join(''); this.claveTemporal = this.usuario.password;
    },
    ultimoIngreso(x) { return x.ultimo_ingreso ? 'Último ingreso: ' + this.fecha(x.ultimo_ingreso) : 'Nunca ha ingresado'; },
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

    // ------------------------------------------------------------ reinicio de fábrica
    abrirReinicio() { this.reinicio = { abierto: true, frase: '', password: '' }; },
    async confirmarReinicio() {
      this.busy = true;
      try {
        await this.api('/api/sistema/reiniciar', { method: 'POST', body: { confirmacion: this.reinicio.frase, password: this.reinicio.password } });
        this.reinicio.abierto = false; this.avisar('Sistema reiniciado: todos los datos fueron borrados.');
        setTimeout(() => location.reload(), 1200);
      } catch { }
      this.busy = false;
    },
});
