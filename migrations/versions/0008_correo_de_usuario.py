"""Correo electrónico (opcional) de cada usuario, para enviarle recordatorios de carga desde Outlook.

Revisión: 0008
Anterior: 0007
"""
import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("usuarios", sa.Column("email", sa.String(length=120), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("usuarios") as lote:
        lote.drop_column("email")
