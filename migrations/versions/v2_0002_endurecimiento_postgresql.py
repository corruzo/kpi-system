"""Endurecimiento para PostgreSQL / Supabase: bitácora inmutable a nivel de motor, RLS en todas las tablas y retiro de
permisos a los roles públicos `anon` y `authenticated` (el único camino a los datos es esta aplicación).

En SQLite no hace nada. Si el rol de conexión no tiene permiso para alguna sentencia, se avisa y no se aborta
(ver `scripts/supabase_hardening.sql` para ejecutarlo a mano).

Revisión: v2_0002
Anterior: v2_0001
"""
import logging

import sqlalchemy as sa
from alembic import op

revision = "v2_0002"
down_revision = "v2_0001"
branch_labels = None
depends_on = None

log = logging.getLogger("alembic.runtime.migration")

TRIGGER = [
    """CREATE OR REPLACE FUNCTION public.bitacora_inmutable() RETURNS trigger AS $$
BEGIN RAISE EXCEPTION 'La bitácora es inalterable'; END; $$ LANGUAGE plpgsql SET search_path = ''""",
    "DROP TRIGGER IF EXISTS trg_bitacora_inmutable ON public.bitacora",
    """CREATE TRIGGER trg_bitacora_inmutable BEFORE UPDATE OR DELETE ON public.bitacora
FOR EACH ROW EXECUTE FUNCTION public.bitacora_inmutable()""",
]
REVOCAR = [
    "REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated",
    "REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated",
    "ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM anon, authenticated",
    "ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM anon, authenticated",
]


def _intentar(bind, sentencia: str) -> None:
    try:
        with bind.begin_nested():
            op.execute(sa.text(sentencia))
    except Exception as e:
        log.warning("No se pudo ejecutar «%s»: %s. Ejecute scripts/supabase_hardening.sql.", sentencia.splitlines()[0], e)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for s in TRIGGER:
        _intentar(bind, s)
    for tabla in sa.inspect(bind).get_table_names(schema="public"):
        _intentar(bind, f'ALTER TABLE public."{tabla}" ENABLE ROW LEVEL SECURITY')
    if bind.execute(sa.text("SELECT 1 FROM pg_roles WHERE rolname IN ('anon', 'authenticated')")).first():
        for s in REVOCAR:
            _intentar(bind, s)


def downgrade() -> None:
    # el endurecimiento se conserva a propósito: bajar de versión no debe reabrir la base
    pass
