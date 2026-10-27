"""Migraciones del esquema con Alembic: aplicar, o comprobar que la base está al día.

El arranque de la aplicación nunca altera el esquema por su cuenta salvo en desarrollo (o con SIGT_AUTO_MIGRATE=1).
En producción lo normal es migrar en el despliegue (`alembic upgrade head`) y que la aplicación solo lo verifique.
"""
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory

from ..database import BASE_DIR, engine


def configuracion() -> Config:
    cfg = Config(str(BASE_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BASE_DIR / "migrations"))   # ruta absoluta: no depende del cwd
    return cfg


def revision_cabeza() -> str:
    return ScriptDirectory.from_config(configuracion()).get_current_head()


def revision_actual() -> str | None:
    with engine.connect() as cx:
        return MigrationContext.configure(cx).get_current_revision()


def esta_al_dia() -> bool:
    return revision_actual() == revision_cabeza()


def actualizar() -> None:
    command.upgrade(configuracion(), "head")


def exigir_al_dia() -> None:
    if not esta_al_dia():
        raise RuntimeError(f"La base de datos no está actualizada (revisión {revision_actual() or 'ninguna'}; se esperaba "
                           f"{revision_cabeza()}). Ejecute «alembic upgrade head» o defina SIGT_AUTO_MIGRATE=1.")
