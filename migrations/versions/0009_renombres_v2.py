"""Renombres de la versión 2 (paso intermedio): «presupuesto» → «meta» y el umbral verde «meta» → «nivel óptimo».

Revisión: 0009
Anterior: 0008
"""
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_presupuestos_ejercicio", table_name="presupuestos")
    op.drop_index("ix_presupuestos_actualizado_por_id", table_name="presupuestos")
    with op.batch_alter_table("indicadores") as t:
        t.alter_column("meta", new_column_name="nivel_optimo")
        t.alter_column("meta_tope", new_column_name="nivel_optimo_tope")
    with op.batch_alter_table("mediciones") as t:
        t.alter_column("meta", new_column_name="nivel_optimo")
        t.alter_column("meta_tope", new_column_name="nivel_optimo_tope")
    with op.batch_alter_table("mediciones") as t:
        t.alter_column("presupuesto", new_column_name="meta")
    op.rename_table("presupuestos", "metas")
    op.create_index("ix_metas_ejercicio", "metas", ["ejercicio"])
    op.create_index("ix_metas_actualizado_por_id", "metas", ["actualizado_por_id"])


def downgrade() -> None:
    op.drop_index("ix_metas_ejercicio", table_name="metas")
    op.drop_index("ix_metas_actualizado_por_id", table_name="metas")
    op.rename_table("metas", "presupuestos")
    with op.batch_alter_table("mediciones") as t:
        t.alter_column("meta", new_column_name="presupuesto")
    with op.batch_alter_table("mediciones") as t:
        t.alter_column("nivel_optimo", new_column_name="meta")
        t.alter_column("nivel_optimo_tope", new_column_name="meta_tope")
    with op.batch_alter_table("indicadores") as t:
        t.alter_column("nivel_optimo", new_column_name="meta")
        t.alter_column("nivel_optimo_tope", new_column_name="meta_tope")
    op.create_index("ix_presupuestos_ejercicio", "presupuestos", ["ejercicio"])
    op.create_index("ix_presupuestos_actualizado_por_id", "presupuestos", ["actualizado_por_id"])
