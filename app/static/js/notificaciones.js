/* Notificaciones: la campana de la cabecera. Avisos guardados (carga aprobada, devuelta con su motivo, reabierta) y avisos
   calculados de cierre de período cercano con cargas pendientes (ver servicios/notificaciones.py). */
SIGT.modulos.notificaciones = () => ({
    notif: { abierto: false, no_leidas: 0, items: [], avisos: [], dias_aviso: 5 },
    _tn: null,

    ganchos: {
      ingreso() { clearInterval(this._tn); this._tn = setInterval(() => { if (!document.hidden && this.user) this.refrescarNotif(); }, 90000); },
      salida() { clearInterval(this._tn); this.notif = { abierto: false, no_leidas: 0, items: [], avisos: [], dias_aviso: 5 }; },
    },

    get notifTotal() { return this.notif.no_leidas + this.notif.avisos.length; },
    async refrescarNotif() { try { Object.assign(this.notif, await this.api('/api/notificaciones', {}, true)); } catch { } },
    async marcarLeidas(ids = null) {
      try {
        const r = await this.api('/api/notificaciones/leer', { method: 'POST', body: { ids } }, true);
        this.notif.no_leidas = r.no_leidas;
        this.notif.items.forEach(n => { if (!ids || ids.includes(n.id)) n.leida = true; });
      } catch { }
    },
    // Lleva a la carga del indicador (y período) a los que se refiere el aviso; quien no carga va al historial de cargas
    async irAAviso(indicadorId, periodo = null) {
      this.notif.abierto = false;
      if (this.puede('cargas.cargar') && this.indicadores.some(i => i.id === indicadorId)) {
        await this.go('carga');
        this.f.indicador_id = indicadorId; await this.cambiarIndicador();
        if (periodo) { this.f.periodo = periodo; await this.cambiarPeriodo(); }
      } else if (this.puede('cargas.ver')) { await this.go('historial'); }
    },
    async abrirNotif(n) { if (!n.leida) await this.marcarLeidas([n.id]); await this.irAAviso(n.indicador_id, n.periodo); },
    tipoNotifColor: t => ({ aprobada: 'bg-green-600', devuelta: 'bg-amber-500', reabierta: 'bg-red-600' }[t] || 'bg-slate-400'),
});
