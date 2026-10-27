# SGC • TRIPOLIVEN · Sistema de Gestión de la Calidad — indicadores de gestión de Tripoliven, C.A.

Aplicación web (FastAPI + SQLAlchemy + Alpine.js + Tailwind + Chart.js) para cargar, aprobar y analizar indicadores bajo ISO 9001:2015. Diseño por tarjetas, responsive, con navegación inferior en móvil.
No incluye datos de ejemplo: se parte de una base vacía y el administrador crea áreas, usuarios e indicadores desde la propia interfaz.

## Producción con Supabase
1. En Supabase: *Project Settings → Database → Connection string (URI)*. Use el **Session pooler** (puerto 5432) para un servidor persistente, o el **Transaction pooler** (6543) en plataformas serverless.
2. Defina las variables (ver `.env.example`):
   | Variable | Descripción |
   |---|---|
   | `SIGT_ENV=production` | Cookies `Secure`, HSTS, sin `/docs`; exige `SIGT_SECRET` y base de datos. |
   | `SIGT_DATABASE_URL` | URI de Supabase (`postgresql://…?sslmode=require`). |
   | `SIGT_SECRET` | 32+ caracteres aleatorios (firma de sesiones). |
   | `SIGT_ADMIN_USER` / `SIGT_ADMIN_PASSWORD` | Solo para crear el primer administrador con la base vacía (≥ 10 caracteres). Elimine la contraseña después. |
   | `SIGT_TRUST_PROXY=1` | Detrás de un proxy/balanceador (IP real para el límite de intentos). |
3. Despliegue: `docker build -t sgc-tripoliven . && docker run -p 8000:8000 --env-file .env sgc-tripoliven` (o cualquier plataforma que ejecute el `Dockerfile`). Healthcheck: `GET /healthz`. Sirva siempre tras HTTPS.
4. **Migraciones (Alembic).** El esquema solo cambia mediante migraciones versionadas (`migrations/versions/`). Antes de arrancar una versión nueva ejecute `alembic upgrade head` con las mismas variables de entorno (el `Dockerfile` ya lo hace al iniciar el contenedor; el *advisory lock* evita que dos réplicas migren a la vez). En producción la aplicación **solo verifica** que la base esté al día y, si no lo está, responde 503 indicando qué hacer; con `SIGT_AUTO_MIGRATE=1` migra ella sola al arrancar. La primera migración crea las tablas (o completa una base creada antes de Alembic sin perder datos), deja un *trigger* que impide UPDATE/DELETE en `bitacora` y activa RLS en las tablas (la API REST pública de Supabase queda sin acceso; la aplicación usa el rol `postgres`). Si el usuario de la base no tiene permisos para ello, ejecute `scripts/supabase_hardening.sql` en el SQL Editor. **Importante:** la migración `0003` cifra la contraseña de los reportes con `SIGT_SECRET`; ejecútela con la misma `SIGT_SECRET` que usa la aplicación. En Vercel (sin paso de despliegue) migre desde su equipo o CI con `SIGT_DATABASE_URL`/`SIGT_SECRET` de producción, o defina `SIGT_AUTO_MIGRATE=1`.
5. Ingrese como administrador y siga la guía de configuración inicial: **Organización** (áreas y usuarios) → **Indicadores** (fichas).

Alternativa sin variable de entorno: `python -m app.crear_admin`.

## Desarrollo local
```bash
pip install -r requirements-dev.txt        # dependencias congeladas + pytest, httpx, ruff, pip-audit
SIGT_ADMIN_USER=admin SIGT_ADMIN_PASSWORD=una-clave-larga python run.py   # SQLite en data/sigt.db (migra solo en desarrollo)
alembic revision --autogenerate -m "descripción"   # tras cambiar app/models.py; revise el archivo generado
alembic upgrade head
pytest                                  # SQLite; con SIGT_DATABASE_URL corre contra Postgres
npm install && npm run build:css        # solo si modifica las clases Tailwind (el CSS compilado va en el repositorio)
```
Tailwind, Alpine y Chart.js se sirven desde `app/static/` (sin CDN ni dependencias externas en tiempo de ejecución).

## Arquitectura

El código sigue capas; cada una solo depende de las anteriores (lo que se necesita primero va primero):

