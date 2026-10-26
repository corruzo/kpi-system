/* Bitácora del sistema (solo administrador): consulta, filtros y verificación de integridad. */
SIGT.modulos.bitacora = () => ({
    bitacora: [], bitAccion: '', bitUsuario: '', bitMas: false, ACCIONES,

    // Ganchos: el núcleo los invoca al ingresar, al entrar a una vista y al salir.
    ganchos: {
      entrar: { bitacora() { return this.cargarBitacora(); } },
    },

    async cargarBitacora(reset = true) {
      const q = new URLSearchParams({ limite: 100, desde: reset ? 0 : this.bitacora.length });
      if (this.bitAccion) q.set('accion', this.bitAccion); if (this.bitUsuario.trim()) q.set('usuario', this.bitUsuario.trim());
      const r = await this.api('/api/bitacora?' + q);
      this.bitacora = reset ? r : [...this.bitacora, ...r]; this.bitMas = r.length === 100;
    },
    async verificarBitacora() {
      const r = await this.api('/api/bitacora/verificar');
      this.avisar(r.ok ? `Integridad verificada: ${r.total} registros sin alteraciones.` : `¡Alteración detectada en el registro #${r.primer_error_id}!`, !r.ok);
    },
    resumenBit(b) {
      const d = b.detalle || {}, c = b.codigo ? b.codigo + ' · ' : '';
      switch (b.accion) {
        case 'CARGA': case 'REENVIO': return `${c}${d.periodo}: resultado ${d.resultado} (${d.semaforo}). Valores: ` + Object.entries(d.valores || {}).map(([k, v]) => `${k}=${v}`).join(', ') + (d.plan_mejora ? `. Plan: ${d.plan_mejora}` : '');
        case 'APROBACION': case 'OBSERVACION': return `${c}${d.periodo}` + (d.nota ? `: ${d.nota}` : '');
        case 'NOTA_AUDITORIA': return `${c}${d.periodo}: ${d.texto}`;
        case 'REAPERTURA': return `${c}${d.periodo}: ${d.nota}`;
        case 'REPORTE_EXPORTADO': return `Reporte Excel (${d.filas} filas) ${(d.filtros || []).join(' · ')}`;
        case 'INDICADOR_EDITADO': return `${d.codigo}: cambios en ` + Object.keys(d.cambios || {}).join(', ');
        case 'INICIO_SESION': return 'Inicio de sesión';
        case 'IMPORTACION': return `${d.codigo} ← ${d.archivo} (${d.hoja}): ${(d.periodos || []).length} períodos importados`;
        case 'PARAMETROS_EDITADOS': return 'Cambios: ' + Object.keys(d.cambios || {}).join(', ');
        case 'CATALOGO_CREADO': case 'CATALOGO_ELIMINADO': return d.valor || `${d.cantidad || ''} elementos (${d.origen || ''})`;
        case 'CATALOGO_EDITADO': return `${d.tipo}: ${(d.antes || [])[0]} → ${(d.despues || [])[0]}`;
        case 'CLAVE_CAMBIADA': return 'Cambio de contraseña';
        case 'USUARIO_CREADO': case 'USUARIO_EDITADO': return `${d.username || ''} ${d.rol || ''} ` + Object.keys(d.cambios || {}).join(', ');
        case 'AREA_CREADA': case 'AREA_ELIMINADA': return d.nombre;
        case 'AREA_EDITADA': return `${d.antes} → ${d.despues}`;
        default: return `${d.codigo || ''} ${d.nombre || ''}`;
      }
    },
});
