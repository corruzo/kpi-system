# Prompt de trabajo — SPE TPV, versión 2 (jerarquía, roles y permisos)

> Pegar en la sesión nueva: **«Lee `docs/PROMPT_V2.md` completo y ejecútalo fase por fase.»**
> Idioma de trabajo y de toda la interfaz: **español**. El usuario no es programador: explica en simple, sin jerga.

---

## 0. Cómo trabajar (reglas no negociables)

1. **Calidad sobre velocidad.** Lee el código existente antes de cambiarlo. Nada de parches: este es un rediseño de base.
2. **Por fases, con puntos de control.** Al terminar cada fase (sección 9): pruebas verdes, `ruff` limpio, commit en la rama de la sesión,
   y un resumen corto de lo hecho, lo probado y lo pendiente. No empieces la fase siguiente con pruebas rojas.
3. **Rama y despliegue.** Trabaja SOLO en la rama de desarrollo que te asigne la sesión. **NO subas a `master`** (Vercel despliega `master`
   a producción y este rediseño rompe el esquema): el usuario autorizará esa subida explícitamente al final. No abras pull requests salvo que lo pida.
4. **Nada de acciones destructivas en producción.** No ejecutes SQL contra Supabase de producción. Deja el procedimiento de reinicio documentado
   y como script (sección 8) para que lo ejecute el usuario.
5. **Verificación real.** Además de pytest, verifica la interfaz en un navegador (Playwright está instalado; capturas de pantalla en escritorio y
   en móvil 390 px) y revisa que no haya errores de JavaScript en consola. No digas «listo» sin haberlo probado.
6. **Honestidad.** Si algo no se pudo probar o queda a medias, dilo explícitamente. Otro revisor (Claude, en otra sesión) auditará tu trabajo
   contra la lista de la sección 11.
7. **Decisiones abiertas** (sección 10): usa el valor por defecto indicado y déjalo claramente anotado; si es un bloqueo real, pregunta.
8. **Al final de cada commit** agrega los trailers de atribución que indique la sesión.

## 1. Contexto del proyecto (ya existe, versión 1)

Sistema web de indicadores de gestión (ISO 9001) de Tripoliven, C.A. Repositorio `/home/user/kpi-system` (GitHub `corruzo/kpi-system`).

- **Backend:** FastAPI + SQLAlchemy 2 + Alembic + Pydantic v2. **Base:** PostgreSQL (Supabase) en producción, SQLite en desarrollo y pruebas.
- **Frontend:** Alpine.js por módulos (`app/static/js/*.js`, `SIGT.modulos.*`, composición en `app/static/app.js`), vistas HTML parciales
  (`app/static/parciales/…`, ensambladas en el servidor por `app/plantilla.py`), Tailwind compilado y **versionado en el repo**
  (`npm run build:css` tras cambiar cualquier clase), Chart.js, Motion.
- **Despliegue:** Vercel (función serverless Python, `api/index.py`), rama `master`, migraciones al arrancar. No agregues `pyproject.toml`.
- **Calidad:** `make verificar` (ruff, pytest, migraciones + `alembic check`, CSS al día). CI en `.github/workflows/ci.yml`.
- **Lee primero:** `README.md`, `docs/ARQUITECTURA.md`, `docs/OPERACION.md`, `docs/MANUAL_DE_USO.txt`, `app/servicios/acceso.py`,
  `app/api/deps.py`, `app/models.py`, `tests/conftest.py`, `tests/api/test_aislamiento.py`.
- **Ya implementado y que debe conservarse** (todo con pruebas): flujo anual (período fiscal → presupuesto → carga mensual comparada),
  ejercicio fiscal con inicio en octubre, bitácora inmutable encadenada con SHA-256, bloqueo global de escrituras, límite de intentos de login en
  base de datos, cookie de sesión HttpOnly/SameSite=Strict, verificación de origen (CSRF), CSP, RLS en Supabase, `Cache-Control: no-store`
  + `Vary: Cookie` en `/api/*`, endpoint único de arranque `/api/arranque`, código de indicador automático, insignia NC-16, respaldo cifrado
  (`app/servicios/respaldo.py`, CLI `app.respaldar`), reportes Excel en blanco y negro firmados, recordatorios por Outlook (`mailto:`),
  panel de control, importación de planillas NC-16, guía de bienvenida, tests de aislamiento.
- **Vocabulario ya adoptado:** «encargado de proceso» (nunca «jefe de área»).

## 2. Objetivo de la versión 2

