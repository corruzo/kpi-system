"""Bitácora de trazabilidad: permiso técnico, solo del Desarrollador."""
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from ...servicios import auditoria, bitacora
from .. import serializadores as ser
from ..deps import Desde, IdConsulta, Limite, con_total, get_db, requiere_permiso

router = APIRouter(prefix="/api/bitacora", tags=["bitácora"], dependencies=[Depends(requiere_permiso("bitacora.ver"))])


@router.get("")
def listar(accion: str | None = None, indicador_id: IdConsulta = None, usuario: str | None = None,
           desde: Desde = 0, limite: Limite = 100, response: Response = None, db: Session = Depends(get_db)):
    con_total(response, bitacora.contar(db, accion=accion, indicador_id=indicador_id, usuario=usuario))
    codigos = bitacora.codigos_de_indicadores(db)
    return [ser.bitacora(b, codigos.get(b.indicador_id))
            for b in bitacora.listar(db, accion=accion, indicador_id=indicador_id, usuario=usuario, desde=desde, limite=limite)]


@router.get("/verificar")
def verificar(db: Session = Depends(get_db)):
    """Recorre la cadena de hashes y confirma que ningún registro fue alterado."""
    return auditoria.verificar(db)
