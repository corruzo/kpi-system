"""Consulta de la bitácora del sistema (solo administrador)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Bitacora, Indicador


def codigos_de_indicadores(db: Session) -> dict[int, str]:
    return dict(db.execute(select(Indicador.id, Indicador.codigo)).all())


def listar(db: Session, *, accion=None, indicador_id=None, usuario=None, desde=0, limite=100) -> list[Bitacora]:
    q = select(Bitacora).order_by(Bitacora.id.desc()).offset(max(desde, 0)).limit(min(limite, 500))
    if accion:
        q = q.where(Bitacora.accion == accion)
    if indicador_id:
        q = q.where(Bitacora.indicador_id == indicador_id)
    if usuario:
        q = q.where(Bitacora.usuario_nombre.ilike(f"%{usuario}%"))
    return list(db.scalars(q))
