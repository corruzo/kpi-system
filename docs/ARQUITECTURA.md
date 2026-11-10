# Arquitectura de SPE TPV

## Capas (la dependencia va siempre hacia abajo)

```
 navegador (Alpine.js, módulos en app/static/js)        ← solo presentación; nunca decide permisos
        │  HTTPS, cookie de sesión HttpOnly
 app/main.py            middleware: CSRF/origen, cabeceras de seguridad, Cache-Control, Vary
 app/api/routers/*      HTTP: valida entrada (schemas.py), declara el rol exigido (deps.requiere), traduce errores
 app/api/serializadores salida JSON explícita (nunca se devuelve un modelo tal cual)
 app/servicios/*        reglas de negocio y transacciones; no conocen HTTP
 app/dominio/*          lógica pura sin base de datos: calendario fiscal, fórmulas, semáforo, meta
 app/models.py          esquema (SQLAlchemy 2) — la verdad del modelo de datos
 migrations/versions    única vía para cambiar el esquema (Alembic); `alembic check` impide divergencias
```

## Reglas de ingeniería

1. **Un solo lugar para cada decisión de acceso.** Qué indicadores ve cada rol lo decide `servicios/acceso.py`
   (`restringir` para consultas, `exigir_visible` para un registro). Ningún servicio filtra por rol por su cuenta.
2. **Aislamiento estricto del encargado de proceso.** Cada indicador tiene un único `encargado_id`; el encargado solo ve y
   carga lo que se le asignó (aunque comparta área con otro). Lo no visible responde **404**, no 403, para no revelar que
   existe. Cubierto por `tests/api/test_aislamiento.py` (incluye un barrido que exige sesión en *toda* ruta `/api/*`).
3. **La base garantiza lo que el código promete**: claves foráneas, `CHECK`, índices en todas las FK, RLS activada en Supabase
   y roles `anon`/`authenticated` sin permisos (el único camino a los datos es esta aplicación).
4. **Bitácora inmutable y encadenada** (SHA-256 del registro anterior; trigger en PostgreSQL contra UPDATE/DELETE).
5. **Escrituras serializadas**: dependencia `escritura` (bloqueo asesor 727001 en PostgreSQL / candado en SQLite) → la cadena
   de la bitácora y los consecutivos (códigos de indicador) no se corrompen con peticiones simultáneas.
6. **Errores de negocio tipados** (`errores.py`): los servicios lanzan `Invalido/Conflicto/NoEncontrado/Prohibido`; la API los
   convierte en JSON. Nada de `except Exception` silenciosos.
7. **Sin dependencias en tiempo de ejecución fuera del servidor**: Tailwind compilado, Alpine y Chart.js se sirven locales.
   La CSP conserva `unsafe-eval`/`unsafe-inline` solo porque Alpine los necesita.
8. **Caché**: toda respuesta `/api/*` lleva `Cache-Control: no-store` y `Vary: Cookie` (salvo `/api/publico`, 60 s, sin datos de
   usuario, y el logo versionado). Al cerrar sesión se borran las preferencias locales.

## Datos y roles

| Rol (interno) | Nombre en pantalla | Ve | Hace |
|---|---|---|---|
| `jefe` | Encargado de proceso | Solo sus indicadores asignados | Carga datos y corrige devoluciones |
| `gerente` | Gerente / Auditor SGC | Todo lo activo | Aprueba/devuelve, presupuesta, analiza |
| `admin` | Administrador SGC | Todo (incluso archivados) | Configura, soporte, respaldos |

El valor interno `jefe` se conserva (restricción `ck_usuarios_rol` y sesiones existentes); solo cambia el texto mostrado.

## Calidad automatizada

`make verificar` ejecuta lo mismo que el CI (`.github/workflows/ci.yml`): ruff, pytest en SQLite **y** PostgreSQL 16, migraciones
desde cero + `alembic check`, CSS compilado al día y `pip-audit` de dependencias. `.pre-commit-config.yaml` lo corre antes de
cada commit/push. Despliegue: Vercel despliega la rama `master`; las migraciones se aplican al arrancar.

## Rendimiento
- **Una petición de arranque** (`GET /api/arranque`) entrega usuario, parámetros, ejercicios, indicadores, áreas, bandeja, listas y
  resumen de inicio según el rol (reutiliza los mismos routers, así cada dato conserva su regla de acceso). Antes eran ~10
  peticiones, varias encadenadas: en un servidor remoto cada una paga su viaje de red.
- **CDN**: estáticos con huella `s-maxage` de un año; el HTML y `/api/publico` con `s-maxage` corto y `stale-while-revalidate`,
  para que la CDN de Vercel los sirva sin despertar la función de Python.
- **Interfaz**: sin `backdrop-filter` ni `blur` de pantalla completa (costosos de pintar en móviles), animaciones de entrada de
  0,18 s solo en opacidad/desplazamiento y sin muelles, observadores del DOM limitados a atributos.
- **Base de datos**: listados sin consultas por fila (p. ej. ejercicios: una consulta, no una por año).
