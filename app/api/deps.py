"""Dependencias de FastAPI: sesión de base de datos, usuario autenticado, permisos por rol y bloqueo de escritura."""
from fastapi import Depends, Request
from sqlalchemy.orm import Session

from .. import security
from ..config import TRUST_PROXY
from ..database import get_db
from ..errores import NoAutenticado, Prohibido
from ..models import Usuario
from ..servicios.concurrencia import candado_escritura

__all__ = ["escritura", "get_db", "origen_cliente", "requiere", "usuario_actual"]


def usuario_actual(request: Request, db: Session = Depends(get_db)) -> Usuario:
    """El usuario de la cookie de sesión; la sesión caduca al cambiar la contraseña o desactivar al usuario."""
    token = security.leer_token(request.cookies.get(security.COOKIE))
    u = db.get(Usuario, token[0]) if token else None
    if not u or not u.activo or u.sesion_v != token[1]:
        raise NoAutenticado("Sesión no válida o expirada.")
    return u


def requiere(*roles: str):
    """Dependencia que exige uno de los roles dados."""
    def comprobar(u: Usuario = Depends(usuario_actual)) -> Usuario:
        if u.rol not in roles:
            raise Prohibido("No tiene permisos para esta acción.")
        return u
    return comprobar


def escritura():
    """Serializa las operaciones que escriben en la base (mantiene íntegra la cadena de la bitácora)."""
    with candado_escritura:
        yield


def origen_cliente(request: Request) -> str:
    """IP del cliente; detrás de un proxy de confianza se toma de X-Forwarded-For."""
    reenviado = request.headers.get("x-forwarded-for")
    if TRUST_PROXY and reenviado:
        return reenviado.split(",")[0].strip()
    return request.client.host if request.client else "?"
