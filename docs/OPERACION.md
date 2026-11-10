# Operación, respaldos y recuperación

## Objetivos
- **RPO** (datos que se pueden perder): ≤ 24 h con el respaldo diario; ≤ 1 min si se activa PITR de Supabase (plan Pro).
- **RTO** (tiempo para volver a operar): ≤ 1 h siguiendo el procedimiento de abajo.

## Capas de respaldo (use al menos las dos primeras)
1. **Respaldo cifrado del sistema** (`.sigtbak`): independiente del proveedor; se abre solo con su frase de paso.
   - Desde la aplicación: *Configuración → Avanzado → Respaldo de la base de datos* (Desarrollador): **Exportar** descarga el
     archivo cifrado e **Importar** lo restaura reemplazando todos los datos (pide la frase del respaldo, su contraseña y escribir
     RESTAURAR; es todo-o-nada y obliga a volver a ingresar).
   - Automático: `.github/workflows/respaldo.yml` (diario 07:17 UTC). Cree los secretos `SIGT_DATABASE_URL` y `SIGT_BACKUP_KEY`
     en GitHub → Settings → Secrets → Actions. El archivo queda 30 días como artefacto privado:
     **descárguelo periódicamente y guárdelo fuera de GitHub y de Supabase** (otra nube o disco cifrado).
   - Manual: `SIGT_BACKUP_KEY='frase larga' python -m app.respaldar crear` · `… verificar archivo.sigtbak`.
2. **Respaldos de Supabase** (Dashboard → Database → Backups): diarios en planes de pago; PITR opcional.
3. **Guarde la frase de paso en un gestor de contraseñas distinto al de las credenciales de la base.** Sin ella, el respaldo
   es irrecuperable (a propósito: contiene hashes de contraseñas y toda la bitácora).

## Verificación periódica (una vez al mes)
`python -m app.respaldar verificar <archivo>` confirma frase, integridad por tabla y estado de la cadena de la bitácora.
Un respaldo que nunca se verificó no es un respaldo. Haga una restauración de prueba trimestral (abajo, en una base nueva).

## Restaurar (desastre o migración de servidor)
1. Cree una base PostgreSQL **vacía** (nuevo proyecto de Supabase o base local).
2. Con las variables del nuevo entorno **sin** `SIGT_ADMIN_PASSWORD`: `alembic upgrade head` (debe quedar en la misma
   revisión del respaldo; `verificar` la muestra).
3. `SIGT_BACKUP_KEY='…' python -m app.respaldar restaurar archivo.sigtbak`. Es todo-o-nada: revierte si algún conteo o la
   cadena de la bitácora no coincide. Se niega a escribir en una base con datos.
4. Aplique `scripts/supabase_hardening.sql` si es Supabase, actualice `SIGT_DATABASE_URL` y redespliegue.
5. Use el **mismo `SIGT_SECRET`** (cifra la contraseña de los reportes); si cambió, redefínala en *Parámetros*.

## Incidentes frecuentes
| Síntoma | Qué hacer |
|---|---|
| Usuario bloqueado por intentos | Personas → *Desbloquear accesos* (Desarrollador) |
| Persona sospecha que otra usa su cuenta | Personas → Soporte → *Cerrar sus sesiones* + generar clave temporal (Desarrollador) |
| Alguien no ve un indicador | Es lo esperado si el nodo del indicador no está en su ámbito y no es su responsable ni su cargador: Personas → *¿Qué ve?* para comprobarlo; Indicadores → Editar → *Asignación* para corregirlo |
| No se puede inhabilitar/eliminar a una persona | Es responsable de indicadores o su única cargadora: reasígnelos primero (Personas → *Indicadores*) |
| Cuenta nueva «pendiente de asignación» | El Coordinador SGC debe darle rol, ámbito e indicadores (Personas → *Rol y posición*) |
| Hay que cambiar lo que un rol puede hacer | Coordinador SGC → Roles y permisos; rige desde la siguiente petición de cada persona |
| «La cadena de la bitácora no es válida» | Detenga escrituras, conserve la base tal cual, restaure el último respaldo verificado en una base nueva y compare |

## Antes de cada despliegue
`make verificar` en verde (o el CI de GitHub), migración probada en una copia si cambia el esquema, y un respaldo reciente.

## Reinicio a la versión 2 (producción)

La versión 2 cambia el esquema por completo (estructura en árbol, roles y permisos, metas). Los datos de la versión 1 eran de prueba y
**se eliminan**: no hay migración de usuarios ni de indicadores. **Este procedimiento es destructivo e irreversible; no se ejecutó desde el
desarrollo: lo ejecuta una persona autorizada.**

1. **Respaldo previo** (por si acaso): `SIGT_BACKUP_KEY='frase larga' python -m app.respaldar crear` con la base de producción
   (`SIGT_DATABASE_URL`), y `python -m app.respaldar verificar archivo.sigtbak`. Guárdelo fuera de GitHub y de Supabase.
2. **Detenga las escrituras** (no hay nada que hacer si nadie usa el sistema; en Vercel, pause el despliegue de producción).
3. En Supabase → SQL Editor, ejecute **`scripts/reset_produccion_v2.sql`**: borra el esquema `public` completo (tablas, datos, bitácora y
   `alembic_version`) y lo recrea vacío. Confirme antes que está en el proyecto correcto.
4. **Despliegue** de la rama de la versión 2 en producción (la autorización para subirla a `master` la da el responsable del proyecto).
   Con `VERCEL` definido las migraciones corren al arrancar y crean el esquema (`v2_0001`) y el endurecimiento (`v2_0002`: trigger de la
   bitácora, RLS y retiro de permisos a `anon`/`authenticated`). Si el rol de conexión no pudo aplicar el endurecimiento, la migración lo avisa
   en el log: ejecute `scripts/supabase_hardening.sql` a mano (es idempotente).
5. **Primer Desarrollador:** con `SIGT_ADMIN_USER` y `SIGT_ADMIN_PASSWORD` definidos y la base vacía, el primer arranque crea al Desarrollador
   y siembra los roles de sistema (Desarrollador y Coordinador SGC). **Elimine `SIGT_ADMIN_PASSWORD`** del entorno y cambie la contraseña.
6. Siga *Puesta en marcha* en la aplicación: el Desarrollador crea las cuentas (incluido el Coordinador SGC, que se le asigna con
   Personas → *Rol y posición*); el Coordinador arma la estructura, los roles y asigna a cada persona su rol, su ámbito e indicadores.
7. Verifique: `alembic current` = `v2_0002`; `GET /healthz`; ingrese con una cuenta de cada rol y compruebe sus menús; haga un respaldo nuevo.
