"""Sesión: ingreso, salida, perfil, cambio de contraseña, guía de bienvenida y datos públicos de marca."""
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from ... import schemas, security
from ...config import PRODUCCION
from ...models import Usuario
from ...servicios import marca, parametros, sesion
from .. import serializadores as ser
from ..deps import escritura, get_db, origen_cliente, usuario_actual

router = APIRouter(prefix="/api", tags=["sesión"])


def _abrir_sesion(response: Response, u: Usuario) -> None:
    response.set_cookie(security.COOKIE, security.crear_token(u.id, u.sesion_v), httponly=True, secure=PRODUCCION,
                        samesite="lax", max_age=security.DURACION)


@router.post("/login")
def ingresar(datos: schemas.LoginIn, request: Request, response: Response, db: Session = Depends(get_db),
             _=Depends(escritura)):
    u = sesion.autenticar(db, datos.username, datos.password, origen_cliente(request))
    _abrir_sesion(response, u)
    return ser.usuario(u)


@router.post("/logout")
def salir(response: Response):
    response.delete_cookie(security.COOKIE)
    return {"ok": True}


@router.get("/me")
def perfil(u: Usuario = Depends(usuario_actual)):
    return ser.usuario(u)


@router.post("/cambiar-clave")
def cambiar_clave(datos: schemas.ClaveIn, response: Response, db: Session = Depends(get_db),
                  u: Usuario = Depends(usuario_actual), _=Depends(escritura)):
    sesion.cambiar_clave(db, u, datos.actual, datos.nueva)
    _abrir_sesion(response, u)   # la sesión actual se renueva; las demás quedan invalidadas
    return {"ok": True}


@router.post("/tour")
def marcar_guia(datos: schemas.TourIn, db: Session = Depends(get_db), u: Usuario = Depends(usuario_actual)):
    return {"tour_visto": sesion.marcar_guia(db, u, datos.visto)}


@router.get("/publico")
def datos_publicos(db: Session = Depends(get_db)):
    """Nombre de la empresa y logo, visibles antes de iniciar sesión."""
    return {"empresa": parametros.leer(db).get("empresa", ""), "logo_url": marca.url_logo(db)}
