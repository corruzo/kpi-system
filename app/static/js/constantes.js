/* Constantes y utilidades compartidas por todos los módulos de la interfaz. */
window.SIGT = { modulos: {} };   // cada archivo de js/ registra aquí su módulo; app.js los compone

const SEM = { verde: '#16a34a', amarillo: '#f59e0b', rojo: '#dc2626', sin_datos: '#a6bbd1' };
const NAVY = '#0b3558', BRAND = '#006bff';
const ACCIONES = ['RECORDATORIO', 'PARAMETROS_EDITADOS', 'CATALOGO_CREADO', 'CATALOGO_EDITADO', 'CATALOGO_ELIMINADO', 'IMPORTACION', 'CARGA', 'REENVIO', 'APROBACION', 'OBSERVACION', 'NOTA_AUDITORIA', 'INDICADOR_CREADO', 'INDICADOR_EDITADO', 'INDICADOR_ASIGNADO', 'INDICADORES_ASIGNADOS', 'INDICADOR_ARCHIVADO', 'INDICADOR_RESTAURADO', 'INDICADOR_ELIMINADO', 'UNIDAD_CREADA', 'UNIDAD_EDITADA', 'UNIDAD_MOVIDA', 'UNIDAD_ELIMINADA', 'ROL_CREADO', 'ROL_EDITADO', 'ROL_ELIMINADO', 'USUARIO_CREADO', 'USUARIO_EDITADO', 'USUARIO_ASIGNADO', 'USUARIO_ELIMINADO', 'DESARROLLADOR_DESIGNADO', 'DESARROLLADOR_RETIRADO', 'CLAVE_CAMBIADA', 'REAPERTURA', 'REPORTE_EXPORTADO', 'INICIO_SESION', 'EJERCICIO_CREADO', 'META_GUARDADA', 'SESIONES_CERRADAS', 'ACCESOS_DESBLOQUEADOS', 'LOGO_ACTUALIZADO', 'LOGO_ELIMINADO', 'EJERCICIO_CERRADO', 'EJERCICIO_REABIERTO', 'RESPALDO_CREADO', 'RESPALDO_RESTAURADO'];
const ICONOS = {
  recordatorios: 'M3 8l9 6 9-6M5 5h14a2 2 0 012 2v10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2z',
  inicio: 'M3 12l9-9 9 9M5 10v10a1 1 0 001 1h3v-6h6v6h3a1 1 0 001-1V10',
  carga: 'M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931z',
  historial: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
  bandeja: 'M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-4l-1 2H9l-1-2H4',
  panel: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z',
  fichas: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4',
  org: 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z',
  importar: 'M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M17 8l-5-5m0 0L7 8m5-5v12',
  ficha: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
  ejercicios: 'M8 7V3m8 4V3M5 11h14M6 5h12a1 1 0 011 1v13a1 1 0 01-1 1H6a1 1 0 01-1-1V6a1 1 0 011-1z',
  meta: 'M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
  reportes: 'M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5m0 0l5-5m-5 5V4',
  estructura: 'M3 5h6v4H3zM15 3h6v4h-6zM15 11h6v4h-6zM15 19h6v2h-6zM9 7h3m0 0V5m0 2v6m0 0h3m-3 0v6h3',
  personas: 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z',
  roles: 'M12 3l8 3v5c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V6l8-3zm-1 9l-2-2m2 2l4-4',
  config: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065zM15 12a3 3 0 11-6 0 3 3 0 016 0z',
  bitacora: 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z',
};

// Lista paginada → método que carga una página (lo usa irPagina en nucleo.js)
const CARGADORES = { bitacora: 'cargarBitacora', historial: 'cargarHistorial', bandeja: 'cargarBandeja', fichas: 'cargarFichas',
  usuarios: 'cargarUsuarios', recordatorios: 'cargarRecordatorios' };
const VISTA_INICIAL = 'inicio';       // primera vista tras ingresar
// Secciones del menú: [id, permisos (basta uno; null = siempre), etiqueta, etiqueta corta, grupo]. El menú se arma por PERMISOS,
// nunca por un rol fijo: lo que la persona no puede usar no aparece. El servidor es quien decide; esto solo lo refleja.
const SECCIONES = [
  ['inicio', null, 'Inicio', 'Inicio', ''],
  ['estructura', ['estructura.ver'], 'Estructura de la empresa', 'Estructura', 'Configurar'],
  ['roles', ['roles.gestionar'], 'Roles y permisos', 'Roles', 'Configurar'],
  ['personas', ['usuarios.ver'], 'Personas', 'Personas', 'Configurar'],
  ['fichas', ['indicadores.ver'], 'Indicadores', 'Fichas', 'Configurar'],
  ['meta', ['metas.ver'], 'Período y metas', 'Metas', 'Configurar'],
  ['carga', ['cargas.cargar'], 'Cargar datos', 'Cargar', 'Operar'],
  ['bandeja', ['cargas.aprobar'], 'Bandeja de aprobación', 'Bandeja', 'Operar'],
  ['recordatorios', ['recordatorios.enviar'], 'Recordatorios de carga', 'Avisos', 'Operar'],
  ['historial', ['cargas.ver'], 'Cargas', 'Cargas', 'Operar'],
  ['panel', ['panel.ver'], 'Panel de control', 'Panel', 'Analizar'],
  ['reportes', ['reportes.general', 'reportes.fichas', 'reportes.verificar'], 'Reportes', 'Reportes', 'Analizar'],
  ['ejercicios', ['ejercicios.crear', 'ejercicios.cerrar', 'ejercicios.reabrir'], 'Cierre de años', 'Cierre', 'Control'],
  ['importar', ['importacion.usar'], 'Importar', 'Importar', 'Control'],
  ['config', ['parametros.gestionar', 'catalogos.gestionar', 'respaldo.exportar', 'respaldo.restaurar', 'sistema.reiniciar', 'soporte.desbloquear'], 'Configuración', 'Ajustes', 'Control'],
  ['bitacora', ['bitacora.ver'], 'Bitácora', 'Bitácora', 'Control'],
];
const SEGUIMIENTO = ['bandeja', 'recordatorios', 'historial'];
const NIVEL_ETIQUETA = { gerencia: 'Gerencia', departamento: 'Departamento', jefatura: 'Jefatura' };
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const nf = (v, d) => Number(v).toLocaleString('es-VE', { minimumFractionDigits: 0, maximumFractionDigits: d });
