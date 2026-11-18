# Seguridad, privacidad y rendimiento de SPE TPV

Documento técnico para auditoría interna y para la revisión legal. **No es asesoría jurídica**: lo legal depende de la ley aplicable a
la empresa y debe validarlo su asesor (ver «Lo que requiere una decisión de la empresa»).

## 1. Medidas técnicas (verificadas en el código y en pruebas)

| Área | Medida |
|---|---|
| Contraseñas | PBKDF2-HMAC-SHA256, **600 000 iteraciones** (mínimo recomendado por OWASP), sal única de 16 bytes, comparación en tiempo constante. Las iteraciones viajan dentro del hash: se pueden subir sin invalidar cuentas, y los hashes antiguos se actualizan solos al ingresar. Mínimo 10 caracteres. Tiempo de respuesta igual para usuario inexistente (no se pueden enumerar cuentas). |
| Sesión | Cookie `HttpOnly`, `Secure`, `SameSite=Strict`; firmada con HMAC-SHA256; caduca a las 10 h; se revoca al cambiar la clave, cerrar sesión o inhabilitar la cuenta. `SIGT_SECRET` obligatorio (32+ caracteres) en producción. |
| Fuerza bruta | Bloqueo de 15 min por pareja origen+usuario, por origen y por usuario; los contadores viven en la base (valen en todas las instancias) y guardan solo un hash SHA-256: no se almacenan IP ni usuarios en claro. |
| Autorización | Un solo motor (`servicios/acceso.py`): rol × árbol × asignación. Toda ruta declara su permiso; una prueba recorre **todas** las rutas × cada rol y falla si alguna queda sin declarar. Lo que no se ve responde 404; lo que se ve y no se puede hacer, 403. Anti-escalada de roles. |
| CSRF | Verificación de origen en toda petición que modifica datos, más `SameSite=Strict`. |
| Cabeceras | `Content-Security-Policy` (solo recursos propios y `frame-ancestors 'none'`), `Strict-Transport-Security` (1 año), `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `Permissions-Policy`, COOP/CORP. |
| XSS / inyección | Consultas con ORM y parámetros (sin SQL armado con datos del usuario); todo texto del usuario que se muestra como HTML pasa por `esc()`; la interfaz no carga recursos de terceros (tipografías y librerías son locales). |
| Archivos | Logo y planillas Excel con límites de tamaño; lectura de ZIP con protección contra bombas de descompresión. |
| Base de datos | RLS activo en todas las tablas y sin permisos para `anon`/`authenticated` de Supabase; bitácora **inalterable** (trigger del motor) y encadenada con SHA-256 (verificable desde la interfaz). |
| Auditoría | Bitácora de ingresos, cargas, revisiones, cambios de ficha, metas, asignaciones, roles, cierres y justificaciones; historial por indicador y de cada devolución. |
| Respaldo | Cifrado (Fernet, clave derivada con 600 000 iteraciones), verificable, diario con GitHub Actions (artefacto privado, 30 días). Restauración todo-o-nada. |
| Dependencias | `pip-audit` y `npm audit` sin vulnerabilidades conocidas al momento de escribir esto (`make auditar` las repite). |
| Pruebas | Más de 300 automáticas (seguridad, permisos, migraciones, SQL de instalación, N+1) y verificación en PostgreSQL real. |

## 2. Rendimiento (medido en modo producción, red local)

- Página de ingreso: primer pintado ≈ 140 ms, 36 peticiones, **HTML 224 KB → 49 KB** con gzip; CSS 59 KB → 10 KB; Chart.js (200 KB) solo se descarga al abrir un gráfico.
- Scripts, estilos y tipografías versionados por huella con caché de **1 año** (`immutable`): la segunda visita casi no descarga nada.
- API con 60 indicadores: arranque 47 ms; listas paginadas 10–15 ms; panel 29 ms; tablero 35 ms (mediana).
- Reporte Excel general (60 indicadores): **4 s → 1 s** tras corregir un cálculo cuadrático en el ajuste de columnas. Con cientos de indicadores seguirá creciendo de forma lineal; en Vercel Hobby el límite por función es corto, vigílelo.
- Sin N+1 (pruebas de consultas), listas paginadas en el servidor, conexiones sin pool en serverless con el *transaction pooler* de Supabase.
- En producción influye la **región**: ponga el proyecto de Supabase y el despliegue de Vercel en la misma región (no verificable desde el código).

## 3. Datos personales que trata el sistema

| Dato | Dónde | Quién lo ve | Conservación |
|---|---|---|---|
| Nombre, usuario, correo (opcional) | `usuarios` | Quien tenga «Ver personas» (solo su rama) | Mientras exista la cuenta; con actividad solo se **inhabilita** (para no romper la trazabilidad) |
| Hash de contraseña | `usuarios` | Nadie (no se muestra ni se exporta) | Hasta que cambie |
| Quién hizo qué y cuándo | `bitacora`, `revisiones`, `mediciones`, `notificaciones` | Según permiso (la bitácora completa, solo el Desarrollador) | La bitácora es permanente por diseño (auditoría) |
| Contadores de intentos fallidos | `intentos_fallidos` (hash SHA-256) | Nadie | Ventana de 15 min |
| Sesión | Cookie del navegador | La propia persona | 10 h |
| Respaldos | Archivo cifrado | Quien tenga la frase de paso | 30 días en GitHub; el resto lo decide la empresa |

No hay analítica, publicidad, cookies de terceros ni envío de datos a terceros desde la interfaz. Proveedores que alojan los datos: **Supabase** (base) y **Vercel** (aplicación) y **GitHub** (respaldos).

## 4. Brechas conocidas y mejoras recomendadas (por prioridad)

1. **Autenticación en dos pasos (2FA)**: no existe. Recomendable al menos para Desarrollador y Coordinador SGC.
2. **CSP con `unsafe-inline` y `unsafe-eval`**: Alpine.js en su versión estándar lo exige. Se mitiga con el escape sistemático de texto, pero lo ideal es migrar a la versión «CSP» de Alpine y mover los scripts en línea (cambio grande de interfaz).
3. **Usuario de base de datos**: la aplicación se conecta como `postgres`, que ignora RLS. Lo más seguro es un rol propio con solo los permisos necesarios.
4. **Límite de peticiones general** (más allá del ingreso): no hay; delegarlo en el firewall/WAF de la plataforma.
5. **Monitoreo y alertas**: existe el panel de salud para el Desarrollador; no hay alertas externas (correo/Slack) ni registro centralizado.
6. **Prueba de restauración periódica** del respaldo (el archivo se verifica, pero conviene restaurarlo en un entorno de prueba cada cierto tiempo) y copia fuera de GitHub/Supabase.
7. **Accesibilidad** (WCAG): hay etiquetas, roles y foco, pero no se ha auditado con lectores de pantalla.

## 5. Lo que requiere una decisión de la empresa (no lo resuelve el código)

- **Marco legal aplicable y aviso de privacidad.** El sistema no incluye aviso de privacidad ni términos de uso; deben redactarse con su asesor legal según la normativa vigente de protección de datos y laboral del país, e informarse a quienes tengan cuenta.
- **Política de retención y de ejercicio de derechos** (acceso, rectificación, supresión). La bitácora es inalterable por diseño: defina con su asesor qué datos personales pueden anonimizarse y cuáles deben conservarse como registro de calidad.
- **Responsable del tratamiento y procedimiento ante incidentes** (quién avisa a quién y en qué plazo).
- **Contratos con proveedores** (Supabase, Vercel, GitHub) y ubicación de los datos.
- **Política de contraseñas/2FA y de altas y bajas de cuentas** (inhabilitar de inmediato a quien deje la empresa).
- **ISO 9001:2015**: el sistema da trazabilidad (versiones de carga, aprobación, historial de cambios, cierre inalterable del ejercicio) y soporta los requisitos 7.5 (información documentada), 9.1.3 (análisis y evaluación) y 10.2 (acciones correctivas), pero la certificación evalúa el proceso de la organización, no solo la herramienta.

## 6. Licencias de terceros

Alpine.js, Chart.js, Motion y Tailwind CSS: MIT. Tipografía Manrope: SIL OFL 1.1. Los avisos de licencia están en `app/static/vendor/` y `app/static/fonts/`. Las dependencias de Python y npm tienen licencias permisivas (MIT/BSD/Apache); revíselas con `pip-licenses` si necesita un inventario formal.
