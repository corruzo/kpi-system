"""Recordatorios de carga: quién tiene períodos pendientes (administrador y gerente)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ... import schemas
from ...models import Usuario
from ...servicios import recordatorios
from .. import serializadores as ser
from ..deps import IdRuta, escritura, get_db, requiere

router = APIRouter(prefix="/api/recordatorios", tags=["recordatorios"])
quienes = requiere("gerente", "admin")


@router.get("")
def pendientes(db: Session = Depends(get_db), _=Depends(quienes)):
    r = recordatorios.pendientes_por_encargado(db)
    for e in r["encargados"]:
        e["ultimo_recordatorio"] = ser.iso(e["ultimo_recordatorio"])
    return r


@router.post("/{usuario_id}", status_code=201)
def registrar(usuario_id: IdRuta, datos: schemas.RecordatorioIn, db: Session = Depends(get_db), u: Usuario = Depends(quienes),
              _=Depends(escritura)):
    recordatorios.registrar(db, u, usuario_id, datos.mensaje)
    return {"ok": True}
