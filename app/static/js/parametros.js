/* Parámetros del sistema (empresa, formato, inicio del ejercicio fiscal) y logo de la empresa. */
SIGT.modulos.parametros = () => ({
    marca: { empresa: '', logo_url: null },     // datos públicos: visibles antes de iniciar sesión
    params: {}, parForm: {},

    // Ganchos: el núcleo los invoca al ingresar, al entrar a una vista y al salir.
    ganchos: {
      ingreso() { return this.cargarParametros(); },
      entrar: { org() { this.parForm = { ...this.params }; } },
    },

    async cargarParametros() { this.params = await this.api('/api/parametros'); },
    async guardarParametros() {
      this.busy = true;
      try { this.params = await this.api('/api/parametros', { method: 'PUT', body: { empresa: this.parForm.empresa, gerencia_emisora: this.parForm.gerencia_emisora, codigo_formato: this.parForm.codigo_formato, ejercicio_inicio: Number(this.parForm.ejercicio_inicio) } }); this.parForm = { ...this.params }; this.avisar('Parámetros guardados.'); } catch { }
      this.busy = false;
    },
    get logoUrl() { return this.params.logo_url || this.marca.logo_url; },
    reducirImagen(file, max = 600) {
      return new Promise((ok, mal) => {
        const fr = new FileReader();
        fr.onerror = () => mal(new Error('No se pudo leer el archivo.'));
        fr.onload = () => {
          const img = new Image();
          img.onerror = () => mal(new Error('El archivo no es una imagen válida.'));
          img.onload = () => {
            const k = Math.min(1, max / Math.max(img.width, img.height)), c = document.createElement('canvas');
            c.width = Math.round(img.width * k); c.height = Math.round(img.height * k);
            c.getContext('2d').drawImage(img, 0, 0, c.width, c.height); ok(c.toDataURL('image/png'));
          };
          img.src = fr.result;
        };
        fr.readAsDataURL(file);
      });
    },
    async subirLogo(ev) {
      const f = ev.target.files[0]; if (!f) return;
      if (!/^image\/(png|jpeg|webp)$/.test(f.type)) { this.avisar('Use una imagen PNG, JPG o WebP.', true); ev.target.value = ''; return; }
      this.busy = true;
      let img; try { img = await this.reducirImagen(f); } catch (e) { this.avisar(e.message, true); this.busy = false; ev.target.value = ''; return; }
      try {
        const r = await this.api('/api/logo', { method: 'PUT', body: { imagen: img } });
        this.params.logo_url = r.logo_url; this.marca.logo_url = r.logo_url; this.avisar('Logo actualizado.');
      } catch { }
      this.busy = false; ev.target.value = '';
    },
    async quitarLogo() {
      if (!confirm('¿Quitar el logo de la empresa?')) return;
      try { await this.api('/api/logo', { method: 'DELETE' }); this.params.logo_url = null; this.marca.logo_url = null; this.avisar('Logo eliminado.'); } catch { }
    },
});
