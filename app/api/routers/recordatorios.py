"""Recordatorios de carga: quién tiene períodos pendientes (administrador y gerente)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ... import schemas
from ...models import Usuario
from ...servicios import recordatorios
from .. import serializadores as ser
from ..deps import Desde, IdRuta, Limite, escritura, get_db, requiere

router = APIRouter(prefix="/api/recordatorios", tags=["recordatorios"])
quienes = requiere("gerente", "admin")


@router.get("")
def pendientes(solo_pendientes: bool = False, desde: Desde = 0, limite: Limite | None = None, db: Session = Depends(get_db), _=Depends(quienes)):
    """Encargados con carga pendiente. Con `limite` se entrega solo una página de encargados (`total` da la cantidad)."""
    r = recordatorios.pendientes_por_encargado(db)
    r["deben"] = sum(1 for e in r["encargados"] if e["total"] > 0)
    r["sin_correo"] = sum(1 for e in r["encargados"] if e["total"] > 0 and not e["email"])
    if solo_pendientes:
        r["encargados"] = [e for e in r["encargados"] if e["total"] > 0]
    r["total"] = len(r["encargados"])
    if limite is not None:
        r["encargados"] = r["encargados"][desde:desde + limite]
    for e in r["encargados"]:
        e["ultimo_recordatorio"] = ser.iso(e["ultimo_recordatorio"])
    return r


@router.post("/{usuario_id}", status_code=201)
def registrar(usuario_id: IdRuta, datos: schemas.RecordatorioIn, db: Session = Depends(get_db), u: Usuario = Depends(quienes),
              _=Depends(escritura)):
    recordatorios.registrar(db, u, usuario_id, datos.mensaje)
    return {"ok": True}
