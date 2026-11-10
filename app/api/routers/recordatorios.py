"""Recordatorios de carga: quién tiene períodos pendientes, dentro del ámbito de quien consulta."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ... import schemas
from ...models import Usuario
from ...servicios import recordatorios
from .. import serializadores as ser
from ..deps import Desde, IdRuta, Limite, escritura, get_db, requiere_permiso

router = APIRouter(prefix="/api/recordatorios", tags=["recordatorios"])
envia = requiere_permiso("recordatorios.enviar")


@router.get("")
def pendientes(solo_pendientes: bool = False, desde: Desde = 0, limite: Limite | None = None, db: Session = Depends(get_db),
               u: Usuario = Depends(envia)):
    """Personas que cargan indicadores del ámbito de quien consulta, con sus pendientes. Con `limite` se entrega una página."""
    r = recordatorios.pendientes_por_persona(db, u)
    r["deben"] = sum(1 for e in r["personas"] if e["total"] > 0)
    r["sin_correo"] = sum(1 for e in r["personas"] if e["total"] > 0 and not e["email"])
    if solo_pendientes:
        r["personas"] = [e for e in r["personas"] if e["total"] > 0]
    r["total"] = len(r["personas"])
    if limite is not None:
        r["personas"] = r["personas"][desde:desde + limite]
    for e in r["personas"]:
        e["ultimo_recordatorio"] = ser.iso(e["ultimo_recordatorio"])
    return r


@router.post("/{usuario_id}", status_code=201)
def registrar(usuario_id: IdRuta, datos: schemas.RecordatorioIn, db: Session = Depends(get_db), u: Usuario = Depends(envia),
              _=Depends(escritura)):
    recordatorios.registrar(db, u, usuario_id, datos.mensaje)
    return {"ok": True}
