"""Bitácora de trazabilidad: visible únicamente para el Administrador SGC."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...servicios import auditoria, bitacora
from .. import serializadores as ser
from ..deps import get_db, requiere

router = APIRouter(prefix="/api/bitacora", tags=["bitácora"], dependencies=[Depends(requiere("admin"))])


@router.get("")
def listar(accion: str | None = None, indicador_id: int | None = None, usuario: str | None = None,
           desde: int = 0, limite: int = 100, db: Session = Depends(get_db)):
    codigos = bitacora.codigos_de_indicadores(db)
    return [ser.bitacora(b, codigos.get(b.indicador_id))
            for b in bitacora.listar(db, accion=accion, indicador_id=indicador_id, usuario=usuario, desde=desde, limite=limite)]


@router.get("/verificar")
def verificar(db: Session = Depends(get_db)):
    """Recorre la cadena de hashes y confirma que ningún registro fue alterado."""
    return auditoria.verificar(db)
