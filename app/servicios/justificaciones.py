"""Períodos justificados: un período que no se carga por una razón formal (parada de planta, el indicador empezó a medirse
después, no aplica). Cuenta como cubierto: no aparece como pendiente ni impide cerrar el ejercicio fiscal.

Lo hace quien tenga el permiso `periodos.justificar`, solo sobre indicadores de su ámbito, siempre con motivo, solo mientras
el ejercicio esté abierto y solo si el período no tiene ya una carga. Todo queda en la bitácora; se puede revocar."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..dominio import calendario
from ..errores import Conflicto, Invalido, NoEncontrado, Prohibido
from ..models import TIPOS_JUSTIFICACION, Indicador, Medicion, PeriodoJustificado, Usuario
from . import acceso, auditoria, ejercicios, indicadores

MIN_MOTIVO = 5
ETIQUETAS = {"parada_planta": "Parada de planta", "inicio_medicion": "Empezó a medirse después", "no_aplica": "No aplica"}


def _indicador_del_ambito(db: Session, u: Usuario, indicador_id: int) -> Indicador:
    ind = indicadores.obtener_visible(db, u, indicador_id)
    if not acceso.en_ambito(u, ind):
        raise Prohibido("Solo puede justificar períodos de indicadores de su ámbito.")
    return ind


def justificar(db: Session, u: Usuario, indicador_id: int, periodo: str, tipo: str, motivo: str) -> PeriodoJustificado:
    ind = _indicador_del_ambito(db, u, indicador_id)
    if tipo not in TIPOS_JUSTIFICACION:
        raise Invalido("Tipo de justificación no válido.")
    motivo = " ".join(motivo.split())
    if len(motivo) < MIN_MOTIVO:
        raise Invalido("Indique el motivo de la justificación.")
    if ind.frecuencia == "eventual":
        raise Invalido("Un indicador eventual se carga cuando ocurre: no tiene períodos que justificar.")
    if not calendario.periodo_valido(ind.frecuencia, periodo) or calendario.es_futuro(ind.frecuencia, periodo, calendario.hoy()):
        raise Invalido("Período no válido para la frecuencia del indicador.")
    anio = calendario.ejercicio_de(ind.frecuencia, periodo)
    ejercicios.exigir_abierto(db, anio)
    if db.scalar(select(Medicion.id).where(Medicion.indicador_id == ind.id, Medicion.periodo == periodo)):
        raise Conflicto("Ese período ya tiene una carga: no puede justificarse.")
    if db.scalar(select(PeriodoJustificado.id).where(PeriodoJustificado.indicador_id == ind.id, PeriodoJustificado.periodo == periodo)):
        raise Conflicto("Ese período ya está justificado.")
    j = PeriodoJustificado(indicador_id=ind.id, periodo=periodo, ejercicio=anio, tipo=tipo, motivo=motivo, por_id=u.id)
    db.add(j)
    db.flush()
    auditoria.registrar(db, u, "PERIODO_JUSTIFICADO", "periodo", ind.id,
                        {"codigo": ind.codigo, "periodo": periodo, "etiqueta": calendario.etiqueta(ind.frecuencia, periodo),
                         "tipo": tipo, "motivo": motivo}, ind)
    db.commit()
    return j


def revocar(db: Session, u: Usuario, indicador_id: int, periodo: str) -> None:
    ind = _indicador_del_ambito(db, u, indicador_id)
    j = db.scalar(select(PeriodoJustificado).where(PeriodoJustificado.indicador_id == ind.id, PeriodoJustificado.periodo == periodo))
    if not j:
        raise NoEncontrado("Ese período no está justificado.")
    ejercicios.exigir_abierto(db, j.ejercicio)
    auditoria.registrar(db, u, "JUSTIFICACION_REVOCADA", "periodo", ind.id,
                        {"codigo": ind.codigo, "periodo": periodo, "etiqueta": calendario.etiqueta(ind.frecuencia, periodo),
                         "tipo": j.tipo, "motivo": j.motivo}, ind)
    db.delete(j)
    db.commit()
