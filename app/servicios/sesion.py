"""Inicio de sesión, cambio de contraseña y guía de bienvenida."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import security
from ..errores import DemasiadosIntentos, Invalido, NoAutenticado
from ..models import Usuario
from . import auditoria

limite_intentos = security.LimiteIntentos()
MAX_POR_PAREJA = 5      # misma IP contra el mismo usuario
MAX_POR_ORIGEN = 20     # una IP probando muchos usuarios (password spraying)
MAX_POR_USUARIO = 10    # muchas IP contra un mismo usuario (más holgado: bloquear la cuenta ajena es un riesgo)


def autenticar(db: Session, username: str, password: str, origen: str) -> Usuario:
    """Valida credenciales (con bloqueo temporal tras demasiados fallos) y registra el ingreso."""
    usuario = username.strip().lower()
    pareja, por_origen, por_usuario = f"{origen}|{usuario}", f"origen|{origen}", f"usuario|{usuario}"
    if (limite_intentos.bloqueado(pareja, MAX_POR_PAREJA) or limite_intentos.bloqueado(por_origen, MAX_POR_ORIGEN)
            or limite_intentos.bloqueado(por_usuario, MAX_POR_USUARIO)):
        raise DemasiadosIntentos("Demasiados intentos fallidos. Intente de nuevo en 15 minutos.")
    u = db.scalar(select(Usuario).where(Usuario.username == usuario))
    # Se verifica siempre una contraseña (la ficticia si el usuario no existe) para que el tiempo no delate cuentas.
    correcta = security.verificar_password(password, u.password_hash if u else security.HASH_FICTICIO)
    if not u or not u.activo or not correcta:
        for llave in (pareja, por_origen, por_usuario):   # también cuentan los usuarios inexistentes
            limite_intentos.fallo(llave)
        raise NoAutenticado("Usuario o contraseña incorrectos.")
    limite_intentos.limpiar(pareja)
    limite_intentos.limpiar(por_usuario)   # el contador del origen NO se borra: un acceso válido no perdona el spraying
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
