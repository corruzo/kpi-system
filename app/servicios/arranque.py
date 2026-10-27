"""Arranque del sistema: esquema al día (Alembic), primer administrador, parámetros y calendario fiscal.

`iniciar()` se ejecuta una sola vez por proceso (en serverless puede invocarse desde la primera petición).
"""
import logging
import os
import threading

from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError

from .. import security
from ..config import PRODUCCION
from ..database import SessionLocal
from ..models import Usuario
from . import auditoria, ejercicios, migraciones, parametros

log = logging.getLogger("sigt")
_candado = threading.Lock()
_iniciado = False


# ---------------------------------------------------------------- base de datos
def migrar_automaticamente() -> bool:
    """¿Debe este proceso aplicar las migraciones al arrancar? Sí en desarrollo y en Vercel (no tiene paso de despliegue donde
    migrar); en el resto de producción solo con SIGT_AUTO_MIGRATE=1 (lo normal es migrar en el despliegue y que la
    aplicación únicamente verifique). SIGT_AUTO_MIGRATE=0 lo desactiva siempre."""
    por_defecto = "1" if (not PRODUCCION or os.getenv("VERCEL")) else "0"
    return os.getenv("SIGT_AUTO_MIGRATE", por_defecto) == "1"


def preparar_base() -> None:
    """Esquema al día vía Alembic (aplicándolo o exigiéndolo); no se crean ni alteran tablas por otro camino."""
    if migrar_automaticamente():
        migraciones.actualizar()
    migraciones.exigir_al_dia()


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
