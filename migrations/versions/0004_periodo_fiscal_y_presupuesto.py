"""Período fiscal explícito y presupuesto por indicador.

- `ejercicios`: quién y cuándo creó el período (ahora un período debe crearse antes de usarse).
- `presupuestos`: lo presupuestado por indicador y período de su frecuencia.
- `mediciones.presupuesto`: foto del presupuesto vigente al cargar el dato real.
- Los años que ya tenían cargas quedan como períodos creados y abiertos (nada se pierde ni se bloquea).

Revisión: 0004
Anterior: 0003
"""
import logging

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

log = logging.getLogger("alembic.runtime.migration")


def upgrade() -> None:
    with op.batch_alter_table("ejercicios") as lote:   # «batch»: SQLite no puede añadir una clave foránea con ALTER
        lote.add_column(sa.Column("creado_por_id", sa.Integer(), nullable=True))
        lote.add_column(sa.Column("creado_en", sa.DateTime(), nullable=True))
        lote.create_foreign_key("fk_ejercicios_creado_por", "usuarios", ["creado_por_id"], ["id"])
    op.add_column("mediciones", sa.Column("presupuesto", sa.Float(), nullable=True))
    op.create_table(
        "presupuestos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ejercicio", sa.Integer(), nullable=False),
        sa.Column("indicador_id", sa.Integer(), nullable=False),
        sa.Column("periodo", sa.String(length=10), nullable=False),
        sa.Column("valor", sa.Float(), nullable=False),
        sa.Column("actualizado_por_id", sa.Integer(), nullable=True),
        sa.Column("actualizado_en", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["ejercicio"], ["ejercicios.anio"]),
        sa.ForeignKeyConstraint(["indicador_id"], ["indicadores.id"]),
        sa.ForeignKeyConstraint(["actualizado_por_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("indicador_id", "periodo"),
    )
    op.create_index(op.f("ix_presupuestos_ejercicio"), "presupuestos", ["ejercicio"], unique=False)

    # Los ejercicios con cargas pasan a ser períodos creados (abiertos si no existía su fila).
    bind = op.get_bind()
    ejercicios = sa.table("ejercicios", sa.column("anio", sa.Integer), sa.column("estado", sa.String),
                          sa.column("creado_en", sa.DateTime))
    mediciones = sa.table("mediciones", sa.column("ejercicio", sa.Integer))
    existentes = set(bind.execute(sa.select(ejercicios.c.anio)).scalars())
    con_datos = {a for a in bind.execute(sa.select(mediciones.c.ejercicio).distinct()).scalars() if a}
    for anio in sorted(con_datos - existentes):
        bind.execute(ejercicios.insert().values(anio=anio, estado="abierto"))

    if bind.dialect.name == "postgresql":   # RLS sin políticas, como el resto de las tablas
        try:
            with bind.begin_nested():
                op.execute(sa.text('ALTER TABLE "presupuestos" ENABLE ROW LEVEL SECURITY'))
        except Exception as e:
            log.warning("No se pudo activar RLS en presupuestos: %s. Ejecute scripts/supabase_hardening.sql.", e)


def downgrade() -> None:
    op.drop_index(op.f("ix_presupuestos_ejercicio"), table_name="presupuestos")
    op.drop_table("presupuestos")
    op.drop_column("mediciones", "presupuesto")
    with op.batch_alter_table("ejercicios") as lote:
        lote.drop_constraint("fk_ejercicios_creado_por", type_="foreignkey")
        lote.drop_column("creado_en")
        lote.drop_column("creado_por_id")
