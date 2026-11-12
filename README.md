# SPE TPV · indicadores de gestión (ISO 9001) de Tripoliven, C.A.

Aplicación web (FastAPI + SQLAlchemy 2 + Alembic + Pydantic v2; Alpine.js + Tailwind + Chart.js + Motion) para cargar, aprobar y analizar
indicadores de gestión. Diseño por tarjetas, responsive (navegación inferior en móvil, barra lateral en escritorio). No incluye datos de
ejemplo: se parte de una base vacía.

## Modelo de la versión 2 (jerárquico)

La empresa se modela como funciona físicamente: **cada gerente ve toda su gerencia, cada jefe ve toda su jefatura y quien carga datos solo
ve lo que carga. Ver baja por el árbol; modificar es solo lo asignado personalmente.**

- **Estructura:** `Empresa → Gerencia → Departamento → Jefatura` (tabla `unidades`, con `ruta` materializada). Los indicadores cuelgan de
  un nodo de cualquier nivel y tienen un **responsable** (el «dueño», único que modifica la ficha) y uno o más **cargadores**.
- **Personas:** cada persona tiene **un rol**, **cero o más nodos de ámbito** (ve ese nodo y todo lo que cuelga de él) y sus indicadores.
  Una cuenta nueva **no tiene acceso a nada** hasta que el Coordinador SGC la asigna («pendiente de asignación»).
- **Roles:** dos de sistema — **Desarrollador** (todo, incluido lo técnico; inmutable) y **Coordinador SGC** (todo lo funcional, nada técnico;
  define los demás roles). El Coordinador crea roles con nombre libre (Gerente general, Gerente, Jefe, Analista…) eligiendo solo el **nivel**
  (Ninguno / Ver / Ver y modificar) de cada permiso del catálogo; el **alcance** es fijo.
- **Permisos:** catálogo único en `app/permisos.py` (documentado en [`docs/PERMISOS.md`](docs/PERMISOS.md), generado desde el código y
  validado por una prueba). Toda ruta `/api/*` declara su permiso con `requiere_permiso`; el motor `app/servicios/acceso.py` cruza
  **rol × árbol × asignación**. Lo que no se ve responde **404**; lo que se ve pero no se puede hacer, **403**.
- **Aprobación jerárquica:** aprueba el superior más cercano de quien cargó (el nivel más cercano hacia arriba con un aprobador distinto del
  autor); el Coordinador SGC es respaldo; nadie aprueba una carga propia.
- **Vocabulario:** **Meta** = lo que se espera lograr en un período; **Nivel óptimo** = umbral verde del semáforo
  (antes «meta» de la ficha); **Límite crítico** = frontera del rojo.

## Producción con Supabase
1. En Supabase: *Project Settings → Database → Connection string (URI)*. **Session pooler** (5432) para servidor persistente o **Transaction pooler** (6543) en plataformas serverless.
2. Variables (ver `.env.example`):
   | Variable | Descripción |
   |---|---|
   | `SIGT_ENV=production` | Cookies `Secure`, HSTS, sin `/docs`; exige `SIGT_SECRET` y base de datos. |
   | `SIGT_DATABASE_URL` | URI de Supabase (`postgresql://…?sslmode=require`). |
   | `SIGT_SECRET` | 32+ caracteres aleatorios (firma de sesiones y cifrado de la clave de reportes). |
   | `SIGT_ADMIN_USER` / `SIGT_ADMIN_PASSWORD` | Solo con la base vacía: crean al **primer Desarrollador** (≥ 10 caracteres). Elimine la contraseña después. |
   | `SIGT_TRUST_PROXY=1` | Detrás de un proxy/balanceador (IP real para el límite de intentos). |
3. Despliegue: `docker build -t spe-tpv . && docker run -p 8000:8000 --env-file .env spe-tpv` (o Vercel: `vercel.json` + `api/index.py`, rama `master`; las migraciones corren al arrancar). Healthcheck: `GET /healthz`. Siempre tras HTTPS.
4. **Migraciones (Alembic):** el esquema solo cambia con migraciones versionadas (`migrations/versions/`): `v2_0001` (esquema base) y `v2_0002` (endurecimiento PostgreSQL: bitácora inmutable por trigger, RLS en todas las tablas, sin permisos para `anon`/`authenticated`). `alembic upgrade head` antes de arrancar; `alembic check` verifica que no haya diferencias con los modelos.
5. **Pasar de la versión 1 a la 2 destruye los datos** (eran de prueba): siga el procedimiento de [`docs/OPERACION.md`](docs/OPERACION.md) («Reinicio a la versión 2»), con `scripts/reset_produccion_v2.sql`.
6. Ingrese como Desarrollador y siga **Puesta en marcha**: estructura → roles → personas → indicadores → período fiscal → metas → carga.

Alternativa sin variable de entorno: `python -m app.crear_admin` (crea un Desarrollador).

