/* Composición de la interfaz: une los módulos de js/ en el componente Alpine `sigt()`.

   Cada módulo (SIGT.modulos.x) devuelve su estado y sus métodos, y puede declarar `ganchos`:
     ingreso()  → cargar sus datos al iniciar sesión          salida()   → limpiar al cerrar sesión
     entrar{}   → cargar datos al abrir una vista (por id)     listo()    → acción final tras ingresar
     ejercicio() → recargar lo que depende del ejercicio fiscal elegido en la cabecera
   El orden de la lista es el del flujo de uso: primero lo que otros necesitan. */
const ORDEN_DE_MODULOS = [
  'nucleo',        // arranque, API, avisos, navegación
  'sesion',        // ingreso, salida, perfil
  'formatos',      // presentación de números, fechas y semáforos
  'ayuda',         // botones «i»
  'parametros',    // empresa, ejercicio fiscal, logo
  'ejercicios',    // ejercicio fiscal activo (condiciona casi todo lo demás)
  'indicadores',   // fichas técnicas
  'inicio',        // pantalla de bienvenida y tareas pendientes
  'carga',         // carga de datos
  'revision',      // historial y bandeja de aprobación
  'panel',         // dashboard
  'ficha_tecnica', // ficha en pantalla
  'reportes',      // Excel
  'organizacion',  // áreas, usuarios, listas
  'importacion',   // fichas históricas
  'bitacora',      // trazabilidad
  'guia',          // recorrido de bienvenida
];

function sigt() {
  const componente = {};
  const ganchos = { ingreso: [], salida: [], listo: [], ejercicio: [], entrar: {} };
  for (const nombre of ORDEN_DE_MODULOS) {
    const modulo = SIGT.modulos[nombre]();
    const g = modulo.ganchos || {};
    delete modulo.ganchos;
    // se copian los descriptores (no los valores) para conservar los getters
    Object.defineProperties(componente, Object.getOwnPropertyDescriptors(modulo));
    for (const tipo of ['ingreso', 'salida', 'listo', 'ejercicio']) if (g[tipo]) ganchos[tipo].push(g[tipo]);
    for (const [vista, f] of Object.entries(g.entrar || {})) (ganchos.entrar[vista] ||= []).push(f);
  }
  componente.ganchos = ganchos;
  return componente;
}