Pasar de un modelo plano (admin / gerente / encargado) a un **modelo jerárquico igual a como funciona físicamente la empresa**:

> Cada gerente ve toda su gerencia, cada jefe ve toda su jefatura, y quien carga datos solo ve lo que carga.
> El Desarrollador (Sistemas/TI) se encarga de lo técnico; el **Coordinador SGC** (Normalización) decide, con una lista de permisos
> predefinida, qué puede hacer cada rol. Ver baja por el árbol; **modificar solo lo asignado personalmente**.

## 3. Cambios de nombre (obligatorios, en TODO el sistema)

1. **Nombre del sistema:** «SGC • TRIPOLIVEN» → **«SPE TPV»** (título de pestaña, login, encabezados/pies de los Excel, correos de
   recordatorio, manual, README, documentación). El significado de las siglas SPE es una decisión abierta (sección 10): hasta que el usuario lo
   confirme, usa literalmente «SPE TPV» sin expandir. El dominio de Vercel no se toca.
2. **«Presupuesto» → «Meta».** Aplica a interfaz, API, base de datos, Excel, manual y pruebas (tabla `metas`, rutas `/metas`,
   «Real vs Meta», «Meta del período», «Meta anual», etc.). **Choque que debes resolver:** hoy `Indicador.meta` / `Medicion.meta` es el
   *umbral verde* del semáforo. Renómbralo en todas partes (columna, esquemas, serializadores, fórmulas de Excel, textos) a
   **«Nivel óptimo»** (código: `nivel_optimo`; «Límite crítico» / `limite` se queda). Resultado esperado en la ficha:
   «Nivel óptimo (verde ≥ 90)», «Límite crítico (rojo < 80)» y, por período, «Meta de octubre: 85». Revisa el importador de Excel
   (`app/servicios/lector_excel.py`): en las planillas NC-16 la palabra «Meta» designa el umbral; mapea ese texto a `nivel_optimo`.
   Nunca deben coexistir dos conceptos distintos llamados «meta».
3. Roles: **Desarrollador**, **Coordinador SGC**; los demás los define el Coordinador. Desaparecen «Administrador SGC», «Gerente / Auditor SGC»
   y «Encargado de proceso» como roles fijos (el último pasa a ser solo una forma de llamar a quien carga; ver sección 4).

## 4. Modelo organizacional

**Árbol:** `Empresa (raíz, implícita) → Gerencia → Departamento → Jefatura`. Implementar como tabla única de nodos
(`unidades`: `id`, `nombre`, `nivel` ∈ {gerencia, departamento, jefatura}, `padre_id`, `ruta` materializada tipo `/1/4/9/`) para poder
consultar subárboles con un prefijo (funciona en PostgreSQL y SQLite). Validar: el nivel debe corresponder al del padre (gerencia
bajo la raíz, departamento bajo gerencia, jefatura bajo departamento); sin ciclos; nombres únicos entre hermanos; no se puede borrar un
nodo con hijos, usuarios o indicadores (mensaje claro); mover un nodo reajusta `ruta` de todo su subárbol dentro de una transacción.

**Posición del usuario (ámbito):** un usuario tiene **cero o más** nodos de ámbito (`usuario_unidades`). Un jefe puede tener dos o más
jefaturas. Ámbito = ese nodo **y todo lo que cuelga de él**. Sin ámbito, el usuario solo ve lo que le asignaron (caso del analista).
Ejemplos que deben funcionar como pruebas de aceptación:

| Usuario | Ámbito | Ve | Modifica |
|---|---|---|---|
| Gerente general (José Mora) | la raíz (todo) | **absolutamente todo** | solo sus indicadores asignados |
| Gerente de RRHH | Gerencia RRHH | RRHH + sus departamentos (RRHH, SST, Sistemas) | solo los asignados a él |
| Jefe con 2 jefaturas | esas 2 jefaturas | ambas completas | solo los asignados a él |
| Analista | ninguno | solo lo que le asignaron | solo eso |

La visibilidad **solo baja**: un jefe no ve los indicadores propios de su gerente (que cuelgan del nodo gerencia).

**Indicadores:** cada indicador pertenece a un nodo **de cualquier nivel** (los propios de un gerente cuelgan de su gerencia) y tiene:
- un **responsable** (1 usuario; el «dueño»; es quien lo modifica), y
- **cargadores** (1..n usuarios que cargan el dato). Por defecto el responsable es también cargador.
Casos a cubrir: solo el jefe carga; solo el gerente carga; un analista carga y el jefe es responsable; varios analistas cargan el mismo indicador.

