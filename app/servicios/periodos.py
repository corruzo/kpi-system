"""Consulta de los períodos justificados (ver `justificaciones.py`). Módulo aparte para que lo usen `indicadores` y `ejercicios`
sin importarse entre sí."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import PeriodoJustificado


def justificados_de(db: Session, ids: list[int] | None = None) -> dict[int, dict[str, PeriodoJustificado]]:
    """{indicador_id: {período: justificación}} (de los indicadores `ids`, si se dan), en una sola consulta."""
    q = select(PeriodoJustificado)
    if ids is not None:
        q = q.where(PeriodoJustificado.indicador_id.in_(ids))
    salida: dict[int, dict[str, PeriodoJustificado]] = {}
    for j in db.scalars(q):
        salida.setdefault(j.indicador_id, {})[j.periodo] = j
    return salida
