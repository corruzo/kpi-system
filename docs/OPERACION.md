# Operación, respaldos y recuperación

## Objetivos
- **RPO** (datos que se pueden perder): ≤ 24 h con el respaldo diario; ≤ 1 min si se activa PITR de Supabase (plan Pro).
- **RTO** (tiempo para volver a operar): ≤ 1 h siguiendo el procedimiento de abajo.

## Capas de respaldo (use al menos las dos primeras)
1. **Respaldo cifrado del sistema** (`.sigtbak`): independiente del proveedor; se abre solo con su frase de paso.
   - Desde la aplicación: *Organización → Avanzado → Respaldo de la base de datos* (administrador): **Exportar** descarga el
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
| Usuario bloqueado por intentos | Organización → Equipo → *Desbloquear accesos* |
| Persona sospecha que otra usa su cuenta | Organización → Equipo → *Cerrar sesiones* + restablecer clave |
| Encargado no ve un indicador | Es lo esperado si no está asignado a él: Indicadores → Editar → *Encargado de proceso* |
| No se puede inhabilitar/eliminar un encargado | Tiene indicadores asignados: reasígnelos primero |
| «La cadena de la bitácora no es válida» | Detenga escrituras, conserve la base tal cual, restaure el último respaldo verificado en una base nueva y compare |

## Antes de cada despliegue
`make verificar` en verde (o el CI de GitHub), migración probada en una copia si cambia el esquema, y un respaldo reciente.
