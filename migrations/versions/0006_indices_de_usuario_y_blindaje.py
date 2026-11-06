"""Índices en las columnas que apuntan a usuarios y blindaje de la base en Supabase.

- Índices (todas las bases): las 8 llaves foráneas hacia `usuarios` (bitácora, cargas, notas, ejercicios, presupuestos). Sin ellos,
  consultar la actividad de un usuario o borrarlo recorre las tablas completas.
- PostgreSQL / Supabase (si el rol no tiene permiso, se avisa y no se aborta; ver scripts/supabase_hardening.sql):
  · RLS en `alembic_version` (estaba expuesta por la API pública de Supabase).
  · Se retiran a los roles públicos `anon` y `authenticated` todos los permisos sobre las tablas y secuencias del esquema
    `public`: la aplicación usa el rol `postgres` y nunca debe haber otro camino a los datos (defensa en profundidad: antes
    solo las frenaba la RLS sin políticas).
  · La función de la bitácora fija su `search_path`.

Revisión: 0006
Anterior: 0005
"""
import logging

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

log = logging.getLogger("alembic.runtime.migration")

INDICES = [
    ("ix_bitacora_usuario_id", "bitacora", ["usuario_id"]),
    ("ix_ejercicios_cerrado_por_id", "ejercicios", ["cerrado_por_id"]),
    ("ix_ejercicios_reabierto_por_id", "ejercicios", ["reabierto_por_id"]),
    ("ix_ejercicios_creado_por_id", "ejercicios", ["creado_por_id"]),
    ("ix_mediciones_cargado_por_id", "mediciones", ["cargado_por_id"]),
    ("ix_mediciones_revisado_por_id", "mediciones", ["revisado_por_id"]),
    ("ix_notas_auditoria_usuario_id", "notas_auditoria", ["usuario_id"]),
    ("ix_presupuestos_actualizado_por_id", "presupuestos", ["actualizado_por_id"]),
]

BLINDAJE = [
    'ALTER TABLE "alembic_version" ENABLE ROW LEVEL SECURITY',
    "ALTER FUNCTION public.bitacora_inmutable() SET search_path = ''",
    "REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated",
    "REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated",
    "ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM anon, authenticated",
    "ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM anon, authenticated",
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for nombre, tabla, columnas in INDICES:
        if nombre not in {i["name"] for i in inspector.get_indexes(tabla)}:
            op.create_index(nombre, tabla, columnas)
    if bind.dialect.name != "postgresql":
        return
    existen = set(bind.execute(sa.text("SELECT rolname FROM pg_roles WHERE rolname IN ('anon', 'authenticated')")).scalars())
    for sentencia in BLINDAJE:
        if ("anon" in sentencia) and not existen:
            continue                                   # base de PostgreSQL sin Supabase: esos roles no existen
        try:
            with bind.begin_nested():
                op.execute(sa.text(sentencia))
        except Exception as e:
            log.warning("No se pudo ejecutar «%s»: %s. Ejecute scripts/supabase_hardening.sql.", sentencia, e)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for nombre, tabla, _ in reversed(INDICES):
        if nombre in {i["name"] for i in inspector.get_indexes(tabla)}:
            op.drop_index(nombre, table_name=tabla)
    # el blindaje (RLS, permisos retirados) se conserva a propósito: bajar de versión no debe reabrir la base