```
app/
  config.py, database.py, models.py, schemas.py, errores.py   base: configuración, ORM, entradas validadas, errores de negocio
  dominio/      reglas puras, sin BD ni HTTP: formulas (evaluador AST seguro), semaforo, calendario (ejercicio fiscal), ficha_texto
  servicios/    casos de uso (lanzan ErrorNegocio): arranque, sesion, parametros, marca (logo), organizacion, indicadores,
                mediciones, ejercicios, panel, bitacora/auditoria, reportes, importacion + lector_excel
  excel/        generación de libros .xlsx (comun, general, ficha, bitacora)
  api/          routers delgados por funcionalidad (sesion, organizacion, indicadores, mediciones, ejercicios, reportes,
                importacion, bitacora), deps (sesión y permisos) y serializadores
  main.py       ensamblado: arranque diferido, cabeceras de seguridad, traducción de errores, routers, estáticos
  plantilla.py  expande los parciales HTML (<!--#incluir ...-->)
  static/       index.html + parciales/ (vistas y componentes) + js/ (un módulo Alpine por funcionalidad, compuestos en app.js)
tests/          dominio/ (unitarias puras), api/ (por funcionalidad), test_migracion.py; conftest.py con fábricas de datos
```

Los tests son independientes entre sí: cada uno crea sus propios datos (`tests/conftest.py`). Estilo: `ruff check app api run.py tests` (configuración en `ruff.toml`; no usar `pyproject.toml`: Vercel lo detecta y deja de instalar `requirements.txt`).

## Roles
| Rol | Capacidades |
|---|---|
| Jefe de Área | Carga rápida de su área; resultado y semáforo en vivo; análisis y plan de mejora obligatorios si hay Alerta/Crítico (validado en servidor); reenvío de cargas devueltas. |
| Gerente / Auditor SGC | Bandeja de aprobación, notas de auditoría, panel de análisis, exportación CSV. |
| Administrador SGC | Fichas de indicadores, áreas, usuarios (alta, roles, restablecer clave, desactivar), bitácora. |

## Reglas y seguridad
- Semáforo «mayor es mejor»: verde ≥ meta, amarillo ≥ límite, rojo < límite; el inverso es simétrico.
- Cada carga guarda meta/límite vigentes; editar la ficha no altera el histórico. Cargas enviadas/aprobadas no se modifican; si se devuelven, se reenvían (versión +1).
- Eliminar un indicador o usuario con historial lo archiva/desactiva; un área con indicadores o usuarios no se elimina.
- Fórmulas con evaluador AST restringido (sin `eval`).
- Bitácora de solo inserción con cadena SHA-256 (verificable desde la interfaz), protegida además por trigger en Postgres y bloqueo en el ORM; escrituras serializadas con *advisory lock* entre procesos.
- Contraseñas PBKDF2-SHA256 (210 000 iteraciones), mínimo 10 caracteres; cambiar o restablecer una clave invalida las sesiones previas; bloqueo por intentos fallidos (5 por IP+usuario, 20 por IP, 10 por usuario, en 15 min) con contadores en la base, compartidos entre procesos; cerrar sesión revoca el token en el servidor; la contraseña de los reportes se guarda cifrada (Fernet, clave derivada de `SIGT_SECRET`); cabeceras CSP/HSTS/X-Frame-Options.

## Vercel
`vercel.json` + `api/index.py` ejecutan la app como función serverless. Variables obligatorias (Project → Settings → Environment Variables): `SIGT_ENV=production`, `SIGT_SECRET`, `SIGT_DATABASE_URL` (use el **pooler** de Supabase, no `db.<proyecto>.supabase.co`, que es solo IPv6), `SIGT_ADMIN_USER`, `SIGT_ADMIN_PASSWORD`. Tras cambiar variables hay que redesplegar. Si falla, revise Deployments → Logs: el mensaje indica la variable que falta.

## Permisos del Administrador SGC
Acceso a todo el sistema: fichas, áreas y usuarios; carga de datos en cualquier área; bandeja de aprobación, notas de auditoría, panel, cargas, exportación y bitácora. Por segregación de funciones (ISO 9001), nadie puede aprobar ni devolver una carga que realizó él mismo.

## Gestión de indicadores
Búsqueda y filtros (área, frecuencia, estado), duplicar, archivar/restaurar, eliminar (con cargas se archiva), claves de variables generadas automáticamente, reordenar variables, validación de fórmula con aviso de variables sin usar y probador con resultado y semáforo en vivo. Con cargas registradas no se puede cambiar la frecuencia ni las claves de las variables; los cambios de meta o fórmula quedan en la bitácora y no alteran el histórico.