**Visibilidad de un indicador para un usuario** = (su nodo está dentro de algún ámbito del usuario) **o** (es responsable) **o** (es cargador)
**o** (rol con alcance global: Desarrollador / Coordinador SGC / Gerente general por estar en la raíz).

## 5. Roles y permisos

**Roles fijos del sistema** (en tabla `roles`, marcados `de_sistema`):
- **Desarrollador:** todo, incluido lo técnico. **Inmutable**: nadie puede editar el rol, ni quitarle permisos, ni cambiarle el rol a un
  Desarrollador salvo otro Desarrollador mediante un procedimiento explícito; el sistema impide quedarse sin ningún Desarrollador activo.
  Nadie lo modifica desde la interfaz funcional (el Coordinador no lo ve ni lo toca).
- **Coordinador SGC:** todo lo funcional, **nada técnico**. Define roles y asigna permisos; asigna a cada usuario rol, posición en el árbol e
  indicadores. **No puede**: modificar a un Desarrollador, darse permisos técnicos, dar un permiso que él mismo no tiene, ni cambiar su propio
  rol/permisos (anti-escalada). Su rol no se puede dejar sin ciertos permisos mínimos (gestionar roles/usuarios-asignación).
- **Roles definidos por el Coordinador:** nombre libre (p. ej. «Gerente», «Jefe», «Analista», «Gerente general»), cada uno es un conjunto de
  permisos con nivel. Se pueden crear, renombrar, duplicar y borrar (si ningún usuario lo usa). Un usuario tiene **un** rol.
- **Usuario nuevo = sin acceso.** El Desarrollador crea la cuenta (nombre, usuario, correo, clave temporal); entra a una pantalla
  «Su cuenta está pendiente de asignación» hasta que el Coordinador le asigne rol, ámbito e indicadores. **Acceso denegado por defecto.**
- Los roles viejos (`jefe`/`gerente`/`admin`) **desaparecen**; no hay migración de usuarios (ver sección 8).

**Catálogo de permisos** (fuente única en código, p. ej. `app/permisos.py`; cada entrada: `codigo`, `grupo`, `etiqueta`, `descripcion`,
`niveles_permitidos` ⊆ {ver, modificar}, `alcance` fijo, `tecnico: bool`). El Coordinador **solo elige el nivel por permiso**
(Ninguno / Ver / Ver y modificar, o Ninguno / Sí cuando solo tenga sentido una acción); **el alcance no es editable** y se aplica siempre
sobre los datos según la sección 4. Los permisos `tecnico` solo existen para el Desarrollador y **no aparecen** en la pantalla del Coordinador.
Tabla `rol_permisos(rol_id, permiso, nivel)`. «Modificar» incluye «Ver».

| Grupo | Permiso (código) | Alcance |
|---|---|---|
| Indicadores | `indicadores.ver` · `indicadores.crear` · `indicadores.editar` · `indicadores.archivar` · `indicadores.eliminar` · `indicadores.asignar` · `formulas.probar` | ver: ámbito+asignados · crear/asignar: a sí mismo o a personas **debajo** de él · editar/archivar/eliminar: solo los que él es responsable |
| Cargas | `cargas.ver` · `cargas.cargar` · `cargas.reabrir` · `cargas.notas` | cargar: solo donde es cargador · ver: ámbito+asignados |
| Aprobación | `cargas.aprobar` | ver sección 6 |
| Metas | `metas.ver` · `metas.cargar` · `metas.copiar` | cargar/copiar: indicadores propios y de quienes están debajo |
| Ejercicios | `ejercicios.ver` · `ejercicios.crear` · `ejercicios.cerrar` · `ejercicios.reabrir` | global |
| Análisis | `panel.ver` · `reportes.general` · `reportes.fichas` · `reportes.verificar` | ámbito+asignados |
| Recordatorios | `recordatorios.enviar` | solo personas de su ámbito |
| Estructura | `estructura.ver` · `estructura.gestionar` (árbol) · `catalogos.gestionar` · `parametros.gestionar` (empresa, logo) · `importacion.usar` | global |
| Personas | `usuarios.ver` · `usuarios.asignar` (rol, ámbito, indicadores) · `roles.gestionar` | Coordinador / Desarrollador |
| **Técnico (solo Desarrollador)** | `bitacora.ver` · `bitacora.exportar` · `usuarios.cuentas` (crear/inhabilitar/eliminar cuenta, restablecer clave) · `soporte.sesiones` · `soporte.desbloquear` · `respaldo.exportar` · `respaldo.restaurar` · `sistema.reiniciar` · `sistema.puesta_en_marcha` | global |
| Cuenta propia (todos, no editable) | cambiar contraseña, guía de bienvenida | propia |

