# Catálogo de permisos de SPE TPV

> Documento **generado** desde `app/permisos.py` y las rutas de la API (`python -m app.permisos_doc`). Una prueba automática verifica que coincida con el código: no se edita a mano.

El Coordinador SGC solo elige el **nivel** de cada permiso para un rol; el **alcance** es fijo y lo aplica siempre el motor (`app/servicios/acceso.py`). «Ver y modificar» incluye «Ver». Lo que no se puede ver responde **404**; lo que se ve pero no se puede hacer, **403**.

## Reglas del motor (no configurables)

- **Visible** = el nodo del indicador está dentro de algún ámbito de la persona, **o** es su responsable, **o** es su cargador, **o** la persona tiene alcance global (Desarrollador, Coordinador SGC o ámbito en la raíz de la empresa). La visibilidad solo baja por el árbol.
- **Modificar** una ficha (editar, archivar, eliminar): solo su responsable. **Cargar** datos: solo sus cargadores. Los roles de sistema tienen alcance total.
- **Crear / asignar indicadores y fijar metas**: a sí mismo o a personas que están **debajo** en la estructura.
- **Aprobar**: el superior más cercano hacia arriba que tenga el permiso `cargas.aprobar` y sea distinto del autor; si hay varios en ese nivel, cualquiera. El Coordinador SGC es respaldo. Nadie aprueba una carga propia.
- **Anti-escalada**: nadie edita su propio rol, nadie concede un permiso que no tiene y los permisos técnicos no se conceden a ningún rol.
- **Usuario nuevo = sin acceso** hasta que el Coordinador SGC le asigne rol, ámbito e indicadores.

## Roles de sistema

| Rol | Qué es |
|---|---|
| **Desarrollador** | Todo, incluido lo técnico. Inmutable: no se edita, no se borra, no se le quitan permisos. El sistema nunca queda sin uno activo. |
| **Coordinador SGC** | Todo lo funcional, nada técnico. Define roles y asigna personas. No toca a un Desarrollador ni cambia su propio rol. |

## Indicadores

| Permiso | Función | Niveles | Alcance | Rutas |
|---|---|---|---|---|
| `indicadores.ver` | **Ver indicadores**: Consultar la lista de indicadores y su ficha técnica. | Ninguno / Ver | Los indicadores de su ámbito (su nodo y lo que cuelga de él) y los que tiene asignados. | `GET /api/indicadores`<br>`GET /api/indicadores/{indicador_id}/ficha` |
| `indicadores.crear` | **Crear indicadores**: Crear fichas nuevas (el código lo asigna el sistema) y definir su nodo, responsable y quienes cargan. | Ninguno / Sí | A sí mismo o a personas que están debajo de él en la estructura. | `GET /api/catalogos`<br>`GET /api/indicadores/codigo-sugerido`<br>`GET /api/usuarios/opciones`<br>`POST /api/indicadores` |
| `indicadores.editar` | **Editar indicadores**: Cambiar la ficha: fórmula, variables, semáforo y textos. | Ninguno / Sí | Solo los indicadores de los que es responsable. | `GET /api/catalogos`<br>`PUT /api/indicadores/{indicador_id}` |
| `indicadores.archivar` | **Archivar y restaurar**: Archivar un indicador (conserva su historial) o restaurarlo. | Ninguno / Sí | Solo los indicadores de los que es responsable. | `POST /api/indicadores/{indicador_id}/archivar`<br>`POST /api/indicadores/{indicador_id}/restaurar` |
| `indicadores.eliminar` | **Eliminar indicadores**: Borrar definitivamente un indicador que no tiene cargas. | Ninguno / Sí | Solo los indicadores de los que es responsable. | `DELETE /api/indicadores/{indicador_id}` |
| `indicadores.asignar` | **Asignar responsable y cargadores**: Cambiar el nodo, el responsable y las personas que cargan un indicador de su ámbito o propio. | Ninguno / Sí | A sí mismo o a personas que están debajo de él en la estructura. | `GET /api/usuarios/opciones`<br>`PUT /api/indicadores/{indicador_id}/asignacion` |
| `formulas.probar` | **Validar y probar fórmulas**: Usar el validador y el probador de fórmulas de la ficha. | Ninguno / Sí | No accede a datos. | `POST /api/formula/probar`<br>`POST /api/formula/validar` |

