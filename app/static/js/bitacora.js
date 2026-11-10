/* Bitácora del sistema (permiso técnico bitacora.ver): consulta, filtros y verificación de integridad. */
SIGT.modulos.bitacora = () => ({
    bitacora: [], bitAccion: '', bitUsuario: '', ACCIONES,

    // Ganchos: el núcleo los invoca al ingresar, al entrar a una vista y al salir.
    ganchos: {
      entrar: { bitacora() { return this.cargarBitacora(); } },
    },

    async cargarBitacora(pagina = 1) {
      const q = new URLSearchParams();
      if (this.bitAccion) q.set('accion', this.bitAccion); if (this.bitUsuario.trim()) q.set('usuario', this.bitUsuario.trim());
      this.bitacora = await this.pedirPagina('bitacora', '/api/bitacora?' + q, pagina);
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
        case 'USUARIO_ELIMINADO': return `${d.username || ''} (${d.nombre || ''}) eliminado`;
        case 'SESIONES_CERRADAS': return `Sesiones de ${d.username || ''} cerradas por soporte`;
        case 'ACCESOS_DESBLOQUEADOS': return 'Bloqueo por intentos fallidos levantado';
        case 'IMPORTACION': return `${d.codigo} ← ${d.archivo} (${d.hoja}): ${(d.periodos || []).length} períodos importados`;
        case 'PARAMETROS_EDITADOS': return 'Cambios: ' + Object.keys(d.cambios || {}).join(', ');
        case 'CATALOGO_CREADO': case 'CATALOGO_ELIMINADO': return d.valor || `${d.cantidad || ''} elementos (${d.origen || ''})`;
        case 'CATALOGO_EDITADO': return `${d.tipo}: ${(d.antes || [])[0]} → ${(d.despues || [])[0]}`;
        case 'CLAVE_CAMBIADA': return 'Cambio de contraseña';
        case 'USUARIO_CREADO': case 'USUARIO_EDITADO': return `${d.username || ''} ${d.rol || ''} ` + Object.keys(d.cambios || {}).join(', ');
        case 'UNIDAD_CREADA': case 'UNIDAD_ELIMINADA': return `${d.nombre} (${d.nivel})`;
        case 'UNIDAD_EDITADA': return `${d.antes} → ${d.despues}`;
        case 'UNIDAD_MOVIDA': return `${d.nombre}: cambió de lugar en la estructura`;
        case 'ROL_CREADO': case 'ROL_ELIMINADO': return d.nombre;
        case 'ROL_EDITADO': return `${d.nombre}: cambios en ` + Object.keys(d.cambios || {}).join(', ') + (d.cambios?.permisos ? ` (${Object.keys(d.cambios.permisos).join(', ')})` : '');
        case 'USUARIO_ASIGNADO': return `${d.username}: ` + Object.entries(d.cambios || {}).map(([k, v]) => `${k}: ${JSON.stringify(v[0])} → ${JSON.stringify(v[1])}`).join('; ');
        case 'INDICADOR_ASIGNADO': return `${d.codigo}: ` + Object.keys(d.cambios || {}).join(', ');
        case 'INDICADORES_ASIGNADOS': return `${d.username}: ` + Object.entries(d).filter(([k]) => k !== 'username').map(([k, v]) => `${k.replace(/_/g, ' ')} ${v.join(', ')}`).join('; ');
        case 'META_GUARDADA': return `${d.ejercicio}: ` + Object.keys(d.cambios || {}).length + ' período(s)';
        case 'DESARROLLADOR_DESIGNADO': case 'DESARROLLADOR_RETIRADO': return d.username;
        default: return `${d.codigo || ''} ${d.nombre || ''}`;
      }
    },
});