Si al implementar encuentras una función del sistema que no está en esta tabla, **agrégala al catálogo y avísalo** (la lista debe cubrir
literalmente TODAS las funciones/rutas de la API).

**Motor de permisos** (módulo único, p. ej. `app/servicios/acceso.py` reescrito + `app/permisos.py`): funciones
`puede(usuario, permiso, nivel)`, `ambito(usuario)`, `indicadores_visibles(q, usuario)` (reemplaza `restringir`), `exigir_*`. **Ninguna ruta ni
servicio decide permisos por su cuenta.** Dependencia FastAPI `requiere_permiso("codigo", nivel)`. Lo no visible responde **404**; lo
visible pero sin permiso para la acción, **403**. Carga de permisos del usuario una vez por petición (no una consulta por chequeo).

## 6. Flujo del sistema (versión 2)

1. **Instalación/arranque:** el primer **Desarrollador** se crea con `SIGT_ADMIN_USER` / `SIGT_ADMIN_PASSWORD` (se conservan los nombres de las
   variables). Se siembran los roles de sistema y el catálogo de permisos.
2. **Cuentas:** Desarrollador crea usuarios (incluidos los Coordinadores). Sin rol = sin acceso.
3. **Estructura y personas (Coordinador SGC):** arma gerencias → departamentos → jefaturas; define roles y permisos; asigna a cada persona rol,
   ámbito (uno o varios nodos) e indicadores. Cada cambio de rol/permiso/ámbito/asignación queda en bitácora.
4. **Indicadores:** quien tenga `indicadores.crear` los crea (código automático por prefijo del nodo) y los asigna **solo a sí mismo o a
   personas debajo de él** (el Coordinador/Desarrollador sin restricción). Se define nodo, responsable y cargadores.
5. **Ejercicio y metas:** crear ejercicio (octubre–septiembre configurable); quien tenga `metas.cargar` ingresa la meta por período o anual
   repartida (mismo alcance que crear: propios y de quienes están debajo; el Coordinador siempre). Sin meta del período no se carga el dato real.
6. **Carga mensual:** el cargador ve solo lo que carga, digita, el sistema calcula semáforo y compara contra la meta del período.
7. **Aprobación jerárquica:** el **revisor es el superior directo** en el árbol; el **Coordinador SGC es respaldo y puede aprobar siempre**.
   Regla exacta: aprobadores elegibles = usuarios con `cargas.aprobar` cuyo ámbito cubre el nodo del indicador, tomando **el nivel más cercano
   hacia arriba que tenga al menos un aprobador elegible distinto del autor**; si en ese nivel hay varios (p. ej. dos jefes en la misma jefatura),
   cualquiera puede aprobar. Se suman siempre los Coordinadores. **Nadie aprueba una carga propia** (segregación de funciones, ya implementada:
   conservarla). Si el autor es el gerente general, aprueba el Coordinador. Aprobar/devolver/reabrir quedan en bitácora.
8. **Análisis, reportes y recordatorios:** todo filtrado por ámbito. El panel y los Excel solo incluyen lo visible para quien los pide
   (verificar con pruebas). Los recordatorios por Outlook solo alcanzan a personas del ámbito de quien envía.
9. **Cierre de año:** igual que hoy (verificación previa, cierre con foto, reapertura con motivo), con permisos `ejercicios.*`.
10. **Gerente general:** rol con ámbito en la raíz y permisos de **solo ver** sobre todo lo funcional (incluidas metas y reportes de todas las
    gerencias) más modificar/cargar sobre sus indicadores asignados; no ve bitácora ni soporte (técnico). Debe poder construirse **solo con la
    pantalla de roles**, sin código especial.

## 7. Interfaz (pantallas nuevas o reformadas)

Mantén el diseño, las animaciones ligeras y la responsividad actuales (nada de `backdrop-filter`; botones grandes; móvil 390 px sin scroll
horizontal). Todo en español. Menús y botones se muestran **solo si el usuario tiene el permiso** (el servidor es quien manda, la interfaz solo
refleja). Lo que no debe aparecer para un rol, no aparece (no solo deshabilitado).

