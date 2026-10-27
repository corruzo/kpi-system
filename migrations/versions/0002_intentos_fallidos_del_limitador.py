"""Tabla `intentos_fallidos`: contadores del limitador de intentos compartidos entre procesos.

Revisión: 0002
Anterior: 0001
"""
import logging

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

log = logging.getLogger("alembic.runtime.migration")


def upgrade() -> None:
    op.create_table(
        "intentos_fallidos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("llave", sa.String(length=64), nullable=False),
        sa.Column("fecha", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_intentos_fallidos_fecha"), "intentos_fallidos", ["fecha"], unique=False)
    op.create_index("ix_intentos_fallidos_llave_fecha", "intentos_fallidos", ["llave", "fecha"], unique=False)
    if op.get_bind().dialect.name == "postgresql":   # RLS sin políticas, como el resto de las tablas
        try:
            with op.get_bind().begin_nested():
                op.execute(sa.text('ALTER TABLE "intentos_fallidos" ENABLE ROW LEVEL SECURITY'))
        except Exception as e:
            log.warning("No se pudo activar RLS en intentos_fallidos: %s. Ejecute scripts/supabase_hardening.sql.", e)


def downgrade() -> None:
    op.drop_index("ix_intentos_fallidos_llave_fecha", table_name="intentos_fallidos")
    op.drop_index(op.f("ix_intentos_fallidos_fecha"), table_name="intentos_fallidos")
    op.drop_table("intentos_fallidos")
