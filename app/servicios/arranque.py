"""Arranque del sistema: tablas, migración aditiva, endurecimiento en PostgreSQL y primer administrador.

`iniciar()` se ejecuta una sola vez por proceso (en serverless puede invocarse desde la primera petición).
"""
import logging
import os
import threading

from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import OperationalError

from .. import security
from ..database import ES_POSTGRES, Base, SessionLocal, engine
from ..models import Usuario
from . import auditoria, ejercicios, parametros

log = logging.getLogger("sigt")
_candado = threading.Lock()
_iniciado = False

_TRIGGER_BITACORA = """
CREATE OR REPLACE FUNCTION bitacora_inmutable() RETURNS trigger AS $$
BEGIN RAISE EXCEPTION 'La bitácora es inalterable'; END; $$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trg_bitacora_inmutable ON bitacora;
CREATE TRIGGER trg_bitacora_inmutable BEFORE UPDATE OR DELETE ON bitacora
FOR EACH ROW EXECUTE FUNCTION bitacora_inmutable();
"""


# ---------------------------------------------------------------- base de datos
def migrar() -> None:
    """Migración aditiva: agrega a las tablas existentes las columnas nuevas del modelo (sin perder datos)."""
    inspector = inspect(engine)
    for tabla in Base.metadata.sorted_tables:
        if not inspector.has_table(tabla.name):
            continue
        existentes = {c["name"] for c in inspector.get_columns(tabla.name)}
        for columna in tabla.columns:
            if columna.name not in existentes:
                tipo = columna.type.compile(dialect=engine.dialect)
                with engine.begin() as cx:
                    cx.execute(text(f'ALTER TABLE "{tabla.name}" ADD COLUMN "{columna.name}" {tipo}'))
                log.warning("Migración: columna %s.%s agregada.", tabla.name, columna.name)


def _endurecer_postgres() -> None:
    """Bitácora inalterable a nivel de motor y RLS sin políticas (la API REST pública de Supabase queda sin acceso)."""
    try:
        with engine.begin() as cx:
            cx.execute(text(_TRIGGER_BITACORA))
            for tabla in Base.metadata.tables:
                cx.execute(text(f'ALTER TABLE "{tabla}" ENABLE ROW LEVEL SECURITY'))
    except Exception as e:  # permisos insuficientes, etc.
        log.warning("No se pudo endurecer la base (trigger/RLS): %s. Ejecute scripts/supabase_hardening.sql.", e)


def preparar_base() -> None:
    Base.metadata.create_all(engine)
    migrar()
    if ES_POSTGRES:
        _endurecer_postgres()


# ---------------------------------------------------------------- primer administrador
def crear_admin(username: str, nombre: str, password: str) -> Usuario:
    with SessionLocal() as db:
        u = Usuario(username=username.lower(), nombre=nombre, rol="admin", password_hash=security.hash_password(password))
        db.add(u)
        db.flush()
        auditoria.registrar(db, u, "USUARIO_CREADO", "usuario", u.id, {"username": u.username, "rol": "admin", "origen": "bootstrap"})
        db.commit()
        return u


def crear_admin_inicial() -> None:
    """Con la base vacía, crea el administrador definido en SIGT_ADMIN_USER / SIGT_ADMIN_PASSWORD."""
    with SessionLocal() as db:
        if db.scalar(select(func.count(Usuario.id))):
            return
    usuario, clave = os.getenv("SIGT_ADMIN_USER"), os.getenv("SIGT_ADMIN_PASSWORD")
    if not (usuario and clave):
        log.warning("Base vacía: defina SIGT_ADMIN_USER y SIGT_ADMIN_PASSWORD para crear el primer administrador, "
                    "o ejecute «python -m app.crear_admin».")
        return
    if len(clave) < 10:
        raise RuntimeError("SIGT_ADMIN_PASSWORD debe tener al menos 10 caracteres.")
    crear_admin(usuario, os.getenv("SIGT_ADMIN_NAME", "Administrador SGC"), clave)
    log.warning("Primer administrador «%s» creado. Elimine SIGT_ADMIN_PASSWORD del entorno.", usuario)


# ---------------------------------------------------------------- orquestación
def iniciar() -> None:
    """Deja el sistema listo: tablas → administrador → parámetros → calendario fiscal → ejercicio de cada medición."""
    global _iniciado
    with _candado:
        if _iniciado:
            return
        preparar_base()
        crear_admin_inicial()
        with SessionLocal() as db:
            parametros.crear_faltantes(db)
        parametros.refrescar(forzar=True)
        with SessionLocal() as db:
            ejercicios.recalcular(db)
        _iniciado = True


def esta_iniciado() -> bool:
    return _iniciado


def motivo_del_fallo(e: Exception) -> str:
    """Motivo legible sin exponer credenciales: solo la primera línea del error del driver."""
    if isinstance(e, (OperationalError, RuntimeError)):
        linea = (str(getattr(e, "orig", None) or e).strip().splitlines() or [""])[0]
        return f"{type(e).__name__}: {linea[:300]}"
    return f"{type(e).__name__} (vea los logs del servidor para el detalle)"