## Desarrollo local
```bash
pip install -r requirements-dev.txt        # dependencias congeladas + pytest, httpx, ruff, pip-audit
SIGT_ADMIN_USER=admin SIGT_ADMIN_PASSWORD=una-clave-larga python run.py   # SQLite en data/sigt.db (migra solo en desarrollo)
alembic revision --autogenerate -m "descripción"   # tras cambiar app/models.py; revise el archivo generado
pytest                                              # SQLite; con SIGT_DATABASE_URL corre contra PostgreSQL
python -m app.permisos_doc                          # regenera docs/PERMISOS.md tras cambiar el catálogo o los permisos de las rutas
npm install && npm run build:css                    # solo si modifica clases Tailwind (el CSS compilado va en el repositorio)
make verificar                                      # ruff + pytest + migraciones + alembic check + CSS al día (lo mismo que el CI)
```
Tailwind, Alpine y Chart.js se sirven desde `app/static/` (sin CDN). No agregue `pyproject.toml` (Vercel lo trataría como proyecto instalable).

## Arquitectura
```
app/
  config.py, database.py, models.py, schemas.py, errores.py   base: configuración, ORM, entradas validadas, errores de negocio
  permisos.py   catálogo único de permisos (código, grupo, niveles, alcance, técnico, implica); permisos_doc.py genera docs/PERMISOS.md
  dominio/      reglas puras sin BD ni HTTP: formulas (evaluador AST seguro), semaforo, calendario fiscal, meta, ficha_texto
  servicios/    casos de uso: acceso (EL motor de permisos), estructura (árbol), roles, personas, indicadores, mediciones (aprobación
                jerárquica), metas, ejercicios, panel, tablero, reportes, recordatorios, importacion + lector_excel, respaldo, reinicio,
                auditoria (bitácora encadenada), parametros, marca, sesion, arranque
  excel/        libros .xlsx en blanco y negro (comun, general, ficha, bitacora, sello)
  api/          routers delgados por funcionalidad + deps (requiere_permiso, sesión) + serializadores
  main.py       ensamblado: cabeceras de seguridad, CSRF/origen, traducción de errores, routers, estáticos
  static/       index.html + parciales/ (vistas y componentes) + js/ (un módulo Alpine por funcionalidad, compuestos en app.js)
tests/          dominio/ (puras), api/ (por funcionalidad, incluye barrido ruta × rol), test_migracion, test_respaldo, test_permisos_doc
```
Detalle y reglas de ingeniería en [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md). Las pruebas son independientes: cada una crea sus propios datos (`tests/conftest.py`).

## Flujo anual: período fiscal → meta → carga mensual → aprobación
1. El Desarrollador crea las cuentas; el Coordinador SGC arma la estructura, define roles y asigna personas e indicadores.
2. Quien tiene `ejercicios.crear` abre el **período fiscal** (octubre–septiembre configurable en Parámetros).
3. Quien tiene `metas.cargar` fija la **meta** por período o anual repartida (indicadores propios y de quienes están debajo; el Coordinador, todos). Sin meta del período no se carga el dato real.
4. El **cargador** digita el dato; el sistema calcula resultado y semáforo y lo compara con la meta del período. En amarillo/rojo el análisis y el plan de mejora son obligatorios (ISO 9001:2015, 9.1.3 y 10.2).
5. El **superior directo** aprueba o devuelve (Bandeja). Al terminar el año: verificación, **cierre** con foto de resultados y reapertura con motivo.
Los indicadores `eventual` no llevan meta.

## Seguridad
- Cookie de sesión `HttpOnly`/`SameSite=Strict`, verificación de origen (CSRF), CSP, `Cache-Control: no-store` + `Vary: Cookie` en `/api/*`.
- Contraseñas PBKDF2-SHA256 (210 000 iteraciones, mínimo 10 caracteres); cambiar o restablecer una clave invalida las sesiones; bloqueo por intentos fallidos (5 por IP+usuario, 20 por IP, 10 por usuario en 15 min) con contadores en la base.
- Bitácora inmutable y encadenada con SHA-256 (trigger en PostgreSQL); cada cambio de rol, permiso, ámbito o asignación queda registrado.
- Anti-escalada: nadie edita su propio rol, nadie concede un permiso que no tiene, el Coordinador no toca a un Desarrollador y los permisos técnicos no se conceden a ningún rol. El sistema nunca queda sin un Desarrollador activo.
- RLS en todas las tablas de Supabase y sin permisos para `anon`/`authenticated` (`scripts/supabase_hardening.sql`); escrituras serializadas con *advisory lock*.
- Respaldo cifrado (`python -m app.respaldar`), reportes Excel con fórmulas vivas, firmados y verificables.

## Operación
[`docs/OPERACION.md`](docs/OPERACION.md): respaldos (RPO/RTO), restauración, reinicio a la versión 2, incidentes. Manual de usuario completo:
[`docs/MANUAL_DE_USO.txt`](docs/MANUAL_DE_USO.txt) (actualícelo si cambia el funcionamiento). Catálogo de permisos: [`docs/PERMISOS.md`](docs/PERMISOS.md).
