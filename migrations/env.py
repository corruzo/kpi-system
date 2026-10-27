"""Entorno de Alembic: usa el mismo motor y metadatos que la aplicación (app.database / app.models)."""
from alembic import context

from app import models  # noqa: F401  (registra las tablas en Base.metadata)
from app.database import DATABASE_URL, ES_POSTGRES, Base, engine

config = context.config
target_metadata = Base.metadata
ID_BLOQUEO_MIGRACION = 727002   # advisory lock: dos procesos nunca migran a la vez


def _configurar(**opciones):
    context.configure(target_metadata=target_metadata, compare_type=True, **opciones)


def migrar_sin_conexion() -> None:
    """`alembic upgrade head --sql`: genera el SQL sin conectarse."""
    _configurar(url=DATABASE_URL, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def migrar_con_conexion() -> None:
    with engine.connect() as conexion:
        _configurar(connection=conexion)
        with context.begin_transaction():
            if ES_POSTGRES:
                conexion.exec_driver_sql(f"SELECT pg_advisory_xact_lock({ID_BLOQUEO_MIGRACION})")
            context.run_migrations()


if context.is_offline_mode():
    migrar_sin_conexion()
else:
    migrar_con_conexion()
