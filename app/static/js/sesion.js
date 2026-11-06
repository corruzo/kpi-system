/* Sesión: ingreso, salida, perfil y cambio de contraseña. */
SIGT.modulos.sesion = () => ({
    user: null, loginForm: { username: '', password: '' }, loginError: '', verClave: false,
    modalClave: false, clave: { actual: '', nueva: '', repetir: '' },

    async login() {
      this.busy = true; this.loginError = '';
      try { this.user = await this.api('/api/login', { method: 'POST', body: this.loginForm }, true); }
      catch (e) { this.loginError = e.message; this.busy = false; return; }
      this.loginForm.password = ''; this.verClave = false;
      try { await this.abrirSesion(); } catch (e) { if (!e.avisado) this.avisar('No se pudieron cargar todos los datos. Recargue la página.', true); }
      this.busy = false;
    },
    async logout() {
      await this.api('/api/logout', { method: 'POST' });
      this.user = null; this.view = ''; this.menu = false;
      for (const limpiar of this.ganchos.salida) limpiar.call(this);
      try { ['sigt_panel', 'sigt_ej'].forEach(k => localStorage.removeItem(k)); } catch { }   // nada de la sesión queda en el equipo
    },
    iniciales(u = this.user) { return u.nombre.split(' (')[0].split(' ').filter(Boolean).slice(0, 2).map(w => w[0]).join('').toUpperCase(); },
    rolNombre: u => ROLES[u.rol],
    abrirClave() { this.menu = false; this.clave = { actual: '', nueva: '', repetir: '' }; this.modalClave = true; },
    async cambiarClave() {
      this.busy = true;
      try { await this.api('/api/cambiar-clave', { method: 'POST', body: { actual: this.clave.actual, nueva: this.clave.nueva } }); this.modalClave = false; this.avisar('Contraseña actualizada.'); } catch { }
      this.busy = false;
    },
});
