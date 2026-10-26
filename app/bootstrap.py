"""Preparación de la base en el arranque: tablas, endurecimiento en Postgres y primer administrador."""
import logging
import os

from sqlalchemy import func, inspect, select, text

from . import audit
from .database import ES_POSTGRES, Base, SessionLocal, engine
from .models import Usuario
from .security import hash_password

log = logging.getLogger("sigt")

_TRIGGER = """
CREATE OR REPLACE FUNCTION bitacora_inmutable() RETURNS trigger AS $$
BEGIN RAISE EXCEPTION 'La bitácora es inalterable'; END; $$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trg_bitacora_inmutable ON bitacora;
CREATE TRIGGER trg_bitacora_inmutable BEFORE UPDATE OR DELETE ON bitacora
FOR EACH ROW EXECUTE FUNCTION bitacora_inmutable();
"""


def migrar() -> None:
    """Migración aditiva: agrega a tablas existentes las columnas nuevas del modelo (sin perder datos)."""
    insp = inspect(engine)
    for tabla in Base.metadata.sorted_tables:
        if not insp.has_table(tabla.name):
            continue
        existentes = {c["name"] for c in insp.get_columns(tabla.name)}
        for col in tabla.columns:
            if col.name not in existentes:
                tipo = col.type.compile(dialect=engine.dialect)
                with engine.begin() as cx:
                    cx.execute(text(f'ALTER TABLE "{tabla.name}" ADD COLUMN "{col.name}" {tipo}'))
                log.warning("Migración: columna %s.%s agregada.", tabla.name, col.name)


def preparar_base() -> None:
    Base.metadata.create_all(engine)
    migrar()
    if not ES_POSTGRES:
        return
    try:
        with engine.begin() as cx:
            cx.execute(text(_TRIGGER))
            for t in Base.metadata.tables:  # bloquea el acceso directo vía API REST pública de Supabase
                cx.execute(text(f'ALTER TABLE "{t}" ENABLE ROW LEVEL SECURITY'))
    except Exception as e:  # permisos insuficientes, etc.
        log.warning("No se pudo endurecer la base (trigger/RLS): %s. Ejecute scripts/supabase_hardening.sql.", e)


def crear_admin(username: str, nombre: str, password: str) -> Usuario:
    with SessionLocal() as db:
        u = Usuario(username=username.lower(), nombre=nombre, rol="admin",
                    password_hash=hash_password(password))
        db.add(u)
        db.flush()
        audit.registrar(db, u, "USUARIO_CREADO", "usuario", u.id,
                        {"username": u.username, "rol": "admin", "origen": "bootstrap"})
        db.commit()
        return u


def bootstrap_admin() -> None:
    with SessionLocal() as db:
        if db.scalar(select(func.count(Usuario.id))):
            return
    user, pwd = os.getenv("SIGT_ADMIN_USER"), os.getenv("SIGT_ADMIN_PASSWORD")
    if not (user and pwd):
        log.warning("Base vacía: defina SIGT_ADMIN_USER y SIGT_ADMIN_PASSWORD para crear el primer "
                    "administrador, o ejecute «python -m app.crear_admin».")
        return
    if len(pwd) < 10:
        raise RuntimeError("SIGT_ADMIN_PASSWORD debe tener al menos 10 caracteres.")
    crear_admin(user, os.getenv("SIGT_ADMIN_NAME", "Administrador SGC"), pwd)
    log.warning("Primer administrador «%s» creado. Elimine SIGT_ADMIN_PASSWORD del entorno.", user)