- **Estructura de la empresa** (árbol): crear/renombrar/mover/eliminar gerencias, departamentos y jefaturas; ver cuántas personas e indicadores tiene cada nodo.
- **Roles y permisos** (Coordinador): lista de roles; editor con la matriz de permisos agrupada por módulo (**casillas/selector Ninguno · Ver ·
  Ver y modificar**), buscador, descripción de cada permiso, «duplicar rol», contador de usuarios por rol; avisos de lo que el rol puede hacer
  (resumen en lenguaje natural). Nunca muestra permisos técnicos.
- **Personas** (Coordinador): asignar rol, ámbito (uno o varios nodos, con selector de árbol) e indicadores; vista de «qué ve esta persona»
  (previsualización del alcance) para verificar antes de guardar. Desarrollador: además crea/inhabilita cuentas y soporte técnico.
- **Indicador:** campos nodo, responsable y cargadores (con la restricción «a sí mismo o a personas debajo de él»); «Nivel óptimo» y «Límite crítico».
- **Metas** (antes presupuesto) y **Bandeja** (aprobación según la regla del flujo).
- **Cuenta pendiente de asignación** (usuario sin rol).
- Actualiza el **inicio** y el **menú** por permisos (no por rol fijo), y `/api/arranque` para que entregue solo lo permitido.

## 8. Base de datos: reinicio limpio

Los datos actuales son de prueba; **se elimina todo y se rehace el esquema limpio y obligatorio** (claves foráneas, `CHECK`, índices en toda FK,
únicos, `NOT NULL` donde corresponda, RLS en Supabase y revocación a `anon`/`authenticated` como hoy: `scripts/supabase_hardening.sql`).

- Reemplaza la cadena de migraciones 0001–0008 por **una migración base nueva** del esquema v2 (más una de endurecimiento para PostgreSQL),
  manteniendo `alembic check` limpio y la prueba de migración desde cero.
- Nombres limpios: `metas` (antes `presupuestos`), `nivel_optimo`, `unidades`, `usuario_unidades`, `roles`, `rol_permisos`,
  `indicador_cargadores`, etc. La bitácora conserva su inmutabilidad (trigger en PostgreSQL) y encadenamiento.
- Entrega `scripts/reset_produccion_v2.sql` (borra el esquema `public` y lo recrea vacío, incluida `alembic_version`) y la sección en
  `docs/OPERACION.md` con el paso a paso para producción (respaldo previo con `app.respaldar`, ejecutar el script, redesplegar, crear el primer
  Desarrollador con las variables de entorno). **No lo ejecutes.**
- El **respaldo cifrado** (`respaldo.py`) debe seguir funcionando con las tablas nuevas, con pruebas de ida y vuelta.
- Se eliminan datos de ejemplo y roles viejos; los scripts/pruebas se actualizan al nuevo esquema.

## 9. Fases (en este orden; punto de control al final de cada una)

1. **Esquema + catálogo + motor de permisos** (sin interfaz): modelos, migración base, `permisos.py`, `acceso.py`, siembra de roles de sistema,
   dependencia `requiere_permiso`, pruebas unitarias del cruce rol × árbol × asignación (incluye todos los ejemplos de la sección 4).
2. **Renombres:** «SPE TPV», «Meta», «Nivel óptimo» en backend, Excel, importador y textos.
3. **Estructura (árbol) y Personas/Roles:** API + pantallas (secciones 5 y 7), bitácora de cambios, anti-escalada.
4. **Reconversión de cada función existente** al motor (indicadores, cargas, metas, ejercicios, reportes, panel, recordatorios, importación,
   soporte, respaldo, bitácora): ninguna ruta sin `requiere_permiso`. Test de barrido: **toda ruta `/api/*` × cada rol de prueba**.
5. **Aprobación jerárquica** (sección 6, punto 7) con pruebas de todos los casos (superior directo, varios aprobadores, escalamiento, coordinador
   de respaldo, autor = gerente general, nadie aprueba lo propio).
6. **Reportes, panel, recordatorios y `/api/arranque` por ámbito.**
7. **Interfaz final y pulido** (menús por permiso, cuenta pendiente, móvil), **documentación** (manual, README, ARQUITECTURA, OPERACION,
   catálogo de permisos en `docs/PERMISOS.md` generado/validado contra el código por una prueba), **CI** actualizado.
8. **Verificación final:** suite completa, `make verificar`, navegador (capturas en escritorio y móvil de cada pantalla nueva y de cada rol de
   ejemplo), medición de rendimiento (no debe empeorar el arranque: sigue siendo **una** petición de arranque).