## Reportes en Excel
`GET /api/reportes/general.xlsx` (botón en **Reportes**): hojas *Resumen* (indicadores clave, cumplimiento por departamento y gráfico), *Mediciones*, *Tendencias* (matriz con semáforos), *Plan de mejora* (ISO 9001: 9.1.3 y 10.2) y *Fichas técnicas*. Filtros por año, área y estado; el jefe de área solo obtiene su área. Cada descarga queda en la bitácora. El administrador también puede descargar la bitácora (`/api/reportes/bitacora.xlsx`).

## Un ejercicio fiscal a la vez

El ejercicio elegido en la cabecera gobierna **todas** las pantallas de datos, de modo que nunca se mezcla un año con otro:

- **Carga rápida:** solo ofrece los períodos de ese ejercicio (hasta el actual). Los pendientes de otros ejercicios se avisan aparte («Ir a ese ejercicio»).
- **Bandeja y Historial:** muestran únicamente ese ejercicio; las cargas por aprobar de otros ejercicios se avisan con un botón, y el historial puede incluir «otros ejercicios» agrupados por año.
- **Inicio, Panel, Fichas y Reportes:** usan el mismo ejercicio (los reportes lo traen preseleccionado y las hojas «Mediciones» y «Plan de mejora» llevan la columna «Ejercicio fiscal»).
- En pantallas ≥ 1024 px la navegación es una barra lateral (`parciales/barra_lateral.html`); en tabletas, píldoras en la cabecera; en móvil, la barra inferior.
- Si se está viendo un ejercicio distinto al vigente, un aviso lo indica con el botón «Volver al ejercicio vigente».
- API: `GET /api/indicadores?ejercicio=` y `GET /api/indicadores/{id}/periodos?ejercicio=` (por defecto, el vigente); cada medición informa su `ejercicio`. Cada módulo de la interfaz recarga lo suyo con el gancho `ejercicio()`.

## Formato de los Excel y reinicio de fábrica

- Todos los libros pasan por `excel/comun.ajustar()`: filas y columnas se dimensionan según su contenido (texto largo, celdas combinadas, fórmula en varias líneas), el logo y los gráficos tienen espacio propio y `tests/api/test_excel_formato.py` comprueba que nada se superponga ni se recorte. Al agregar una hoja nueva, termínela con `ajustar(ws)`.
- **Organización → Zona de peligro → Borrar todos los datos** deja el sistema como recién instalado: elimina indicadores, cargas, áreas, usuarios, listas, parámetros, logo y bitácora. Pide escribir «BORRAR TODO» y la contraseña del administrador, y conserva únicamente esa cuenta para poder volver a entrar. No deja rastro en la bitácora (también queda vacía).

## Reportes protegidos y verificables

- Los Excel exportados llevan **fórmulas vivas**: en cada ficha el resultado se recalcula desde los datos de su período y el semáforo se evalúa con la meta y el límite (`app/dominio/formula_excel.py` traduce la fórmula del sistema; si alguna no tiene equivalente exacto queda el valor calculado).
- En **Organización → Parámetros** el administrador activa «Bloquear los reportes en Excel con contraseña» y define la contraseña (no se muestra ni se registra en la bitácora). Todas las hojas y la estructura del libro quedan protegidas.
- Cada reporte lleva un **número** y una hoja **Control** con la huella SHA-256 de su contenido y una firma HMAC del sistema; la emisión queda en la bitácora. En **Reportes → Verificar un reporte** (gerente y administrador) se sube el archivo y se comprueba que no fue alterado.
- Nota: la protección de Excel evita cambios accidentales, pero puede quitarse con herramientas externas; lo que garantiza la integridad es la verificación.

## Bitácora: solo administrador
Únicamente el Administrador SGC puede ver, verificar y exportar los registros del sistema (los demás roles reciben 403 y no ven la sección).

## Fórmulas
Operadores `+ − × ÷ ^ % //`, comparaciones, `and/or/not`, `si(cond, a, b)` y `a if cond else b` (evalúan solo la rama elegida: protegen divisiones), `div`, `pct`, `min`, `max`, `sum`, `avg`, `abs`, `round`, `sqrt`, `floor`, `ceil`, `clamp`. Constantes por indicador, variables opcionales con valor por defecto, valores negativos permitidos por variable, decimales configurables y frecuencias mensual/trimestral/semestral/anual. Cada carga guarda una foto de la fórmula, constantes y decimales vigentes. La ficha lleva botones **i** de ayuda, una guía de fórmulas con ejemplos y un probador en vivo.

