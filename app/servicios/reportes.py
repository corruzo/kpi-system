"""Reportes en Excel: consulta los datos según el rol y los filtros, y los entrega a los generadores de `excel/`."""
import secrets
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import excel
from ..dominio import calendario
from ..errores import Invalido, NoEncontrado
from ..excel import comun, sello
from ..models import Area, Bitacora, Indicador, Medicion, Usuario
from ..security import firmar_reporte
from . import auditoria, bitacora, indicadores, marca, parametros


def _nombre_archivo(prefijo: str) -> str:
    return f"SGC_TRIPOLIVEN_{prefijo}_{date.today():%Y%m%d}.xlsx"


def _entregar(db: Session, u: Usuario, libro, tipo: str, prefijo: str, detalle: dict) -> tuple[bytes, str]:
    """Último paso de todo reporte: lo numera y firma, lo bloquea con la contraseña de Parámetros (si está activa),
    deja constancia en la bitácora y devuelve el archivo."""
    numero = f"R-{date.today():%Y%m%d}-{secrets.token_hex(3).upper()}"
    huella = sello.sellar(libro, numero, tipo, u.nombre, comun.hora_local(datetime.utcnow()))
    clave = parametros.clave_de_reportes(db)
    if clave:
        sello.proteger(libro, clave)
    auditoria.registrar(db, u, "REPORTE_EXPORTADO", "reporte", None,
                        {"numero": numero, "tipo": tipo, "huella": huella[:16], "protegido": bool(clave), **detalle})
    db.commit()
    return comun.a_bytes(libro), _nombre_archivo(prefijo)


def verificar(db: Session, contenido: bytes) -> dict:
    """Comprueba que un Excel descargado del SGC • TRIPOLIVEN no fue modificado: firma del sistema, huella del contenido y
    constancia de su emisión en la bitácora."""
    c = sello.leer_control(contenido)
    if not c or not c["numero"]:
        raise Invalido("El archivo no es un reporte del SGC • TRIPOLIVEN (no tiene la hoja «Control»).")
    firma_valida = c["firma"] == firmar_reporte(f"{c['numero']}|{c['huella_declarada']}")
    contenido_intacto = c["huella_real"] == c["huella_declarada"]
    emitido = any((b.detalle or {}).get("numero") == c["numero"]
                  for b in db.scalars(select(Bitacora).where(Bitacora.accion == "REPORTE_EXPORTADO").order_by(Bitacora.id.desc()).limit(5000)))
    ok = firma_valida and contenido_intacto and emitido
    motivo = ("Reporte auténtico: su contenido coincide con el que emitió el sistema." if ok else
              "La firma del sistema no es válida: el archivo no fue emitido por este sistema." if not firma_valida else
              "El contenido del archivo fue modificado después de su emisión." if not contenido_intacto else
              "El número de reporte no consta en la bitácora de este sistema.")
    return {"ok": ok, "numero": c["numero"], "tipo": c["tipo"], "generado_por": c["generado_por"], "fecha": c["fecha"], "motivo": motivo}


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
    libro = excel.general.reporte_general(meds, inds, u.nombre, " · ".join(filtros), por_aprobar, marca.bytes_logo(db))
    return _entregar(db, u, libro, "General", "reporte", {"filtros": filtros, "filas": len(meds)})


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
    libro = excel.ficha.fichas_xlsx(hojas, parametros.datos_para_reportes(db), u.nombre)
    return _entregar(db, u, libro, "Fichas técnicas", "fichas", {"indicadores": len(inds), "ejercicio": anio_ref})


def de_bitacora(db: Session, u: Usuario) -> tuple[bytes, str]:
    registros = db.scalars(select(Bitacora).order_by(Bitacora.id.desc()).limit(50000)).all()
    libro = excel.bitacora.reporte_bitacora(registros, bitacora.codigos_de_indicadores(db), u.nombre, auditoria.verificar(db))
    return _entregar(db, u, libro, "Bitácora", "bitacora", {"registros": len(registros)})