## Cargas

| Permiso | Función | Niveles | Alcance | Rutas |
|---|---|---|---|---|
| `cargas.ver` | **Ver cargas**: Consultar el historial de cargas, sus períodos y su estado. | Ninguno / Ver | Los indicadores de su ámbito (su nodo y lo que cuelga de él) y los que tiene asignados. | `GET /api/indicadores/{indicador_id}/periodos`<br>`GET /api/mediciones`<br>`GET /api/mediciones/resumen-ejercicios` |
| `cargas.cargar` | **Cargar datos**: Digitar el dato real de cada período y corregir las cargas devueltas. | Ninguno / Sí | Solo los indicadores en los que es cargador. | `POST /api/calcular`<br>`POST /api/mediciones` |
| `cargas.reabrir` | **Reabrir cargas aprobadas**: Devolver a quien cargó una carga ya aprobada, con su motivo. | Ninguno / Sí | Las cargas que le corresponde aprobar. | `POST /api/mediciones/{medicion_id}/reabrir` |
| `cargas.notas` | **Notas de auditoría**: Agregar notas de auditoría a una carga. | Ninguno / Sí | Los indicadores de su ámbito (su nodo y lo que cuelga de él) y los que tiene asignados. | `POST /api/mediciones/{medicion_id}/notas` |

## Aprobación

| Permiso | Función | Niveles | Alcance | Rutas |
|---|---|---|---|---|
| `cargas.aprobar` | **Aprobar o devolver cargas**: Revisar las cargas enviadas: aprobarlas o devolverlas con observaciones. Nadie aprueba una carga propia. | Ninguno / Sí | Las cargas de su ámbito, como superior más cercano de quien cargó (el Coordinador SGC puede aprobar siempre). | `GET /api/bandeja`<br>`GET /api/bandeja/resumen`<br>`POST /api/mediciones/{medicion_id}/revision` |

## Metas

| Permiso | Función | Niveles | Alcance | Rutas |
|---|---|---|---|---|
| `metas.ver` | **Ver metas**: Consultar la meta de cada indicador por período. | Ninguno / Ver | Los indicadores de su ámbito (su nodo y lo que cuelga de él) y los que tiene asignados. | `GET /api/ejercicios/{anio}/metas` |
| `metas.cargar` | **Cargar metas**: Ingresar o cambiar la meta por período o anual repartida. | Ninguno / Sí | Sus indicadores y los de quienes están debajo de él. | `PUT /api/ejercicios/{anio}/metas/{indicador_id}` |
| `metas.copiar` | **Copiar metas de otro ejercicio**: Copiar las metas de otro ejercicio a los indicadores que aún no las tienen. | Ninguno / Sí | Sus indicadores y los de quienes están debajo de él. | `POST /api/ejercicios/{anio}/metas/copiar` |

## Ejercicios

| Permiso | Función | Niveles | Alcance | Rutas |
|---|---|---|---|---|
| `ejercicios.ver` | **Ver ejercicios fiscales**: Ver los ejercicios fiscales y su estado (los resultados, solo de lo visible). | Ninguno / Ver | Toda la empresa. | `GET /api/ejercicios` |
| `ejercicios.crear` | **Crear ejercicios**: Abrir un período fiscal para fijar metas y cargar datos. | Ninguno / Sí | Toda la empresa. | `POST /api/ejercicios` |
| `ejercicios.cerrar` | **Cerrar ejercicios**: Verificar y cerrar un ejercicio terminado (queda de solo lectura). | Ninguno / Sí | Toda la empresa. | `GET /api/ejercicios/{anio}/verificacion`<br>`POST /api/ejercicios/{anio}/cerrar` |
| `ejercicios.reabrir` | **Reabrir ejercicios**: Reabrir un ejercicio cerrado, con su motivo. | Ninguno / Sí | Toda la empresa. | `POST /api/ejercicios/{anio}/reabrir` |