## Actualizaciones de esquema
Al arrancar, `app/servicios/arranque.py` agrega automáticamente las columnas nuevas a las tablas existentes (migración aditiva, sin pérdida de datos), por lo que una base de Supabase ya en uso se actualiza sola al desplegar.

## Reemplazo de las fichas en Excel
El sistema cubre todo lo que se llevaba en el libro «Ficha técnica de indicador de gestión» (formato NC-16-7):
- **Ficha completa:** seguimiento (proceso / objetivo organizacional / proveedor), proceso y su objetivo, sigla, gerencia, departamento, líder de proceso, responsables de medición/registro/análisis, fuente, meta («96 Mín.», «3 Máx.»), semáforo con franjas Mín./Máx., fórmula documentada con su leyenda de símbolos y notas. Vista en pantalla (**Ver ficha**), imprimible y exportable.
- **Ejercicio fiscal** configurable (p. ej. octubre–septiembre) y frecuencias **mensual, bimestral, trimestral, cuatrimestral, semestral, anual y eventual**; los períodos se alinean al ejercicio (trimestres que cierran en Dic./Mar./Jun./Sep.).
- **Resultados por período** con cálculo automático, análisis de resultados y correcciones / oportunidades de mejora por período, gráfico de valores con mínimo y máximo.
- **Listas de apoyo** (gerencias, procesos con su objetivo, objetivos organizacionales, cargos) administrables en Organización.
- **Excel por indicador en el formato de la ficha** (`Reportes → Fichas técnicas`): una hoja por indicador con el mismo diseño y gráfico.
- **Importación de años anteriores** (`Importar`): lee el Excel de fichas (una hoja por indicador), traduce la fórmula, propone indicadores y mediciones, muestra una vista previa editable y los carga como aprobados, con registro en la bitácora. Si el ejercicio fiscal del archivo difiere del configurado, avisa antes de importar.

## Diseño de la interfaz
Estilo sobrio y cálido inspirado en Claude.com: fondo crema, títulos en tipografía serif, tarjetas y controles muy redondeados, botones en forma de píldora, cabecera translúcida con navegación en cápsula (escritorio) y barra flotante inferior con menú «Más» (móvil), hojas modales que suben desde abajo en el teléfono y respeto de «reducir movimiento». Conserva los azules corporativos (#0f172a y #0284c7) como acentos. Los estilos se compilan con `npm run build:css` (fuente en `src/input.css` y `tailwind.config.js`).

## Ejercicios fiscales (organización por año de gestión)
- **Selector global** en la cabecera: panel, historial, reportes y fichas se filtran por ejercicio; los registros de años distintos no se mezclan. Cada período de carga está agrupado por ejercicio.
- **Ciclo de vida:** vigente → terminado → verificación → **cerrado**. Sección *Ejercicios fiscales* (administrador gestiona, gerente consulta): estado y resultados de cada año, reportes Excel por ejercicio, cierre con lista de comprobación (sin cargas en revisión/devueltas, períodos sin cargar) y reapertura con motivo.
- Un ejercicio cerrado es de **solo lectura** (cargas, aprobaciones, notas, importaciones) y conserva una foto de sus resultados; todo queda en la bitácora. No se puede cambiar el mes de inicio del ejercicio mientras haya ejercicios cerrados.
- Aviso al administrador/gerente cuando un ejercicio terminó y sigue abierto.

## Dashboard
Estado del ejercicio (avance, carga al día), indicadores clave con comparativo contra el ejercicio anterior, «Requiere atención» (críticos, alertas que empeoran, cargas pendientes), mapa de calor indicador × mes, tendencia vs. meta del ejercicio, distribución de semáforos y cumplimiento por departamento con marca del año anterior.

## Guía de bienvenida y logo
- La primera vez que cada usuario inicia sesión se muestra una **guía paso a paso** según su rol (qué hace cada botón y sección); se puede omitir y repetir desde el menú del perfil («Ver guía de uso»).
- **Logo de la empresa** (Organización → Parámetros): se sube desde el navegador, se valida y se guarda en la base de datos; aparece en el ingreso, la cabecera, la ficha técnica y los reportes Excel.
