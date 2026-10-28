# SGC • TRIPOLIVEN — Manual de usuario

Sistema de Gestión de la Calidad para los indicadores de gestión de Tripoliven, C.A. (ISO 9001:2015).
Este manual describe **cada pantalla y cada botón**, organizado por rol. Si solo necesita su parte, vaya directo a:

| Si usted es… | Lea |
|---|---|
| **Jefe de Área** (carga los datos de su departamento) | [1](#1-conceptos-básicos), [2](#2-ingreso-y-pantalla-general), [3](#3-inicio), [4](#4-jefe-de-área) |
| **Gerente / Auditor SGC** (revisa y analiza) | [1](#1-conceptos-básicos), [2](#2-ingreso-y-pantalla-general), [3](#3-inicio), [5](#5-gerente--auditor-sgc) |
| **Administrador SGC** (configura todo) | Todo el manual, en especial [6](#6-administrador-sgc) y [7](#7-flujo-completo-de-ejemplo-área-de-producción) |

---

## 1. Conceptos básicos

### 1.1 Cómo funciona, en una frase
El administrador define **qué se mide y cuál es la meta** (ficha del indicador); cada mes el **jefe de área** digita los **datos reales**; el sistema calcula el resultado y le pone un **semáforo**; el **gerente / auditor** aprueba o devuelve la carga.

```
Administrador            Jefe de Área               Gerente / Auditor
crea la ficha  ───────►  carga el dato real  ─────► aprueba  ──► cuenta en el panel
(fórmula + meta)         (resultado + semáforo)      o devuelve ──► el jefe corrige y reenvía
```

### 1.2 El semáforo
| Color | Texto en pantalla | Significado |
|---|---|---|
| 🟢 Verde | **Cumple** | Alcanza la meta. |
| 🟡 Amarillo | **Alerta** | Entre la meta y el límite crítico. |
| 🔴 Rojo | **Crítico** | Peor que el límite crítico. |

Depende del **sentido** de la meta que define el administrador:
- *Mayor es mejor* (ej. cumplimiento): verde si resultado **≥ meta**; rojo si **< límite crítico**.
- *Menor es mejor* (ej. mermas, tiempos): verde si resultado **≤ meta**; rojo si **> límite crítico**.

En **Alerta** y **Crítico** el jefe debe escribir el **análisis** y el **plan de mejora** (obligatorio por ISO 9001, 9.1.3 y 10.2).

### 1.3 Estados de una carga
| Estado (como se ve) | Qué significa | Quién actúa |
|---|---|---|
| **En revisión** (enviado) | El jefe la envió; espera al gerente. No se puede modificar. | Gerente / Auditor |
| **Aprobado** | Revisada y aceptada. Cuenta en el panel y los reportes. | — |
| **Devuelto** (observado) | El gerente la rechazó con una observación. | El jefe corrige y **reenvía** (queda la versión 2, 3…) |

Regla de segregación de funciones: **nadie puede aprobar ni devolver una carga que realizó él mismo.**

### 1.4 Ejercicio fiscal
Todo el sistema se organiza por **ejercicio fiscal** (ej. «2026» o «2026-2027», según el mes en que comience el año de gestión, que define el administrador). Los datos de ejercicios distintos nunca se mezclan en pantalla. Un ejercicio pasa por cuatro etapas:

1. **Vigente** — se carga y se aprueba normalmente.
2. **Terminado · por cerrar** — ya pasó su último día; se completan pendientes.
3. **Cerrado** — archivado en **solo lectura** (con una foto de sus resultados). El administrador puede **reabrirlo** con un motivo.
4. **Próximo** — el siguiente, aún no empieza.

### 1.5 Frecuencias de los indicadores
Mensual, bimestral, trimestral, cuatrimestral, semestral, anual o **eventual** (cuando ocurre). La frecuencia determina los **períodos** que se ofrecen para cargar. Los períodos se escriben, por ejemplo, `2026-09` (septiembre 2026) o `2026-Q3` (tercer trimestre del ejercicio).

### 1.6 Roles y permisos
| Acción | Jefe | Gerente | Admin |
|---|:--:|:--:|:--:|
| Cargar datos de indicadores | Solo su área | — | Cualquier área |
| Aprobar / devolver cargas | — | ✔ | ✔ (no las propias) |
| Reabrir una carga aprobada · notas de auditoría | — | ✔ | ✔ |
| Ver panel de análisis | — | ✔ | ✔ |
| Ver historial de cargas | Solo su área | Todas | Todas |
| Descargar reportes Excel | Solo su área | Todas | Todas |
| Verificar autenticidad de un reporte | — | ✔ | ✔ |
| Ver los ejercicios fiscales | — | ✔ | ✔ |
| Cerrar / reabrir ejercicios | — | — | ✔ |
| Crear y editar indicadores | — | — | ✔ |
| Áreas, usuarios, parámetros, logo, listas | — | — | ✔ |
| Importar fichas desde Excel · Bitácora | — | — | ✔ |

---

## 2. Ingreso y pantalla general

### 2.1 Pantalla de ingreso
| Elemento | Qué hacer |
|---|---|
| **Usuario** | Su nombre de usuario (minúsculas, p. ej. `jefe.produccion`). Máximo 40 caracteres. |
| **Contraseña** | Su contraseña. |
| **Continuar** | Ingresa al sistema. Muestra *«Ingresando…»* mientras valida. |

- Un mensaje rojo indica *«Usuario o contraseña incorrectos.»*
- Tras **5 intentos fallidos** seguidos con el mismo usuario desde el mismo equipo, el ingreso se bloquea **15 minutos** (*«Demasiados intentos fallidos…»*). También se bloquea si un mismo equipo prueba muchos usuarios.
- La sesión dura **10 horas**. Después debe ingresar de nuevo.

La primera vez que entra, el sistema le muestra la **guía de bienvenida** (ver 2.4).

### 2.2 Cabecera (barra superior)
| Elemento | Qué hace |
|---|---|
| **Logo / nombre** | Visible en móvil y tablet (en computadora está en la barra lateral). |
| **Selector de ejercicio fiscal** (lista desplegable) | Elige qué ejercicio ver. Los cerrados llevan 🔒. Toda la pantalla se recarga con el ejercicio elegido. Si elige uno que no es el vigente aparece un aviso azul con el botón **Volver al ejercicio vigente**. |
| **Menú de usuario** (su nombre e iniciales) | Abre: **Cambiar contraseña**, **Ver guía de uso**, **Cerrar sesión**. |

**Cambiar contraseña** (ventana):
1. **Contraseña actual**.
2. **Nueva contraseña** (mínimo **10 caracteres**).
3. **Repita la nueva contraseña** (si no coincide, aparece *«Las contraseñas no coinciden.»* y el botón queda desactivado).
4. **Guardar** / **Cancelar** (o ✕).

**Cerrar sesión** termina la sesión y **la invalida en el servidor**: si alguien hubiera copiado su sesión, deja de servir. Cierra también sus sesiones abiertas en otros equipos.

### 2.3 Navegación
- **Computadora (pantalla ancha):** barra lateral izquierda con las secciones de su rol. La sección activa va resaltada en azul. Una **insignia amarilla** con número indica pendientes (por cargar o por aprobar).
- **Tableta:** barra de pestañas arriba.
- **Teléfono:** barra flotante inferior con 4 accesos y **Más** (que abre el resto de secciones).

Secciones por rol:

| Jefe de Área | Gerente / Auditor | Administrador |
|---|---|---|
| Inicio · Carga rápida · Mis cargas · Reportes | Inicio · Panel de análisis · Bandeja de aprobación · Todas las cargas · Reportes · Ejercicios fiscales | Inicio · Indicadores · Panel de análisis · Bandeja de aprobación · Cargar datos · Todas las cargas · Reportes · Ejercicios fiscales · Organización · Importar · Bitácora |

### 2.4 Botones «i» y guía de bienvenida
- Cada botón redondo **«i»** despliega una explicación en lenguaje sencillo del campo o concepto. Púlselo otra vez para ocultarla.
- La **guía de bienvenida** recorre el sistema paso a paso resaltando cada parte. Botones: **Siguiente**, **Atrás**, **Omitir guía** (o tecla *Esc*), **Finalizar**. Las flechas ← → del teclado también avanzan. Puede repetirla desde *Menú de usuario → Ver guía de uso*.

### 2.5 Avisos del ejercicio
- **Aviso azul** «Está viendo el ejercicio …, no el vigente»: **Volver al ejercicio vigente**.
- **Aviso amarillo** (gerente y administrador) «El ejercicio … ya terminó y sigue abierto»: botón **Ir a ejercicios fiscales** / **Ver ejercicios**.

---

## 3. Inicio

Pantalla de bienvenida con el saludo según la hora.

- **Qué hacer ahora**: lista de tareas pendientes, cada una con su botón:
  - *«N cargas del ejercicio esperan su aprobación»* → **Revisar** (gerente / admin).
  - *«N períodos pendientes de cargar»* → **Cargar** (jefe / admin).
  - *«Pendientes en el ejercicio … (ya terminado)»* → **Ver ese ejercicio**.
  - *«N indicadores en estado crítico»* → **Ver panel**.
  - Si no hay nada: *«No tiene tareas pendientes. ✔ Todo está al día.»*
- **Tarjetas de resumen** (gerente / admin): **Cumplimiento**, **En verde**, **En alerta**, **Críticos**.
- **Secciones**: una tarjeta por cada sección a la que usted tiene acceso, con una descripción corta. Tóquela para ir.

---

## 4. Jefe de Área

### 4.1 Carga rápida
Es la pantalla donde se registran los datos reales de cada período.

**Encabezado.** El botón **«i»** junto al título explica los 4 pasos de la carga.

**Avisos que puede ver (arriba):**
- Recuadro azul *«Además tiene N período(s) pendiente(s) en el ejercicio …»* con **Ir a ese ejercicio**.
- Recuadro amarillo **Pendientes de carga**: botones tipo `PRO-01 · Octubre 2026`. Al pulsar uno, el indicador y el período se seleccionan solos.
- Recuadro verde *«✔ Está al día con todas sus cargas.»*
- Si no tiene indicadores: *«Su área aún no tiene indicadores asignados»* (pida al administrador que cree las fichas).

**Paso 1 — elegir indicador y período**
| Campo | Detalle |
|---|---|
| **Indicador** | Lista de los indicadores activos de su área: `código · nombre`. |
| **Período** | Períodos del ejercicio elegido, hasta el mes actual (no se pueden cargar períodos futuros). Cada opción indica *(en curso)*, el estado de la carga existente o *— ejercicio cerrado*. |

**Tarjeta del indicador.** Muestra nombre, objetivo, **Meta** (por ejemplo `≥ 95% · crítico < 85%`) y **Fórmula** en lenguaje legible. El botón **«i»** despliega: **Abrir ficha técnica completa**, área, frecuencia, unidad, fuente de datos, método, constantes y el significado del semáforo.

**Estado de la carga del período** (recuadros):
- *Carga enviada, en revisión* (azul) o *Carga aprobada* (verde): los campos quedan **bloqueados**.
- *Carga devuelta por el Gerente / Auditor* (amarillo) con la **Observación** que escribió: corrija y reenvíe.
- *🔒 Este período pertenece a un ejercicio fiscal cerrado: solo lectura.*

**Paso 2 — Datos del período.** Un campo numérico por cada variable de la ficha (por ejemplo «Producción planificada (kg)» y «Producción real (kg)»).
- Debajo de cada campo puede haber un texto de ayuda.
- Los campos **(opcional)** pueden quedar vacíos (se usa un valor por defecto).
- No se aceptan negativos, salvo que la ficha lo permita.
- Al escribir, el resultado se recalcula solo.

**Paso 3 — Resultado.** Tarjeta grande con el **resultado**, el **semáforo** (Cumple / Alerta / Crítico) y la meta. Si el cálculo falla (dato faltante, división entre cero) aparece el motivo en rojo. El botón **«i»** explica el semáforo.

**Paso 4 — Análisis y plan de mejora** (solo si el resultado es Alerta o Crítico): dos cuadros obligatorios, de **mínimo 10 caracteres** cada uno:
- **Resultados del análisis**: «¿Qué causó la desviación?»
- **Correcciones / plan de mejora**: acciones, responsable y fecha compromiso.

**Botón final:**
- **Enviar carga** — la manda a revisión. Se activa solo cuando todo está completo y válido.
- **Reenviar para revisión** — aparece cuando la carga fue devuelta; crea una nueva versión.

> Una vez enviada, **no se puede modificar** hasta que el gerente la devuelva.

### 4.2 Mis cargas
Historial de todo lo que ha cargado su área en el ejercicio elegido.

**Filtros:** Indicador · Estado (*En revisión, Aprobado, Devuelto*) · Semáforo (*Cumple, Alerta, Crítico*) · Período exacto (ej. `2026-09`).
**Casilla** «Incluir otros ejercicios fiscales»: muestra todos los años, agrupados por ejercicio.

Cada carga es una tarjeta: barra de color del semáforo, código, período, nombre, resultado y estado. **Pulse la tarjeta** para abrirla y ver: los valores digitados, el análisis, el plan de mejora, quién la cargó y cuándo, la versión, las notas de auditoría y la nota de revisión. Dentro hay **Ver ficha del indicador**. **Cargar más** trae registros anteriores.

### 4.3 Reportes (Jefe)
Ver sección [8](#8-reportes). El jefe solo obtiene datos de **su área**.

---

## 5. Gerente / Auditor SGC

### 5.1 Panel de análisis
Vista de resultados del ejercicio elegido, según la **última medición** de cada indicador. Filtro superior: **Todas las áreas** o un área.

| Bloque | Qué muestra |
|---|---|
| **Estado del ejercicio** | Etiqueta del ejercicio y su estado (Vigente / Terminado / Cerrado), fechas, barra **Avance del ejercicio** (tiempo transcurrido) y **Carga al día**. A la derecha: **Por aprobar**, **Devueltas**, **Cargas**. |
| **Tarjetas** | Indicadores, Cumplimiento, En verde, En alerta, Críticos, Carga al día. |
| **Requiere atención** | Indicadores críticos, en alerta y empeorando, o con cargas pendientes. Pulse uno para abrir su ficha. |
| **Tendencia vs. meta** | Gráfico de línea del indicador elegido en la lista desplegable, con líneas de meta y límite crítico. |
| **Mapa de calor del ejercicio** | Una fila por indicador y una columna por mes, coloreada con el semáforo y con el resultado dentro. Pulse el nombre para abrir la ficha. |
| **Distribución de semáforos** | Gráfico circular de Cumple / Alerta / Crítico / Sin datos. |
| **Cumplimiento por departamento** | Barras por área; el rombo ◆ marca el cumplimiento del ejercicio anterior. |
| **Indicadores** (tabla) | Código, nombre, área, último período, resultado, tendencia (▲▼), meta y semáforo. Toque una fila para abrir la ficha. |

### 5.2 Bandeja de aprobación
Cargas **enviadas** esperando su decisión, del ejercicio elegido. Cada tarjeta muestra área, período, indicador, resultado y semáforo (y *«reenvío vN»* si fue corregida), los datos, el análisis y el plan de mejora.

| Elemento | Detalle |
|---|---|
| **Nota de auditoría / motivo de devolución** | Opcional al aprobar; **obligatoria** al devolver (mínimo 5 caracteres). |
| **Devolver con observación** (rojo) | La regresa al jefe con su nota; el jefe la ve en *Carga rápida* y la reenvía. |
| **Aprobar formalmente** (azul) | La aprueba: pasa a contar en el panel y los reportes. |

Si la carga la realizó usted, ambos botones quedan desactivados (*segregación de funciones*). Si hay cargas pendientes de otro ejercicio aparece un aviso con **Ver ese ejercicio**. Con la bandeja vacía: *«✔ No hay cargas pendientes de revisión en este ejercicio.»*

### 5.3 Todas las cargas
Igual que *Mis cargas* (4.2) pero de **todas las áreas**, con filtro adicional **Todas las áreas** y el botón **Descargar Excel** (arriba a la derecha). Al abrir una tarjeta aparecen herramientas extra:
- **Reabrir carga** (si está *Aprobada*): para corregir un error ya aprobado. Escriba el **Motivo de la reapertura** y pulse **Reabrir carga**; vuelve al jefe como *Devuelta* y queda registrado.
- **Agregar nota de auditoría**: escriba la nota y pulse **Agregar nota** (o *Enter*). Se guarda con su nombre y fecha.

### 5.4 Reportes y Ejercicios fiscales
Ver [8](#8-reportes) y [6.4](#64-ejercicios-fiscales). El gerente puede **ver** los ejercicios (panel y descargas) pero no cerrarlos ni reabrirlos.

---

## 6. Administrador SGC

El administrador tiene acceso a **todo**: además de sus secciones propias, puede cargar datos en cualquier área (*Cargar datos*, idéntica a la *Carga rápida* pero con la lista de todos los indicadores y su área), ver el panel, la bandeja y las cargas.

### 6.1 Orden recomendado de configuración inicial
La pantalla **Indicadores** muestra una tarjeta **Configuración inicial** con tres pasos (cada uno con botón **Ir →**):
1. **Crear las áreas de la empresa** (Organización).
2. **Registrar usuarios** (un jefe por área y un gerente / auditor).
3. **Crear las fichas de indicadores**.
Antes, en *Organización → Parámetros*, defina el **mes de inicio del ejercicio fiscal**.

### 6.2 Organización

#### Áreas
| Elemento | Detalle |
|---|---|
| Campo **Nueva área** + **Agregar** | Crea un área (mín. 2 caracteres, nombre único). |
| **Editar** | Carga el nombre en el campo (que pasa a *Renombrar área*); botón **Guardar**, o **✕** para cancelar. |
| **Eliminar** | Pide confirmación. No se puede eliminar un área con indicadores o usuarios asignados. |

#### Usuarios
Botón **+ Nuevo usuario** / **Editar** en cada fila. Ventana:
| Campo | Detalle |
|---|---|
| **Usuario** | 3–40 caracteres: minúsculas, números, punto, guion y guion bajo. No se puede cambiar después. |
| **Nombre completo** | Mínimo 3 caracteres. |
| **Rol** | *Jefe de Área*, *Gerente / Auditor SGC* o *Administrador SGC*. |
| **Área** | Solo para *Jefe de Área* (obligatoria). |
| **Contraseña inicial** / **Nueva contraseña (opcional)** | Mínimo **10 caracteres**. Al restablecerla se cierran las sesiones activas de ese usuario. |
| **Usuario activo** | Al desmarcarlo, el usuario no puede ingresar (su historial se conserva). Los usuarios inactivos se ven atenuados. |

Un administrador **no puede desactivarse ni quitarse el rol a sí mismo**.

#### Logo de la empresa
**Subir logo / Cambiar logo** (PNG, JPG o WebP, hasta 600 KB; se ajusta a 600 px) y **Quitar**. Aparece en el ingreso, la cabecera, la ficha técnica y los reportes Excel. El botón «i» da recomendaciones.

#### Parámetros del sistema
| Campo | Detalle |
|---|---|
| **Empresa** | Nombre en pantallas y reportes. |
| **Gerencia emisora de las fichas** | Aparece en la ficha técnica. |
| **Código del formato** | Ej. `NC-16-7`. |
| **Inicio del ejercicio fiscal** | Mes en que comienza el año de gestión (una base nueva arranca en *Octubre*). Con *Octubre*, el ejercicio 2026-2027 va de octubre 2026 a septiembre 2027. **No se puede cambiar** si hay ejercicios cerrados o cargas que no sean mensuales/eventuales. |
| **Bloquear los reportes en Excel con contraseña** | Si lo marca aparece **Contraseña de los reportes** (mínimo 6 caracteres; en blanco = conserva la actual). Los Excel quedan con hojas protegidas. La contraseña se guarda **cifrada**. |
| **Guardar parámetros** | Aplica los cambios. |

> Los Excel llevan además una hoja **Control** firmada por el sistema (ver 8.3).

#### Listas de apoyo de la ficha
Pestañas **Procesos · Objetivos · Gerencias · Cargos** (con su cantidad). Escriba el elemento y pulse **Agregar** (en *Procesos* hay además un cuadro «Objetivo del proceso», que se copia a la ficha al elegir ese proceso). **Editar** / **Quitar** por elemento. Estas listas se ofrecen como sugerencias al crear indicadores.

#### Zona de peligro — Borrar todos los datos
Botón **Borrar todos los datos…** Abre una ventana que exige:
1. Escribir exactamente **BORRAR TODO**.
2. Su **contraseña de administrador**.
3. **Borrar todo definitivamente**.

Elimina **todo** (indicadores, cargas, áreas, usuarios salvo el suyo, listas, parámetros, logo y la bitácora). **No se puede deshacer.** Descargue antes los reportes que necesite.

### 6.3 Indicadores (fichas técnicas)

#### Lista
- Botón **+ Nuevo indicador** (se desactiva si aún no hay áreas).
- Filtros: **buscar** (código, nombre o área), **Área**, **Frecuencia**, **Estado** (*Activos / Archivados / Todos*). Debajo, el contador «N de M indicadores».
- Columnas: Código, Indicador (con su fórmula), Área, Frecuencia · unidad, Meta / Límite, Cargas.
- Botones por indicador:

| Botón | Qué hace |
|---|---|
| **Ver ficha** | Abre la ficha técnica en pantalla (6.3.3). |
| **Editar** | Abre el formulario de edición. |
| **Duplicar** | Copia la ficha como nueva (*«… (copia)»*); debe asignarle un código nuevo. |
| **Archivar / Restaurar** | Un indicador archivado deja de aparecer para cargar; su historial se conserva. |
| **Eliminar** | Si no tiene cargas, lo borra; si tiene, lo **archiva** (por trazabilidad). Pide confirmación. |

#### 6.3.2 Formulario «Nuevo indicador» / «Editar indicador»
Cada campo tiene su botón **«i»**. Botón **Guía de fórmulas** arriba a la derecha. Si el indicador **ya tiene cargas** aparece un aviso: no se puede cambiar la **frecuencia** ni las **claves** de variables y constantes; sí la meta, la fórmula y los textos (queda en la bitácora y **no altera el histórico**: cada carga conserva la meta y fórmula vigentes cuando se hizo).

**1 · Identificación**
| Campo | Detalle |
|---|---|
| **Código** * | Único, ej. `PRO-01` (se guarda en mayúsculas, máx. 20). |
| **Nombre** * | Nombre completo del indicador. |
| **Objetivo** | Para qué se mide; el jefe lo ve al cargar. |
| **Sigla** | Abreviatura para la fórmula documentada (ej. `SP`). |
| **Área / departamento responsable** * | Solo los jefes de esa área (y el administrador) pueden cargarlo. |

**2 · Proceso, objetivo y responsables**
| Campo | Detalle |
|---|---|
| **Seguimiento de** | *Desempeño de proceso*, *Objetivo organizacional* o *Desempeño de proveedor externo* (cambia las etiquetas de la ficha). |
| **Proceso** / **Objetivo organizacional** | Elija de la lista o escriba. |
| **Objetivo del proceso** / **Objetivo específico** / **Bien o servicio** | Descripción que aparece bajo el proceso. |
| **Gerencia**, **Líder de proceso** | Con sugerencias de las listas de apoyo. |
| **Responsables de medición, registro y análisis** | Tres cuadros; se sugieren los usuarios del sistema. |

**3 · Medición**
| Campo | Detalle |
|---|---|
| **Unidad** * | `%`, `días`, `horas`, `TM`, `kg`, `USD`, `cantidad`… (o escriba otra; máx. 12 caracteres). |
| **Frecuencia** * | Mensual, Bimestral, Trimestral, Cuatrimestral, Semestral, Anual o Eventual. |
| **Decimales** | 0 a 6. El resultado se redondea a esta precisión **antes** de evaluar el semáforo. |
| **Sentido de la meta** * | *Mayor es mejor* o *Menor es mejor*. |

**4 · Metas y semáforo** — *aquí se fija lo presupuestado / la meta*
| Campo | Detalle |
|---|---|
| **Meta (verde ≥ / ≤)** * | Valor desde el cual el indicador **cumple**. |
| **Límite crítico (rojo < / >)** * | Frontera entre Alerta y Crítico. |
| **Tope de la zona verde / amarilla** (opcional) | Acota el otro extremo de cada franja (columnas «Mín./Máx.» de la ficha). Vacíos si no aplica. |
| Franja de vista previa | Resume: *Cumple ≥ X · Alerta intermedia · Crítico < Y*. |

La meta es **un solo valor para todo el año** (no hay una meta distinta por mes). Si necesita un presupuesto mensual variable, defínalo como **variable** (sección 5) para que el jefe lo digite cada mes y úselo en la fórmula (ej. `real / plan * 100`).

**5 · Variables (datos que digita el jefe)** — de 1 a 12.
| Elemento | Detalle |
|---|---|
| **Etiqueta visible** | Lo que ve el jefe, ej. «Producción real (kg)». La **clave** se genera sola. |
| **↑ ↓** | Cambia el orden de los campos. |
| **✕** | Quita la variable (siempre debe quedar al menos una; bloqueado si ya hay cargas). |
| **clave** | Nombre corto que se usa en la fórmula (minúsculas, números y guion bajo; debe empezar por letra). |
| **Opciones** | **Texto de ayuda** para quien carga, **Unidad** junto al campo, **Opcional** (con valor por defecto), **Permite valores negativos**. |
| **+ Variable** | Agrega otra. |

**6 · Constantes** (opcional) — valores fijos de la fórmula que el jefe **no** ve (horas por turno, tarifa, factor…): **Nombre**, **clave**, **Valor**; **+ Constante**, **✕**. Cambiarlas afecta solo las cargas futuras.

**7 · Fórmula**
- Cuadro de texto con la fórmula (ej. `real / plan * 100`). Se valida mientras escribe.
- **Botones de inserción:** *Variables* (inserta la clave), *Operadores* (`+ − × ÷ ^ ( ) > < >= <= == != and or`) y *Funciones* (`si, div, pct, min, max, sum, avg, abs, round, sqrt, clamp`).
- Mensaje de validación y **«Se lee:»** con la fórmula en palabras.
- **Probar con valores de ejemplo:** digite números de prueba y vea el **resultado** y el **semáforo** al instante, antes de guardar.
- Use `si(b > 0, a / b * 100, 0)` o `div(a, b, 0)` para evitar dividir entre cero.

**Guía de fórmulas** (botón superior): reglas básicas, todas las funciones con ejemplos y **ejemplos listos** (cumplimiento, disponibilidad, promedio ponderado, índice de frecuencia, variación %, cumplimiento topado en 100 %, puntaje por rangos, costo unitario). El botón **Usar este ejemplo** carga fórmula, variables y constantes.

**8 · Documentación:** **Fuente de los datos**, **Método y observaciones**, casilla **Indicador activo**.

Botones finales: **Cancelar** y **Guardar indicador** (se activa solo con una fórmula válida).

#### 6.3.3 Ficha técnica en pantalla
Se abre con **Ver ficha** (o desde el panel, el historial o la tarjeta del indicador en la carga). Reproduce el formato de papel del SGC:
- Barra superior: **← Volver**, selector **Ejercicio**, **Descargar Excel (formato SGC)**, **Imprimir**.
- Encabezado con logo, empresa, gerencia y «FICHA TÉCNICA DE INDICADOR DE GESTIÓN».
- **Definición del indicador:** nombre, unidad, meta, frecuencia, fórmula, fuente y la tabla del **semáforo (Mín./Máx.)**.
- **Responsabilidades**, **Resultados de las determinaciones** (variables por período, fila **INDICADOR** coloreada y el estado de cada carga), gráfico **Valores del indicador**, **Análisis y evaluación de resultados** y **Notas**.

### 6.4 Ejercicios fiscales
Muestra un recuadro **Ciclo de vida** (Vigente → Terminado → Verificación → Cerrado) y una tarjeta por ejercicio con: estado, fechas, **Cumplimiento**, **Indicadores**, **Cargas**, **Sin cargar**, barra de semáforos y, si está cerrado, quién lo cerró, cuándo y su nota.

| Botón | Quién | Qué hace |
|---|---|---|
| **Ver panel** | Gerente / Admin | Abre el panel de ese ejercicio. |
| **Reporte Excel** / **Fichas Excel** | Gerente / Admin | Descarga el informe o las fichas de ese ejercicio. |
| **Revisar y cerrar** / **Verificar y cerrar** | Admin (ejercicio terminado) | Abre la **verificación de cierre**. |
| **Reabrir** | Admin (ejercicio cerrado) | Pide un **motivo** (mín. 5 caracteres) y vuelve a admitir cargas y revisiones. |

**Ventana de cierre** — comprueba tres cosas:
1. ✔/✖ El ejercicio **ya terminó**.
2. ✔/✖ **No hay cargas en revisión ni devueltas** (si las hay, se listan: resuélvalas antes).
3. ✔/⚠ Períodos **nunca cargados** (se pueden aceptar marcando *«Entiendo que hay períodos sin cargar y deseo cerrar de todos modos»*).
Además muestra el cumplimiento del ejercicio y permite una **Nota de cierre** (opcional). Botón **Cerrar y archivar ejercicio** (se activa solo si puede cerrarse). El ejercicio queda en **solo lectura**.

### 6.5 Importar fichas históricas
Para traer años anteriores desde el Excel de fichas técnicas (una hoja por indicador).
1. **Seleccionar archivo Excel (.xlsx)** (máx. 8 MB). El sistema lo analiza.
2. Aparece una **vista previa** por hoja: casilla para incluirla, **Código**, **Nombre**, **Área** (indica si es *Área existente* o *Área nueva*), **Frecuencia**, **Fórmula (traducida)** (edítela si falta), y las **mediciones a importar** con su semáforo. Avisos amarillos señalan lo que no se pudo interpretar.
3. Si el ejercicio fiscal del archivo difiere del del sistema, un aviso le pide ajustarlo en *Organización → Parámetros* antes de importar.
4. **Listas de apoyo encontradas**: marque las que quiera importar.
5. **Importar N indicador(es)** (o **Cancelar**). Todo se guarda **o nada** (una sola operación). Las mediciones quedan **aprobadas** y registradas en la bitácora.

### 6.6 Bitácora
Registro **inalterable** (solo inserción, con cadena de hashes SHA-256) de todo lo que ocurre: ingresos, cargas, aprobaciones, cambios de fichas, usuarios, reportes exportados, cierres, etc.
- **Verificar integridad**: recorre toda la cadena y confirma que ningún registro fue alterado.
- **Descargar Excel**: exporta la bitácora.
- Filtros: **Todas las acciones** y **Buscar por usuario**.
- Tabla: #, fecha, usuario y rol, acción, detalle y huella (hash). **Cargar más** para ver anteriores.

---

## 7. Flujo completo de ejemplo: área de Producción

Un caso paso a paso (los datos son ficticios).

**A. El administrador configura (una sola vez)**
1. *Organización → Parámetros*: elegir **Inicio del ejercicio fiscal** → **Guardar parámetros**.
2. *Organización → Áreas*: escribir `Producción` → **Agregar**.
3. *Organización → Usuarios → + Nuevo usuario*: crear `jefe.produccion` (rol *Jefe de Área*, área *Producción*) y `gerente.calidad` (rol *Gerente / Auditor SGC*), cada uno con contraseña de 10+ caracteres.
4. *Indicadores → + Nuevo indicador* (por ejemplo **Cumplimiento del plan de producción**):
   - Código `PRO-01`, nombre, área *Producción*.
   - Unidad `%`, frecuencia *Mensual*, sentido *Mayor es mejor*, 1 decimal.
   - **Meta 95** y **Límite crítico 85** (verde ≥ 95; rojo < 85).
   - Variables: `plan` «Producción planificada (kg)» y `real` «Producción real (kg)».
   - Fórmula: `real / plan * 100`. Probar con 12000 y 11900 → 99,2 % **Cumple**.
   - **Guardar indicador**.

**B. El jefe carga cada mes**
1. Ingresa como `jefe.produccion` → **Carga rápida**.
2. Elige **PRO-01** y el **período** (o pulsa el botón amarillo de pendientes).
3. Digita *Producción planificada* y *Producción real*; ve el resultado y el semáforo.
4. Si sale Alerta/Crítico, escribe **análisis** y **plan de mejora** (10+ caracteres cada uno).
5. **Enviar carga**.

**C. El gerente revisa**
1. Ingresa como `gerente.calidad` → **Bandeja de aprobación**.
2. Revisa datos y análisis. Si están bien: **Aprobar formalmente**. Si no: escribe el motivo y **Devolver con observación**.
3. Si la devolvió, el jefe la ve marcada como *Devuelta* en *Carga rápida*, corrige y pulsa **Reenviar para revisión**.

**D. Seguimiento**
- *Panel de análisis*: mapa de calor mes a mes, tendencia contra la meta y lo que *Requiere atención*.
- *Reportes*: descargar el Excel para presentar.

**E. Fin del año**
- Cuando el ejercicio termina, el administrador entra a *Ejercicios fiscales → Verificar y cerrar*; el ejercicio queda archivado en solo lectura.

> Hay un script que crea este ejemplo completo con datos de ejemplo de enero a octubre: `scripts/ejemplo_produccion.py` (ver el encabezado del archivo).

---

## 8. Reportes

Disponible para todos los roles (el jefe, solo de su área).

### 8.1 Informe de indicadores de gestión (Excel)
- Filtros: **Ejercicio fiscal** (o *Todos los ejercicios*), **Área** (no para el jefe) y **Estado de la carga** (*Todos / Aprobadas / En revisión / Devueltas*).
- Botón **Descargar reporte Excel** (muestra *Generando…*).
- Incluye **5 hojas**: *Resumen* (indicadores clave, cumplimiento por departamento y gráfico), *Mediciones*, *Tendencias* (matriz con semáforos), *Plan de mejora* (ISO 9001 9.1.3 y 10.2) y *Fichas técnicas*, más una hoja **Control**.

### 8.2 Fichas técnicas (formato SGC)
Una hoja por indicador con el diseño de la ficha en papel. Filtros **Área** (no para el jefe) e **Indicador**. Botón **Descargar fichas en Excel**. Usa el ejercicio fiscal elegido (o el vigente).

### 8.3 Verificar un reporte (gerente y administrador)
**Elegir archivo para verificar**: suba un Excel descargado del sistema. Responde:
- ✔ **Reporte auténtico**: coincide con lo que emitió el sistema.
- ✖ **Reporte no válido**, con el motivo (firma inválida, contenido modificado o número no registrado). Muestra N.º, tipo, quién lo generó y fecha.

Cada descarga queda registrada en la bitácora. Si el administrador activó el bloqueo con contraseña, los archivos se pueden abrir y leer normalmente, pero para modificar sus hojas hace falta esa contraseña.

---

## 9. Preguntas frecuentes y solución de problemas

| Situación | Qué ocurre / qué hacer |
|---|---|
| *«Sesión no válida o expirada»* | Su sesión venció (10 h), alguien cambió su contraseña o la cerró. Ingrese de nuevo. |
| *«Demasiados intentos fallidos…»* | Espere 15 minutos o pida al administrador que verifique su usuario. |
| No veo mi indicador en *Carga rápida* | Su área no lo tiene asignado, está **archivado**, o está viendo otro **ejercicio** (cámbielo arriba). |
| El período que busco no aparece | Solo se ofrecen períodos del ejercicio elegido que **ya empezaron**. Los futuros no se pueden cargar. |
| El botón **Enviar carga** está desactivado | Falta algún dato obligatorio, el resultado no se pudo calcular, o (si hay Alerta/Crítico) faltan los 10 caracteres de análisis y plan. |
| No puedo modificar una carga | Está *En revisión* o *Aprobada*. Solo se modifica si el gerente la **devuelve**. |
| *«Este período ya fue cargado y no puede modificarse»* | Igual que arriba. |
| *«El ejercicio fiscal … está cerrado»* | Es de solo lectura; el administrador puede **reabrirlo**. |
| No puedo aprobar una carga | Fue cargada por usted: la debe revisar otra persona. |
| No puedo cambiar la frecuencia o las claves de un indicador | Ya tiene cargas (por trazabilidad). Puede duplicarlo con otro código. |
| No puedo eliminar un área | Tiene indicadores o usuarios asignados. |
| No puedo cambiar el inicio del ejercicio | Hay ejercicios cerrados o cargas que no son mensuales. |
| Un reporte Excel pide contraseña | El administrador activó el bloqueo (*Organización → Parámetros*). |
| *«No se puede leer la contraseña de los reportes»* | Cambió la clave secreta del sistema; el administrador debe definir una nueva contraseña de reportes. |
| *«El sistema está ocupado…»* | Otra operación estaba escribiendo; reintente en unos segundos. |

---

## 10. Glosario

- **Ficha técnica**: definición completa de un indicador (qué mide, fórmula, meta, responsables).
- **Variable**: dato que el jefe digita cada período.
- **Constante**: valor fijo que interviene en la fórmula; el jefe no lo ve.
- **Meta / Límite crítico**: umbrales que definen el semáforo.
- **Carga**: el registro de un indicador para un período.
- **Ejercicio fiscal**: año de gestión de la empresa; sus datos se mantienen separados.
- **Bitácora**: registro inalterable de toda la actividad del sistema.
- **Segregación de funciones**: nadie revisa su propia carga.
