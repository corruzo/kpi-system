"""Notificaciones: avisos a quien carga cuando su carga es aprobada, devuelta (con el motivo) o reabierta.

El aviso de «cierre de mes cercano con cargas pendientes» no se guarda: se calcula al consultar.

Revisión: v2_0007
Anterior: v2_0006
"""
import logging

import sqlalchemy as sa
from alembic import op

revision = "v2_0007"
down_revision = "v2_0006"
branch_labels = None
depends_on = None

log = logging.getLogger("alembic.runtime.migration")


def upgrade() -> None:
    op.create_table(
        "notificaciones",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(length=10), nullable=False),
        sa.Column("titulo", sa.String(length=160), nullable=False),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("indicador_id", sa.Integer(), nullable=True),
        sa.Column("periodo", sa.String(length=10), nullable=True),
        sa.Column("creada_en", sa.DateTime(), nullable=False),
        sa.Column("leida_en", sa.DateTime(), nullable=True),
        sa.CheckConstraint("tipo IN ('aprobada', 'devuelta', 'reabierta')", name="ck_notificaciones_tipo"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["indicador_id"], ["indicadores.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notificaciones_usuario_id"), "notificaciones", ["usuario_id"])
    op.create_index(op.f("ix_notificaciones_indicador_id"), "notificaciones", ["indicador_id"])
    op.create_index(op.f("ix_notificaciones_creada_en"), "notificaciones", ["creada_en"])
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":   # igual que el resto de tablas (v2_0002): sin acceso por la API pública de Supabase
        try:
            with bind.begin_nested():
                op.execute(sa.text('ALTER TABLE public."notificaciones" ENABLE ROW LEVEL SECURITY'))
        except Exception as e:
            log.warning("No se pudo activar RLS en notificaciones: %s. Actívelo a mano: ALTER TABLE public.<tabla> ENABLE ROW LEVEL SECURITY.", e)


def downgrade() -> None:
    op.drop_table("notificaciones")
