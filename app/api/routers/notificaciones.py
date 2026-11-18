"""Notificaciones de la persona (la campana): lo suyo, siempre. No requiere un permiso del catálogo: es de la cuenta propia."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ... import schemas
from ...models import Usuario
from ...servicios import notificaciones
from ..deps import cuenta_propia, escritura, get_db

router = APIRouter(prefix="/api/notificaciones", tags=["notificaciones"])


@router.get("")
def listar(db: Session = Depends(get_db), u: Usuario = Depends(cuenta_propia)):
    """Contador de no leídas, avisos guardados (aprobada, devuelta, reabierta) y avisos calculados de cierre de período cercano."""
    return notificaciones.resumen(db, u)


@router.post("/leer")
def leer(datos: schemas.LeerNotificacionesIn, db: Session = Depends(get_db), u: Usuario = Depends(cuenta_propia), _=Depends(escritura)):
    """Marca como leídas las indicadas (o todas). Solo toca las de quien llama."""
    return {"marcadas": notificaciones.marcar_leidas(db, u, datos.ids), "no_leidas": notificaciones.no_leidas(db, u)}