## Análisis

| Permiso | Función | Niveles | Alcance | Rutas |
|---|---|---|---|---|
| `panel.ver` | **Panel de control**: Resultados, tendencias, mapa de calor y puntualidad. | Ninguno / Ver | Los indicadores de su ámbito (su nodo y lo que cuelga de él) y los que tiene asignados. | `GET /api/dashboard`<br>`GET /api/tablero` |
| `reportes.general` | **Reporte general en Excel**: Descargar el informe «Real vs Meta». | Ninguno / Ver | Los indicadores de su ámbito (su nodo y lo que cuelga de él) y los que tiene asignados. | `GET /api/reportes/general.xlsx` |
| `reportes.fichas` | **Fichas técnicas en Excel**: Descargar las fichas técnicas en el formato NC-16. | Ninguno / Ver | Los indicadores de su ámbito (su nodo y lo que cuelga de él) y los que tiene asignados. | `GET /api/reportes/fichas.xlsx` |
| `reportes.verificar` | **Verificar reportes**: Comprobar que un Excel emitido por el sistema no fue modificado. | Ninguno / Ver | Cualquier reporte emitido por el sistema. | `POST /api/reportes/verificar` |

## Recordatorios

| Permiso | Función | Niveles | Alcance | Rutas |
|---|---|---|---|---|
| `recordatorios.enviar` | **Recordatorios de carga**: Ver quién tiene cargas pendientes y avisarle por correo (Outlook). | Ninguno / Sí | Solo personas que cargan indicadores de su ámbito. | `GET /api/recordatorios`<br>`POST /api/recordatorios/{usuario_id}` |

## Estructura

| Permiso | Función | Niveles | Alcance | Rutas |
|---|---|---|---|---|
| `estructura.ver` | **Ver la estructura**: Ver el árbol de gerencias, departamentos y jefaturas. | Ninguno / Ver | Toda la empresa. | `GET /api/unidades` |
| `estructura.gestionar` | **Gestionar la estructura**: Crear, renombrar, mover y eliminar nodos del árbol. | Ninguno / Sí | Toda la empresa. | `DELETE /api/unidades/{unidad_id}`<br>`POST /api/unidades`<br>`POST /api/unidades/{unidad_id}/mover`<br>`PUT /api/unidades/{unidad_id}` |
| `catalogos.gestionar` | **Listas de apoyo**: Mantener las listas de la ficha: procesos, objetivos, gerencias y cargos. | Ninguno / Sí | Toda la empresa. | `DELETE /api/catalogos/{elemento_id}`<br>`GET /api/catalogos`<br>`POST /api/catalogos`<br>`PUT /api/catalogos/{elemento_id}` |
| `parametros.gestionar` | **Parámetros y logo**: Empresa, código del formato, inicio del ejercicio fiscal, protección de reportes y logo. | Ninguno / Sí | Toda la empresa. | `DELETE /api/logo`<br>`GET /api/parametros`<br>`PUT /api/logo`<br>`PUT /api/parametros` |
| `importacion.usar` | **Importar planillas NC-16**: Traer fichas históricas desde Excel (crea indicadores y cargas aprobadas). | Ninguno / Sí | Toda la empresa. | `POST /api/importar/confirmar`<br>`POST /api/importar/excel` |

## Personas

