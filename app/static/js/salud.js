/* Salud del sistema (solo Desarrollador, permiso técnico sistema.salud): una sola petición trae infraestructura, código,
   actividad y alertas con su recomendación; el estado público de Supabase y Vercel se pide aparte (depende de terceros). */
SIGT.modulos.salud = () => ({
    salud: null, externos: null, saludCargando: false,

    ganchos: {
      entrar: { inicio() { return this.cargarSalud(); } },
      salida() { this.salud = null; this.externos = null; },
    },

    async cargarSalud() {
      if (!this.puede('sistema.salud') || this.saludCargando) return;
      this.saludCargando = true;
      try { this.salud = await this.api('/api/sistema/salud', {}, true); } catch { this.salud = null; }
      this.saludCargando = false;
      this.api('/api/sistema/externos', {}, true).then(e => { this.externos = e; }, () => { this.externos = null; });   // sin bloquear la pantalla
    },
    // La fecha del servidor viene en UTC sin zona: «hace 5 min», «hace 2 h», «hace 3 d»
    hace(f) {
      if (!f) return 'nunca';
      const s = Math.max(0, (Date.now() - new Date(f.endsWith('Z') ? f : f + 'Z')) / 1000);
      return s < 90 ? 'ahora mismo' : s < 5400 ? 'hace ' + Math.round(s / 60) + ' min' : s < 129600 ? 'hace ' + Math.round(s / 3600) + ' h' : 'hace ' + Math.round(s / 86400) + ' d';
    },
    estadoSalud() { return { ok: ['Todo en orden', 'border-green-300 bg-green-50 text-green-800'], aviso: ['Requiere atención', 'border-amber-300 bg-amber-50 text-amber-900'], critico: ['Hay problemas graves', 'border-red-300 bg-red-50 text-red-800'] }[this.salud?.estado || 'ok']; },
    colorNivel(n) { return { critico: 'border-red-300 bg-red-50', aviso: 'border-amber-300 bg-amber-50', info: 'border-slate-200 bg-slate-50' }[n]; },
    puntoNivel(n) { return { critico: 'bg-red-600', aviso: 'bg-amber-500', info: 'bg-sky-500' }[n]; },
    colorBarra(p) { return p >= 90 ? 'bg-red-600' : p >= 70 ? 'bg-amber-500' : 'bg-green-600'; },
    externo(k) {
      const e = this.externos?.[k]; if (!e) return ['Consultando…', 'bg-slate-300'];
      return e.indicador === 'none' ? ['Operativo', 'bg-green-600'] : !e.indicador ? ['Sin datos', 'bg-slate-400'] : [e.descripcion, e.indicador === 'minor' ? 'bg-amber-500' : 'bg-red-600'];
    },
    accionLegible(a) { return a.toLowerCase().replace(/_/g, ' '); },
});