## 10. Decisiones abiertas (valores por defecto)

| Tema | Por defecto | Qué hacer |
|---|---|---|
| Significado de «SPE» | no expandir; usar «SPE TPV» | **Preguntar al usuario** antes de la fase 7 |
| Nombre del umbral del semáforo | «Nivel óptimo» | proponer; si el usuario cambia, es solo texto/constante |
| Gerente general y lo técnico | no ve bitácora ni soporte | es solo configuración de su rol |
| Quién crea/inhabilita cuentas | solo Desarrollador (`usuarios.cuentas`) | el Coordinador solo asigna rol/ámbito/indicadores |
| Inhabilitar un responsable | bloqueado hasta reasignar sus indicadores (como hoy) | conservar regla y mensaje |
| Alcance de «ver» para el Coordinador | global | igual que Desarrollador para datos funcionales |

## 11. Criterios de aceptación (el revisor los comprobará uno por uno)

**Seguridad y permisos**
- [ ] Ninguna ruta de la API queda sin permiso declarado; prueba de barrido con una matriz ruta × rol; lo no visible = 404, sin permiso = 403.
- [ ] Un analista sin ámbito ve **solo** sus indicadores en listados, cargas, reportes Excel, panel, recordatorios, `/api/arranque` y caché.
- [ ] Un gerente ve todo su subárbol pero **no puede modificar** lo que no se le asignó (prueba con edición, carga, meta y archivado → 403).
- [ ] El gerente general ve absolutamente todo y modifica solo lo suyo; no accede a bitácora ni soporte.
- [ ] La visibilidad no sube (jefe no ve indicadores propios de su gerente).
- [ ] El Coordinador no puede: tocar a un Desarrollador, dar permisos técnicos, dar permisos que no posee, cambiarse su rol. Probado.
- [ ] Imposible dejar el sistema sin Desarrollador activo; el rol Desarrollador no se puede editar ni vaciar. Probado.
- [ ] Crear indicadores/metas fuera de «yo y los de debajo» → rechazado. Probado.
- [ ] Usuario sin rol: sin acceso a nada salvo su cuenta/contraseña/cerrar sesión.
- [ ] Cambios de rol/permiso/ámbito/asignación auditados en la bitácora; un cambio de permisos surte efecto en la siguiente petición.
- [ ] Se conservan TODAS las protecciones de la v1 listadas en la sección 1 (pruebas existentes adaptadas, no borradas).

**Funcional**
- [ ] Árbol de tres niveles con validaciones (nivel/padre, ciclos, borrado, mover subárbol).
- [ ] Un jefe con dos jefaturas ve ambas; un indicador con varios cargadores funciona; todos los casos de carga de la sección 4.
- [ ] Aprobación jerárquica según la regla exacta; Coordinador como respaldo; nadie aprueba lo propio.
- [ ] Pantalla de roles: matriz con TODAS las funciones del catálogo (y solo ellas), sin permisos técnicos; el catálogo cubre todas las rutas
      (prueba que lo compruebe).
- [ ] «SPE TPV» en todas partes; ya no aparece «SGC • TRIPOLIVEN», «presupuesto», «jefe de área» ni «Administrador SGC» en interfaz, Excel ni docs
      (buscar con grep y adjuntar el resultado vacío). Ningún concepto duplicado llamado «meta».
- [ ] Importador de planillas NC-16 sigue funcionando con el nuevo vocabulario (prueba existente adaptada).
- [ ] Respaldo/restauración con el esquema nuevo (ida y vuelta, cadena de bitácora verificada).

**Ingeniería**
- [ ] `ruff` limpio, `alembic upgrade head` desde cero + `alembic check` sin diferencias, CSS compilado al día, suite completa verde
      (sin pruebas omitidas ni borradas para «ponerlas en verde»).
- [ ] Sin consultas N+1 en las rutas calientes (`/api/arranque`, listados); el arranque sigue siendo una petición.
- [ ] Documentación actualizada y coherente; `docs/PERMISOS.md` validado contra el código.
- [ ] Capturas de cada pantalla nueva (escritorio y móvil) y cero errores de consola.

## 12. Entregables finales
Código en la rama de la sesión (sin subir a `master`), `docs/PERMISOS.md`, `scripts/reset_produccion_v2.sql`, documentación actualizada y un informe
final con: qué se hizo por fase, qué se probó y cómo, decisiones tomadas en las «abiertas», cualquier desviación de este prompt y lo que quedó pendiente.
