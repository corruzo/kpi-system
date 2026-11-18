"""Notificaciones de la persona (la campana de la cabecera).

Dos clases de aviso:
- **Guardados** (`Notificacion`): se crean al revisar una carga (aprobada, devuelta con su motivo, reabierta) y llegan a quienes la
  cargan: el responsable principal, el suplente y quien la envió (menos quien revisó). Se marcan como leídos.
- **Calculados** (`avisos_de_cierre`): «el período está por cerrar y faltan cargas». No se guardan: se calculan al consultar, así
  que desaparecen solos al cargar (no hace falta un proceso programado). Empiezan `DIAS_AVISO_CIERRE` días antes del fin del período.
"""
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..dominio import calendario
from ..models import Indicador, Medicion, Notificacion, Usuario, ahora
from . import acceso, indicadores
from .periodos import justificados_de

DIAS_AVISO_CIERRE = 5
MAX_LISTA = 30
VERBO = {"aprobada": "aprobó", "devuelta": "devolvió para corregir", "reabierta": "reabrió"}
TITULO = {"aprobada": "Carga aprobada", "devuelta": "Carga devuelta", "reabierta": "Carga reabierta"}


# ---------------------------------------------------------------- guardados: se crean al revisar
def avisar_revision(db: Session, revisor: Usuario, m: Medicion, tipo: str, nota: str) -> None:
    """Avisa a quienes cargan el indicador (y a quien envió esta carga) que `revisor` la aprobó, devolvió o reabrió.
    Va dentro de la transacción de la revisión (el llamador hace commit)."""
    ind = m.indicador
    destinatarios = {x.id: x for x in [*ind.cargadores, m.cargado_por] if x is not None and x.activo and x.id != revisor.id}
    texto = f"{revisor.nombre} {VERBO[tipo]} la carga de {calendario.etiqueta(ind.frecuencia, m.periodo)} de {ind.codigo} · {ind.nombre}."
    if nota:
        texto += f" Motivo: {nota}" if tipo != "aprobada" else f" Nota: {nota}"
    for uid in destinatarios:
        db.add(Notificacion(usuario_id=uid, tipo=tipo, titulo=f"{TITULO[tipo]}: {ind.codigo}", texto=texto,
                            indicador_id=ind.id, periodo=m.periodo, creada_en=ahora()))


# ---------------------------------------------------------------- calculados: cierre del período cerca
def avisos_de_cierre(db: Session, u: Usuario, hoy: date | None = None) -> list[dict]:
    """[{indicador_id, codigo, nombre, periodos:[etiqueta], dias}] de los indicadores que la persona carga (responsable principal o
    suplente) y que tienen cargas pendientes cuando el período en curso cierra en `DIAS_AVISO_CIERRE` días o menos.
    Pendientes = los vencidos sin cargar (o devueltos) más el período en curso si aún no tiene carga ni justificación."""
    hoy = hoy or calendario.hoy()
    inds = list(db.scalars(select(Indicador).where(acceso.condicion_carga(u), Indicador.frecuencia != "eventual").order_by(Indicador.codigo)))
    if acceso.alcance_total(u):
        inds = [i for i in inds if i.responsable_id == u.id or i.suplente_id == u.id]   # un rol de sistema avisa solo de lo suyo
    if not inds:
        return []
    estados = indicadores.estados_de_todos(db, [i.id for i in inds])
    justificados = justificados_de(db, [i.id for i in inds])
    avisos, hay_cierre_cerca = [], False
    for ind in inds:
        ests = estados.get(ind.id, {})
        pendientes = calendario.periodos_pendientes(ind.frecuencia, hoy, ests, ind.creado_en.date())
        actual = calendario.periodo_actual(ind.frecuencia, hoy)
        ini, fin = calendario.rango(ind.frecuencia, actual)
        dias = (fin - hoy).days
        cerca = dias <= DIAS_AVISO_CIERRE
        if cerca and actual not in ests and actual not in justificados.get(ind.id, {}) and fin >= ind.creado_en.date():
            pendientes = [*pendientes, actual]
        if pendientes:
            avisos.append({"indicador_id": ind.id, "codigo": ind.codigo, "nombre": ind.nombre, "dias": max(dias, 0),
                           "periodos": [calendario.etiqueta(ind.frecuencia, p) for p in pendientes]})
            hay_cierre_cerca = hay_cierre_cerca or cerca
    return avisos if hay_cierre_cerca else []


# ---------------------------------------------------------------- consulta y lectura
def no_leidas(db: Session, u: Usuario) -> int:
    return db.scalar(select(func.count(Notificacion.id)).where(Notificacion.usuario_id == u.id, Notificacion.leida_en.is_(None))) or 0


def listar(db: Session, u: Usuario, limite: int = MAX_LISTA) -> list[Notificacion]:
    """Las más recientes de la persona (sin leer primero)."""
    q = (select(Notificacion).where(Notificacion.usuario_id == u.id)
         .order_by(Notificacion.leida_en.is_not(None), Notificacion.id.desc()).limit(max(1, min(limite, 100))))
    return list(db.scalars(q))


def resumen(db: Session, u: Usuario, hoy: date | None = None) -> dict:
    """Todo lo que necesita la campana: contador de no leídas, avisos guardados y avisos de cierre calculados."""
    return {"no_leidas": no_leidas(db, u), "items": [serializar(n) for n in listar(db, u)], "avisos": avisos_de_cierre(db, u, hoy),
            "dias_aviso": DIAS_AVISO_CIERRE}


def serializar(n: Notificacion) -> dict:
    return {"id": n.id, "tipo": n.tipo, "titulo": n.titulo, "texto": n.texto, "indicador_id": n.indicador_id, "periodo": n.periodo,
            "creada_en": n.creada_en.isoformat(timespec="seconds"), "leida": n.leida_en is not None}


def marcar_leidas(db: Session, u: Usuario, ids: list[int] | None = None) -> int:
    """Marca como leídas las indicadas (solo las propias) o, sin `ids`, todas las de la persona. Devuelve cuántas cambió."""
    q = select(Notificacion).where(Notificacion.usuario_id == u.id, Notificacion.leida_en.is_(None))
    if ids is not None:
        q = q.where(Notificacion.id.in_(ids))
    filas = list(db.scalars(q))
    for n in filas:
        n.leida_en = ahora()
    db.commit()
    return len(filas)
