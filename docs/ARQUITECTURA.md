# Arquitectura de SPE TPV

## Capas (la dependencia va siempre hacia abajo)

```
 navegador (Alpine.js, módulos en app/static/js)   ← solo presentación; nunca decide permisos
        │  HTTPS, cookie de sesión HttpOnly
 app/main.py            middleware: CSRF/origen, cabeceras de seguridad, Cache-Control, Vary
 app/api/routers/*      HTTP: valida entrada (schemas.py), declara el permiso exigido (deps.requiere_permiso), traduce errores
 app/api/serializadores salida JSON explícita (nunca se devuelve un modelo tal cual)
 app/servicios/*        reglas de negocio y transacciones; no conocen HTTP. acceso.py es el motor de permisos
 app/dominio/*          lógica pura sin base de datos: calendario fiscal, fórmulas, semáforo, meta
 app/permisos.py        catálogo único de permisos
 app/models.py          esquema (SQLAlchemy 2) — la verdad del modelo de datos
 migrations/versions    única vía para cambiar el esquema (Alembic); `alembic check` impide divergencias
```

## Reglas de ingeniería

1. **Un solo lugar para cada decisión de acceso.** `servicios/acceso.py` (con el catálogo `permisos.py`) decide qué puede ver y hacer cada
   persona: `puede`, `ambito`, `indicadores_visibles` (consultas), `exigir_visible`, `exigir_modificable`, `exigir_cargable`,
   `exigir_asignacion`, `aprobadores_de`. Ninguna ruta ni servicio filtra por rol por su cuenta.
2. **Toda ruta declara su permiso** (`requiere_permiso("codigo")`, o es de cuenta propia / pública). `tests/api/test_barrido_permisos.py`
   recorre TODAS las rutas × cada rol de prueba y falla si alguna queda sin declarar o si el catálogo y las rutas divergen;
   `docs/PERMISOS.md` se genera de ambos (`python -m app.permisos_doc`) y una prueba lo valida.
3. **404 / 403:** lo que la persona no puede ver responde 404 (no revela que existe); lo que ve pero no puede hacer, 403.
4. **Permisos leídos una vez por petición** (`acceso.preparar` en `deps.usuario_actual`: usuario + rol, permisos y posición) y guardados en
   `usuario.acceso`; un cambio de permisos rige desde la siguiente petición. Sin N+1 en las rutas calientes (probado en `test_robustez`).
5. **La base garantiza lo que el código promete:** claves foráneas, `CHECK`, `NOT NULL`, únicos, índices en toda FK, RLS en Supabase y
   roles `anon`/`authenticated` sin permisos (el único camino a los datos es esta aplicación).
6. **Bitácora inmutable y encadenada** (SHA-256 del registro anterior; trigger en PostgreSQL contra UPDATE/DELETE).
7. **Escrituras serializadas**: dependencia `escritura` (bloqueo asesor en PostgreSQL / candado en SQLite).
8. **Errores de negocio tipados** (`errores.py`): `Invalido/Conflicto/NoEncontrado/Prohibido`; la API los convierte en JSON.
9. **Sin dependencias en tiempo de ejecución fuera del servidor**: Tailwind compilado, Alpine y Chart.js locales. La CSP conserva
   `unsafe-eval`/`unsafe-inline` solo porque Alpine los necesita.
10. **Caché**: toda respuesta `/api/*` lleva `Cache-Control: no-store` y `Vary: Cookie` (salvo `/api/publico` y el logo versionado).

## Modelo organizacional y de permisos

| Tabla | Qué guarda |
|---|---|
| `unidades` | árbol `gerencia → departamento → jefatura` (`padre_id`, `ruta` materializada «/1/4/9/»; el subárbol es un prefijo de ruta) |
| `roles`, `rol_permisos` | roles (de sistema: `desarrollador`, `coordinador`) y su nivel por permiso del catálogo |
| `usuarios` | cuenta; `rol_id` nulo = pendiente de asignación; `ambito_raiz` = ámbito en toda la empresa |
| `usuario_unidades` | nodos de la persona: `ambito` (ve el nodo y lo que cuelga) o `miembro` (solo lo sitúa; el analista) |
| `indicadores` | ficha; `nodo_id` (cualquier nivel), `responsable_id`; `nivel_optimo` / `limite` (semáforo) |
| `indicador_cargadores` | quién carga cada indicador (1..n) |
| `metas`, `mediciones` | meta por período; carga real con foto de la ficha y de la meta vigentes |

