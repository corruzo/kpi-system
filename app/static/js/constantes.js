/* Constantes y utilidades compartidas por todos los módulos de la interfaz. */
window.SIGT = { modulos: {} };   // cada archivo de js/ registra aquí su módulo; app.js los compone

const SEM = { verde: '#16a34a', amarillo: '#f59e0b', rojo: '#dc2626', sin_datos: '#94a3b8' };
const NAVY = '#0f172a', BRAND = '#0284c7';
const ACCIONES = ['PARAMETROS_EDITADOS', 'CATALOGO_CREADO', 'CATALOGO_EDITADO', 'CATALOGO_ELIMINADO', 'IMPORTACION', 'CARGA', 'REENVIO', 'APROBACION', 'OBSERVACION', 'NOTA_AUDITORIA', 'INDICADOR_CREADO', 'INDICADOR_EDITADO', 'INDICADOR_ARCHIVADO', 'INDICADOR_ELIMINADO', 'AREA_CREADA', 'AREA_EDITADA', 'AREA_ELIMINADA', 'USUARIO_CREADO', 'USUARIO_EDITADO', 'CLAVE_CAMBIADA', 'REAPERTURA', 'REPORTE_EXPORTADO', 'INICIO_SESION'];
const ICONOS = {
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
  reportes: 'M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5m0 0l5-5m-5 5V4',
  bitacora: 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z',
};

const ROLES = { jefe: 'Jefe de Área', gerente: 'Gerente / Auditor SGC', admin: 'Administrador SGC' };
const VISTA_INICIAL = 'inicio';       // primera vista tras ingresar
const MENU_POR_ROL = {                                                           // secciones y su orden, por rol
  jefe: ['inicio', 'carga', 'historial', 'reportes'],
  gerente: ['inicio', 'panel', 'bandeja', 'historial', 'reportes', 'ejercicios'],
  admin: ['inicio', 'fichas', 'panel', 'bandeja', 'carga', 'historial', 'reportes', 'ejercicios', 'org', 'importar', 'bitacora'],
};
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const nf = (v, d) => Number(v).toLocaleString('es-VE', { minimumFractionDigits: 0, maximumFractionDigits: d });
