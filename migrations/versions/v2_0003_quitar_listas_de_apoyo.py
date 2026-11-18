"""Quita las «listas de apoyo» de la ficha (tabla `catalogos`) y su permiso `catalogos.gestionar`.

Los campos de la ficha (proceso, objetivo, gerencia, líder) siguen existiendo como texto libre en cada indicador: lo único
que desaparece es la lista maestra que los sugería. Las fichas conservan el texto copiado, así que no se pierde ningún dato.

Revisión: v2_0003
Anterior: v2_0002
"""
import sqlalchemy as sa
from alembic import op

revision = "v2_0003"
down_revision = "v2_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # el permiso deja de existir en el catálogo: se retira de los roles que lo tenían
    op.execute(sa.text("DELETE FROM rol_permisos WHERE permiso = 'catalogos.gestionar'"))
    op.drop_table("catalogos")


def downgrade() -> None:
    op.create_table(
        "catalogos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("valor", sa.String(length=300), nullable=False),
        sa.Column("detalle", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tipo", "valor"),
    )
