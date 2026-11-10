"""Dependencias de FastAPI: sesión de base de datos, usuario autenticado, permisos del catálogo y bloqueo de escritura."""
from typing import Annotated

from fastapi import Depends, Path, Query, Request, Response
from sqlalchemy.orm import Session

from .. import permisos, security
from ..config import TRUST_PROXY
from ..database import ES_POSTGRES, get_db
from ..errores import NoAutenticado, Prohibido
from ..models import Usuario
from ..servicios import acceso
from ..servicios.concurrencia import bloquear_escritura, candado_escritura

# Parámetros numéricos con rango válido: un id gigante o un año imposible se rechaza con 422 en vez de llegar a la base de datos
# (PostgreSQL: «integer out of range») o a las fechas (año 0).
ID_MAX = 2**31 - 1
IdRuta = Annotated[int, Path(ge=1, le=ID_MAX)]
AnioRuta = Annotated[int, Path(ge=2000, le=2100)]
IdConsulta = Annotated[int | None, Query(ge=1, le=ID_MAX)]
AnioConsulta = Annotated[int | None, Query(ge=2000, le=2100)]
Desde = Annotated[int, Query(ge=0, le=10_000_000)]
Limite = Annotated[int, Query(ge=1, le=500)]

__all__ = ["con_total", "AnioConsulta", "AnioRuta", "Desde", "IdConsulta", "IdRuta", "Limite", "escritura", "get_db", "origen_cliente",
           "cuenta_propia", "requiere_permiso", "usuario_actual"]


def con_total(response: Response, total: int) -> None:
    """Informa en `X-Total-Count` cuántos registros hay en total (para paginar sin descargarlos todos)."""
    response.headers["X-Total-Count"] = str(total)


def usuario_actual(request: Request, db: Session = Depends(get_db)) -> Usuario:
    """El usuario de la cookie de sesión, con sus permisos y su ámbito ya leídos (una vez por petición).
    La sesión caduca al cambiar la contraseña o desactivar al usuario."""
    token = security.leer_token(request.cookies.get(security.COOKIE))
    u = db.get(Usuario, token[0]) if token else None
    if not u or not u.activo or u.sesion_v != token[1]:
        raise NoAutenticado("Sesión no válida o expirada.")
    acceso.preparar(db, u)
    return u


def cuenta_propia(u: Usuario = Depends(usuario_actual)) -> Usuario:
    """Funciones de la cuenta propia (perfil, contraseña, guía, arranque): cualquier sesión válida, tenga rol o no."""
    return u


cuenta_propia.propia = True


def requiere_permiso(*codigos: str, nivel: str | None = None):
    """Dependencia que exige un permiso del catálogo (con varios códigos, basta uno). Toda ruta de la API declara el
    suyo así; el alcance sobre los datos lo aplica después el motor (`servicios/acceso.py`)."""
    desconocidos = [c for c in codigos if not permisos.existe(c)]
    if desconocidos or not codigos:
        raise RuntimeError(f"Permiso inexistente en el catálogo: {desconocidos or '(ninguno)'}")

    def comprobar(u: Usuario = Depends(usuario_actual)) -> Usuario:
        if not any(acceso.puede(u, c, nivel) for c in codigos):
            raise Prohibido(acceso.SIN_PERMISO)
        return u
    comprobar.permisos = codigos
    return comprobar


def escritura(db: Session = Depends(get_db)):
    """Serializa las operaciones que escriben en la base (mantiene íntegra la cadena de la bitácora).
    En PostgreSQL lo hace la propia base con un advisory lock transaccional, sin candados en memoria."""
    if ES_POSTGRES:
        bloquear_escritura(db)
        yield
    else:
        with candado_escritura:
            yield


def origen_cliente(request: Request) -> str:
    """IP del cliente; detrás de un proxy de confianza se toma de X-Forwarded-For."""
    reenviado = request.headers.get("x-forwarded-for")
    if TRUST_PROXY and reenviado:
        return reenviado.split(",")[0].strip()
    return request.client.host if request.client else "?"
