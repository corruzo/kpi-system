/* Configuración: parámetros y logo, listas de apoyo de la ficha, respaldo cifrado y reinicio de fábrica.
   (La estructura de la empresa, los roles y las personas tienen sus propios módulos.) */
SIGT.modulos.organizacion = () => ({
    catalogos: [], orgTab: 'empresa',
    catTab: 'proceso', catForm: { id: null, valor: '', detalle: '' },
    reinicio: { abierto: false, frase: '', password: '' },

    // Ganchos: el núcleo los invoca al ingresar, al entrar a una vista y al salir.
    ganchos: {
      entrar: { async config() {
        this.orgTab = this.configTabs[0]?.[0] || 'empresa';
        if (this.puede('catalogos.gestionar')) this.catalogos = await this.api('/api/catalogos');
      } },
    },
    // Pestañas disponibles según los permisos de la persona
    get configTabs() {
      return [['empresa', 'Empresa y logo', 'parametros.gestionar'], ['listas', 'Listas de apoyo', 'catalogos.gestionar'],
        ['avanzado', 'Avanzado', ['respaldo.exportar', 'respaldo.restaurar', 'sistema.reiniciar']]].filter(([, , p]) => this.puedeAlguno([].concat(p)));
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