| Permiso | Función | Niveles | Alcance | Rutas |
|---|---|---|---|---|
| `usuarios.ver` | **Ver personas**: Ver las personas, su rol, su ámbito y lo que alcanzan a ver. | Ninguno / Ver | Todas las personas, salvo los Desarrolladores. | `GET /api/usuarios`<br>`GET /api/usuarios/{usuario_id}/alcance`<br>`GET /api/usuarios/{usuario_id}/indicadores` |
| `usuarios.asignar` | **Asignar rol, ámbito e indicadores**: Dar a cada persona su rol, su posición en la estructura y sus indicadores. | Ninguno / Sí | Todas las personas, salvo los Desarrolladores y uno mismo. | `GET /api/puesta-en-marcha`<br>`GET /api/roles`<br>`GET /api/usuarios/opciones`<br>`POST /api/usuarios/{usuario_id}/alcance`<br>`PUT /api/usuarios/{usuario_id}/asignacion`<br>`PUT /api/usuarios/{usuario_id}/indicadores` |
| `roles.gestionar` | **Roles y permisos**: Crear, renombrar, duplicar y borrar roles, y elegir sus permisos. | Ninguno / Sí | Todos los roles, salvo el propio y el de Desarrollador. | `DELETE /api/roles/{rol_id}`<br>`GET /api/permisos`<br>`GET /api/roles`<br>`POST /api/roles`<br>`POST /api/roles/{rol_id}/duplicar`<br>`PUT /api/roles/{rol_id}` |

## Técnico (solo Desarrollador)

| Permiso | Función | Niveles | Alcance | Rutas |
|---|---|---|---|---|
| `bitacora.ver` | **Ver la bitácora**: Consultar la bitácora inalterable y verificar su cadena. | Ninguno / Ver | Toda la empresa. | `GET /api/bitacora`<br>`GET /api/bitacora/verificar` |
| `bitacora.exportar` | **Exportar la bitácora**: Descargar la bitácora en Excel. | Ninguno / Ver | Toda la empresa. | `GET /api/reportes/bitacora.xlsx` |
| `usuarios.cuentas` | **Cuentas de usuario**: Crear, inhabilitar y eliminar cuentas, restablecer contraseñas y designar Desarrolladores. | Ninguno / Sí | Toda la empresa. | `DELETE /api/usuarios/{usuario_id}`<br>`POST /api/usuarios`<br>`POST /api/usuarios/{usuario_id}/desarrollador`<br>`PUT /api/usuarios/{usuario_id}` |
| `soporte.sesiones` | **Cerrar sesiones**: Cerrar las sesiones abiertas de una persona. | Ninguno / Sí | Toda la empresa. | `POST /api/usuarios/{usuario_id}/cerrar-sesiones` |
| `soporte.desbloquear` | **Desbloquear accesos**: Levantar el bloqueo por intentos fallidos de ingreso. | Ninguno / Sí | Toda la empresa. | `POST /api/sistema/desbloquear-accesos` |
| `respaldo.exportar` | **Exportar respaldo**: Descargar el respaldo cifrado de toda la base. | Ninguno / Sí | Toda la empresa. | `POST /api/respaldo` |
| `respaldo.restaurar` | **Restaurar respaldo**: Reemplazar todos los datos por los de un respaldo. | Ninguno / Sí | Toda la empresa. | `POST /api/respaldo/restaurar` |
| `sistema.salud` | **Salud del sistema**: Ver el estado de la base, el despliegue, el código, los accesos y las alertas del sistema. | Ninguno / Ver | Toda la empresa. | `GET /api/sistema/externos`<br>`GET /api/sistema/salud` |
| `sistema.reiniciar` | **Reinicio de fábrica**: Borrar todos los datos del sistema. | Ninguno / Sí | Toda la empresa. | `POST /api/sistema/reiniciar` |
| `sistema.puesta_en_marcha` | **Guía de puesta en marcha**: Ver el avance de los pasos para arrancar el sistema. | Ninguno / Ver | Toda la empresa. | `GET /api/puesta-en-marcha` |

## Cuenta propia (todos los usuarios con sesión, no configurable)

- Ver su perfil
- Cambiar su contraseña
- Guía de bienvenida
- Cerrar sesión

Rutas: `GET /api/me`, `POST /api/cambiar-clave`, `POST /api/tour`, `GET /api/arranque` (una cuenta sin rol solo recibe su perfil). Públicas (sin sesión): `POST /api/login`, `POST /api/logout`, `GET /api/publico`, `GET /api/logo`.

## Permisos mínimos del Coordinador SGC

Su rol nunca puede quedar sin: `roles.gestionar`, `usuarios.asignar`, `usuarios.ver`, `estructura.ver`, `cargas.aprobar`, `cargas.ver`, `indicadores.ver`, `ejercicios.ver`.
