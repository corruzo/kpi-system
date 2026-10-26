"""Inicio de sesión, cambio de contraseña y guía de bienvenida."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import security
from ..errores import DemasiadosIntentos, Invalido, NoAutenticado
from ..models import Usuario
from . import auditoria

limite_intentos = security.LimiteIntentos()


def autenticar(db: Session, username: str, password: str, origen: str) -> Usuario:
    """Valida credenciales (con bloqueo temporal tras demasiados fallos) y registra el ingreso."""
    usuario = username.strip().lower()
    llave = f"{origen}|{usuario}"
    if limite_intentos.bloqueado(llave):
        raise DemasiadosIntentos("Demasiados intentos fallidos. Intente de nuevo en 15 minutos.")
    u = db.scalar(select(Usuario).where(Usuario.username == usuario))
    if not u or not u.activo or not security.verificar_password(password, u.password_hash):
        limite_intentos.fallo(llave)
        raise NoAutenticado("Usuario o contraseña incorrectos.")
    limite_intentos.limpiar(llave)
    auditoria.registrar(db, u, "INICIO_SESION", "usuario", u.id)
    db.commit()
    return u


def cambiar_clave(db: Session, u: Usuario, actual: str, nueva: str) -> None:
    """Cambia la contraseña e invalida las demás sesiones del usuario (sube su versión de sesión)."""
    if not security.verificar_password(actual, u.password_hash):
        raise Invalido("La contraseña actual no es correcta.")
    u.password_hash = security.hash_password(nueva)
    u.sesion_v += 1
    auditoria.registrar(db, u, "CLAVE_CAMBIADA", "usuario", u.id)
    db.commit()


def marcar_guia(db: Session, u: Usuario, vista: bool) -> bool:
    u.tour_visto = vista
    db.commit()
    return u.tour_visto
