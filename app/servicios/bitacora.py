"""Consulta de la bitácora del sistema (solo administrador)."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Bitacora, Indicador


def codigos_de_indicadores(db: Session) -> dict[int, str]:
    return dict(db.execute(select(Indicador.id, Indicador.codigo)).all())


def _filtrar(q, accion, indicador_id, usuario):
    if accion:
        q = q.where(Bitacora.accion == accion)
    if indicador_id:
        q = q.where(Bitacora.indicador_id == indicador_id)
    if usuario:
        patron = usuario.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")   # «%» y «_» se buscan literalmente
        q = q.where(Bitacora.usuario_nombre.ilike(f"%{patron}%", escape="\\"))
    return q


def listar(db: Session, *, accion=None, indicador_id=None, usuario=None, desde=0, limite=100) -> list[Bitacora]:
    q = select(Bitacora).order_by(Bitacora.id.desc()).offset(max(desde, 0)).limit(max(1, min(limite, 500)))
    return list(db.scalars(_filtrar(q, accion, indicador_id, usuario)))


def contar(db: Session, *, accion=None, indicador_id=None, usuario=None) -> int:
    return db.scalar(_filtrar(select(func.count(Bitacora.id)), accion, indicador_id, usuario)) or 0
