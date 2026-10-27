"""Cifra la contraseña de los reportes (`parametros.clave_reportes`), que se guardaba en texto plano.

Usa una clave derivada de SIGT_SECRET (app/cifrado.py): hay que ejecutar la migración con la misma SIGT_SECRET de la app.

Revisión: 0003
Anterior: 0002
"""
import sqlalchemy as sa
from alembic import op

from app import cifrado

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

parametros = sa.table("parametros", sa.column("clave", sa.String), sa.column("valor", sa.Text))


def _transformar(convertir) -> None:
    bind = op.get_bind()
    valor = bind.execute(sa.select(parametros.c.valor).where(parametros.c.clave == "clave_reportes")).scalar()
    if valor:
        nuevo = convertir(valor)
        if nuevo != valor:
            bind.execute(parametros.update().where(parametros.c.clave == "clave_reportes").values(valor=nuevo))


def upgrade() -> None:
    _transformar(lambda v: v if cifrado.esta_cifrado(v) else cifrado.cifrar(v))


def downgrade() -> None:
    _transformar(lambda v: cifrado.descifrar(v) if cifrado.esta_cifrado(v) else v)
