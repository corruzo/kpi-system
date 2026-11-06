"""Cada indicador tiene UN encargado de proceso (aislamiento estricto de datos entre usuarios).

Antes un usuario con rol de encargado veía todos los indicadores de su área; ahora solo ve los que se le asignan
(`indicadores.encargado_id`). Para no dejar a nadie sin acceso al actualizar, los indicadores de un área que tiene
EXACTAMENTE un encargado activo se le asignan a él; los de áreas con varios o ninguno quedan sin encargado y el
administrador debe asignarlos (mientras tanto, solo admin y gerente los ven).

Revisión: 0007
Anterior: 0006
"""
import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("indicadores") as lote:
        lote.add_column(sa.Column("encargado_id", sa.Integer(), nullable=True))
        lote.create_foreign_key("fk_indicadores_encargado", "usuarios", ["encargado_id"], ["id"])
        lote.create_index("ix_indicadores_encargado_id", ["encargado_id"])
    op.execute("""
        UPDATE indicadores SET encargado_id = (
            SELECT MIN(u.id) FROM usuarios u WHERE u.rol = 'jefe' AND u.activo AND u.area_id = indicadores.area_id)
        WHERE (SELECT COUNT(*) FROM usuarios u WHERE u.rol = 'jefe' AND u.activo AND u.area_id = indicadores.area_id) = 1
    """)


def downgrade() -> None:
    with op.batch_alter_table("indicadores") as lote:
        lote.drop_index("ix_indicadores_encargado_id")
        lote.drop_constraint("fk_indicadores_encargado", type_="foreignkey")
        lote.drop_column("encargado_id")
