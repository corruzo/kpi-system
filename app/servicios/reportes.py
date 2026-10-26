"""Reportes en Excel: consulta los datos según el rol y los filtros, y los entrega a los generadores de `excel/`."""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import excel
from ..dominio import calendario
from ..errores import NoEncontrado
from ..models import Area, Bitacora, Indicador, Medicion, Usuario
from . import auditoria, bitacora, indicadores, marca, parametros


def _nombre_archivo(prefijo: str) -> str:
    return f"SIGT_{prefijo}_{date.today():%Y%m%d}.xlsx"


def general(db: Session, u: Usuario, anio: int | None, area_id: int | None, estado: str | None) -> tuple[bytes, str]:
    """Resumen, mediciones, tendencias, plan de mejora y fichas. El jefe solo obtiene su área."""
    if u.rol == "jefe":
        area_id = u.area_id
    q_ind = select(Indicador).order_by(Indicador.codigo)
    q_med = select(Medicion).join(Indicador).order_by(Indicador.codigo, Medicion.periodo)
    filtros = []
    if area_id:
        q_ind, q_med = q_ind.where(Indicador.area_id == area_id), q_med.where(Indicador.area_id == area_id)
        area = db.get(Area, area_id)
        filtros.append(f"Área: {area.nombre if area else area_id}")
    if anio:
        filtros.append(f"Ejercicio fiscal: {calendario.etiqueta_ejercicio(int(anio))}")
    if estado:
        q_med = q_med.where(Medicion.estado == estado)
        filtros.append(f"Estado: {estado}")
    inds, meds = db.scalars(q_ind).all(), db.scalars(q_med).all()
    if anio:
        meds = [m for m in meds if calendario.ejercicio_de(m.indicador.frecuencia, m.periodo) == int(anio)]
    por_aprobar = len(db.scalars(select(Medicion.id).join(Indicador).where(
        Medicion.estado == "enviado", *([Indicador.area_id == area_id] if area_id else []))).all())
    datos = excel.general.reporte_general(meds, inds, u.nombre, " · ".join(filtros), por_aprobar, marca.bytes_logo(db))
    auditoria.registrar(db, u, "REPORTE_EXPORTADO", "reporte", None, {"filtros": filtros, "filas": len(meds)})
    db.commit()
    return datos, _nombre_archivo("reporte")


def fichas(db: Session, u: Usuario, ejercicio: int | None, area_id: int | None, indicador_id: int | None) -> tuple[bytes, str]:
    """Una hoja por indicador con el formato de la ficha técnica del SGC."""
    q = select(Indicador).order_by(Indicador.codigo)
    if u.rol == "jefe":
        area_id = u.area_id
    if u.rol != "admin":
        q = q.where(Indicador.activo.is_(True))
    if area_id:
        q = q.where(Indicador.area_id == area_id)
    if indicador_id:
        q = q.where(Indicador.id == indicador_id)
    inds = db.scalars(q).all()
    if not inds:
        raise NoEncontrado("No hay indicadores para el reporte.")
    hojas, anio_ref = [], ejercicio
    for ind in inds:
        anio, _, periodos = indicadores.contexto_ficha(db, ind, ejercicio)
        anio_ref = anio_ref or anio
        hojas.append((ind, anio, periodos))
    datos = excel.ficha.fichas_xlsx(hojas, parametros.datos_para_reportes(db), u.nombre)
    auditoria.registrar(db, u, "REPORTE_EXPORTADO", "reporte", None,
                        {"tipo": "fichas", "indicadores": len(inds), "ejercicio": anio_ref})
    db.commit()
    return datos, _nombre_archivo("fichas")


def de_bitacora(db: Session, u: Usuario) -> tuple[bytes, str]:
    registros = db.scalars(select(Bitacora).order_by(Bitacora.id.desc()).limit(50000)).all()
    datos = excel.bitacora.reporte_bitacora(registros, bitacora.codigos_de_indicadores(db), u.nombre, auditoria.verificar(db))
    return datos, _nombre_archivo("bitacora")
