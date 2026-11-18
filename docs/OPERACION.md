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
4. Actualice `SIGT_DATABASE_URL` y redespliegue (en Supabase, `alembic upgrade head` ya aplicó el endurecimiento: RLS, bitácora inalterable y sin permisos para `anon`/`authenticated`).
5. Use el **mismo `SIGT_SECRET`** (cifra la contraseña de los reportes); si cambió, redefínala en *Parámetros*.

## Incidentes frecuentes
| Síntoma | Qué hacer |
|---|---|
| Usuario bloqueado por intentos | Personas → *Desbloquear accesos* (Desarrollador) |
| Persona sospecha que otra usa su cuenta | Personas → Soporte → *Cerrar sus sesiones* + generar clave temporal (Desarrollador) |
| Alguien no ve un indicador | Es lo esperado si el nodo del indicador no está en su ámbito y no es su responsable ni su suplente: Personas → *Ver accesos* para comprobarlo; Indicadores → Editar → *Asignación* para corregirlo |
| No se puede inhabilitar/eliminar a una persona | Es responsable principal de indicadores: reasígnelos primero (Personas → *Indicadores*) |
| Cuenta nueva «pendiente de asignación» | El Coordinador SGC debe darle rol, ámbito e indicadores (Personas → *Rol y posición*) |
| Hay que cambiar lo que un rol puede hacer | Coordinador SGC → Roles y permisos; rige desde la siguiente petición de cada persona |
| «La cadena de la bitácora no es válida» | Detenga escrituras, conserve la base tal cual, restaure el último respaldo verificado en una base nueva y compare |

## Antes de cada despliegue
`make verificar` en verde (o el CI de GitHub), migración probada en una copia si cambia el esquema, y un respaldo reciente.

## Instalar la base desde cero o reiniciarla (producción)

**Destructivo e irreversible: lo ejecuta una persona autorizada, con la base correcta.** Sirve para la primera instalación o para
empezar de nuevo (por ejemplo, tras pruebas).

1. **Respaldo previo** (si hay algo que conservar): `SIGT_BACKUP_KEY='frase larga' python -m app.respaldar crear` con la base de producción
   (`SIGT_DATABASE_URL`), y `python -m app.respaldar verificar archivo.sigtbak`. Guárdelo fuera de GitHub y de Supabase.
2. **Detenga las escrituras** (en Vercel, pause el despliegue de producción si hay usuarios conectados).
3. En Supabase → SQL Editor, ejecute **`scripts/supabase_instalacion_completa.sql`** de una sola vez: borra el esquema `public` y crea todas las
   tablas, la bitácora inalterable, RLS, el retiro de permisos a `anon`/`authenticated` y deja `alembic_version` en la revisión actual.
   (Alternativa sin borrar nada: desplegar; con `VERCEL` definido las migraciones corren al arrancar y aplican el endurecimiento.)
4. **Primer Desarrollador:** defina `SIGT_ADMIN_USER` y `SIGT_ADMIN_PASSWORD` (10+ caracteres) y despliegue: con la base vacía el primer
   arranque lo crea y siembra los roles de sistema (Desarrollador y Coordinador SGC) y los parámetros. **Elimine `SIGT_ADMIN_PASSWORD`** del
   entorno y cambie la contraseña.
5. Siga *Puesta en marcha* en la aplicación: el Desarrollador crea las cuentas (incluido el Coordinador SGC, que se le asigna con
   Personas → *Rol y posición*); el Coordinador arma la estructura, los roles (con «Crear roles sugeridos» parte de los típicos, incluido
   *Calidad*) y asigna a cada persona su rol, su ámbito e indicadores.
6. Verifique: `alembic current` = `v2_0007`; `GET /healthz`; ingrese con una cuenta de cada rol y compruebe sus menús; haga un respaldo nuevo.

El script SQL se genera con `python scripts/generar_sql_supabase.py` y una prueba verifica que coincida con los modelos. Es el único script SQL del proyecto.
