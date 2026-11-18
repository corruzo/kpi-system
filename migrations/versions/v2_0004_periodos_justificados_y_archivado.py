"""Cierre fiscal estricto: períodos justificados y fecha de archivado de los indicadores.

- `periodos_justificados`: un período que no se carga por una razón formal (parada de planta, el indicador empezó a medirse
  después, no aplica). Cuenta como cubierto para el cierre del ejercicio.
- `indicadores.archivado_en`: desde cuándo un indicador está archivado; los períodos posteriores no se le exigen. Los ya
  archivados toman la fecha de su registro en la bitácora (o la de esta migración si no la hay).

Revisión: v2_0004
Anterior: v2_0003
"""
import logging

import sqlalchemy as sa
from alembic import op

revision = "v2_0004"
down_revision = "v2_0003"
branch_labels = None
depends_on = None

log = logging.getLogger("alembic.runtime.migration")


def upgrade() -> None:
    op.add_column("indicadores", sa.Column("archivado_en", sa.DateTime(), nullable=True))
    op.execute(sa.text(
        "UPDATE indicadores SET archivado_en = COALESCE((SELECT MAX(b.fecha) FROM bitacora b WHERE b.indicador_id = indicadores.id "
        "AND b.accion = 'INDICADOR_ARCHIVADO'), CURRENT_TIMESTAMP) WHERE activo = :inactivo").bindparams(inactivo=False))
    op.create_table(
        "periodos_justificados",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("indicador_id", sa.Integer(), nullable=False),
        sa.Column("periodo", sa.String(length=10), nullable=False),
        sa.Column("ejercicio", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.Column("por_id", sa.Integer(), nullable=False),
        sa.Column("en", sa.DateTime(), nullable=False),
        sa.CheckConstraint("tipo IN ('parada_planta', 'inicio_medicion', 'no_aplica')", name="ck_periodos_justificados_tipo"),
        sa.ForeignKeyConstraint(["indicador_id"], ["indicadores.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["por_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("indicador_id", "periodo"),
    )
    op.create_index(op.f("ix_periodos_justificados_ejercicio"), "periodos_justificados", ["ejercicio"])
    op.create_index(op.f("ix_periodos_justificados_por_id"), "periodos_justificados", ["por_id"])
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":   # igual que el resto de tablas (v2_0002): sin acceso por la API pública de Supabase
        try:
            with bind.begin_nested():
                op.execute(sa.text('ALTER TABLE public."periodos_justificados" ENABLE ROW LEVEL SECURITY'))
        except Exception as e:
            log.warning("No se pudo activar RLS en periodos_justificados: %s. Actívelo a mano: ALTER TABLE public.<tabla> ENABLE ROW LEVEL SECURITY.", e)


def downgrade() -> None:
    op.drop_table("periodos_justificados")
    op.drop_column("indicadores", "archivado_en")
