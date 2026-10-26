# SIGT · Sistema de Indicadores de Gestión — Tripoliven, C.A.

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
3. Despliegue: `docker build -t sigt . && docker run -p 8000:8000 --env-file .env sigt` (o cualquier plataforma que ejecute el `Dockerfile`). Healthcheck: `GET /healthz`. Sirva siempre tras HTTPS.
4. Primer arranque: crea las tablas, un *trigger* que impide UPDATE/DELETE en `bitacora` y activa RLS en todas las tablas (la API REST pública de Supabase queda sin acceso; la aplicación usa el rol `postgres`). Si el usuario de la base no tiene permisos para ello, ejecute `scripts/supabase_hardening.sql` en el SQL Editor.
5. Ingrese como administrador y siga la guía de configuración inicial: **Organización** (áreas y usuarios) → **Indicadores** (fichas).

Alternativa sin variable de entorno: `python -m app.crear_admin`.

## Desarrollo local
```bash
pip install -r requirements.txt pytest httpx
SIGT_ADMIN_USER=admin SIGT_ADMIN_PASSWORD=una-clave-larga python run.py   # SQLite en data/sigt.db
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
- Contraseñas PBKDF2-SHA256 (210 000 iteraciones), mínimo 10 caracteres; cambiar o restablecer una clave invalida las sesiones previas; bloqueo tras 5 intentos fallidos en 15 min; cabeceras CSP/HSTS/X-Frame-Options.

## Vercel
`vercel.json` + `api/index.py` ejecutan la app como función serverless. Variables obligatorias (Project → Settings → Environment Variables): `SIGT_ENV=production`, `SIGT_SECRET`, `SIGT_DATABASE_URL` (use el **pooler** de Supabase, no `db.<proyecto>.supabase.co`, que es solo IPv6), `SIGT_ADMIN_USER`, `SIGT_ADMIN_PASSWORD`. Tras cambiar variables hay que redesplegar. Si falla, revise Deployments → Logs: el mensaje indica la variable que falta.

## Permisos del Administrador SGC
Acceso a todo el sistema: fichas, áreas y usuarios; carga de datos en cualquier área; bandeja de aprobación, notas de auditoría, panel, cargas, exportación y bitácora. Por segregación de funciones (ISO 9001), nadie puede aprobar ni devolver una carga que realizó él mismo.

## Gestión de indicadores
Búsqueda y filtros (área, frecuencia, estado), duplicar, archivar/restaurar, eliminar (con cargas se archiva), claves de variables generadas automáticamente, reordenar variables, validación de fórmula con aviso de variables sin usar y probador con resultado y semáforo en vivo. Con cargas registradas no se puede cambiar la frecuencia ni las claves de las variables; los cambios de meta o fórmula quedan en la bitácora y no alteran el histórico.

## Reportes en Excel
`GET /api/reportes/general.xlsx` (botón en **Reportes**): hojas *Resumen* (indicadores clave, cumplimiento por departamento y gráfico), *Mediciones*, *Tendencias* (matriz con semáforos), *Plan de mejora* (ISO 9001: 9.1.3 y 10.2) y *Fichas técnicas*. Filtros por año, área y estado; el jefe de área solo obtiene su área. Cada descarga queda en la bitácora. El administrador también puede descargar la bitácora (`/api/reportes/bitacora.xlsx`).

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
