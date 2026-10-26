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