**Visibilidad de un indicador** = su nodo está dentro de algún ámbito de la persona **o** es su responsable **o** es su cargador **o** la
persona tiene alcance global (Desarrollador, Coordinador SGC, ámbito en la raíz). Solo baja por el árbol. **Modificar** = ser su
responsable; **cargar** = ser su cargador (los roles de sistema, alcance total). **Crear / asignar / fijar metas** = a sí mismo o a
personas *debajo* (miembro de un nodo del ámbito, o con ámbito en un nodo inferior; los pares no están debajo).

**Aprobación:** aprobadores elegibles = personas con `cargas.aprobar` cuyo ámbito cubre el nodo del indicador; se toma el nivel más cercano
hacia arriba que tenga al menos uno distinto del autor (cualquiera de ese nivel aprueba) y se suman siempre los roles de sistema.

**Anti-escalada** (`servicios/roles.py`, `servicios/personas.py`): nadie edita su propio rol ni se asigna a sí mismo; nadie concede un permiso
(o nivel) que no tiene; los permisos técnicos no se conceden a ningún rol; el Coordinador no ve ni toca a un Desarrollador y solo un
Desarrollador da o quita el rol Coordinador; el rol Desarrollador es inmutable y se da/quita solo con el procedimiento explícito
(`POST /api/usuarios/{id}/desarrollador`, que reconfirma la contraseña); el sistema nunca queda sin Desarrollador activo.

## Calidad automatizada

`make verificar` ejecuta lo mismo que el CI (`.github/workflows/ci.yml`): ruff, pytest en SQLite **y** PostgreSQL 16, migraciones desde cero +
`alembic check`, CSS compilado al día y `pip-audit`. Despliegue: Vercel despliega la rama `master`; las migraciones se aplican al arrancar.

## Rendimiento
- **Una petición de arranque** (`GET /api/arranque`) entrega usuario con sus permisos, parámetros, ejercicios, indicadores que carga, nodos
  visibles, bandeja y resumen **solo si la persona tiene el permiso**; una cuenta sin rol recibe únicamente su perfil y la marca.
- **CDN**: estáticos con huella `s-maxage` de un año; HTML y `/api/publico` con `s-maxage` corto y `stale-while-revalidate`.
- **Interfaz**: sin `backdrop-filter`; animaciones de 0,18 s solo en opacidad/desplazamiento.
- **Base de datos**: listados sin consultas por fila; el número de consultas de las rutas calientes no crece con las filas.

## Plan gratuito (Vercel Hobby + Supabase Free): cómo se cuida

| Recurso gratuito | Riesgo | Medida |
|---|---|---|
| **Supabase: salida de datos (5 GB/mes)** | traer cosas pesadas en cada petición | El **logo** (base64, hasta ~800 KB) ya no viaja con los parámetros: antes se descargaba en cada arranque, cada 30 s por instancia y en la pantalla de ingreso. Solo se lee al servir `/api/logo` (con caché de 60 s en memoria y de un año en el navegador/CDN). |
| **Supabase: conexiones y latencia** | cada consulta es un viaje de red desde Vercel | Menos consultas por petición: «quién es y qué puede» pasó de 3 a 1–2 (el Desarrollador, 0 extra); el arranque bajó de 31 a 24 (Desarrollador), de 23 a 17 (gerente/jefe) y de 14 a 10 (gerente general). Con Vercel se usa `NullPool` + el *pooler* de Supabase (puerto 6543). |
| **Supabase: 500 MB de base** | crecimiento de la bitácora | Registros pequeños (JSON) y sin imágenes; el respaldo diario por GitHub Actions es externo y **mantiene activo el proyecto** (Supabase pausa los gratuitos tras 7 días sin actividad). |
| **Vercel: invocaciones y ancho de banda** | cada archivo estático despertaba la función | Estáticos con huella y `s-maxage` de un año (los sirve la CDN, no la función); HTML y `/api/publico` con `s-maxage` corto; gzip. |
| **Vercel: 10 s por función (Hobby)** | operaciones largas | Lo pesado (respaldo completo, restauración) se hace con la línea de comandos o el flujo de GitHub Actions, no con el botón, si la base crece. |
| **Memoria de la función** | cargar objetos completos «por si acaso» | `Medicion.notas`, `Indicador.responsable` e `Indicador.cargadores` ya no se traen siempre: se piden en bloque solo en las listas que los muestran. La bandeja decide qué le toca a cada persona con una consulta liviana (columnas sueltas) y solo carga completas las de la página pedida. |

Regla práctica: antes de agregar una pantalla o ruta, `tests/api/test_robustez.py` comprueba que el número de consultas no crezca con las filas.
