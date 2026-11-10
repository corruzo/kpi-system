"""Reportes en Excel: consulta los datos según el rol y los filtros, y los entrega a los generadores de `excel/`."""
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import excel
from ..dominio import calendario
from ..errores import Invalido, NoEncontrado
from ..excel import comun, sello
from ..models import Area, Bitacora, Indicador, Medicion, Meta, Usuario
from ..security import firmar_reporte
from . import acceso, auditoria, bitacora, indicadores, parametros, zip_seguro

MAX_BYTES_VERIFICAR = 10_000_000


def _nombre_archivo(empresa: str, prefijo: str) -> str:
    return f"{comun.slug(empresa)}_{prefijo}_{calendario.hoy():%Y%m%d}.xlsx"


def _entregar(db: Session, u: Usuario, libro, tipo: str, prefijo: str, detalle: dict) -> tuple[bytes, str]:
    """Último paso de todo reporte: lo numera y firma, lo bloquea con la contraseña de Parámetros (si está activa),
    deja constancia en la bitácora y devuelve el archivo."""
    numero = f"R-{calendario.hoy():%Y%m%d}-{secrets.token_hex(3).upper()}"
    empresa = parametros.datos_para_reportes(db)["empresa"]
    huella = sello.sellar(libro, numero, tipo, u.nombre, comun.ahora_local(), empresa)
    clave = parametros.clave_de_reportes(db)
    if clave:
        sello.proteger(libro, clave)
    auditoria.registrar(db, u, "REPORTE_EXPORTADO", "reporte", None,
                        {"numero": numero, "tipo": tipo, "huella": huella[:16], "protegido": bool(clave), **detalle})
    db.commit()
    return comun.a_bytes(libro), _nombre_archivo(empresa, prefijo)


def verificar(db: Session, contenido: bytes) -> dict:
    """Comprueba que un Excel descargado de SPE TPV no fue modificado: firma del sistema, huella del contenido y
    constancia de su emisión en la bitácora."""
    if len(contenido) > MAX_BYTES_VERIFICAR:
        raise Invalido("El archivo supera 10 MB.")
    try:
        zip_seguro.validar_xlsx(contenido)
    except ValueError as e:
        raise Invalido(str(e)) from None
    c = sello.leer_control(contenido)
    if not c or not c["numero"]:
        raise Invalido("El archivo no es un reporte de SPE TPV (no tiene la hoja «Control»).")
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
    """Real contra meta. El encargado de proceso solo obtiene sus indicadores (ver `acceso`)."""
    q_ind = acceso.restringir(select(Indicador).order_by(Indicador.codigo), u)
    q_med = acceso.restringir(select(Medicion).join(Indicador).order_by(Indicador.codigo, Medicion.periodo), u)
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
    q_pres = acceso.restringir(select(Meta).join(Indicador, Meta.indicador_id == Indicador.id), u)
    if area_id:
        q_pres = q_pres.where(Indicador.area_id == area_id)
    if anio:
        q_pres = q_pres.where(Meta.ejercicio == int(anio))
    metas = {(p.indicador_id, p.periodo): p.valor for p in db.scalars(q_pres)}
    anios = {int(anio)} if anio else ({m.ejercicio or calendario.ejercicio_de(m.indicador.frecuencia, m.periodo) for m in meds}
                                      | {p.ejercicio for p in db.scalars(q_pres)})
    q_apr = acceso.restringir(select(Medicion.id).join(Indicador).where(Medicion.estado == "enviado"), u)
    if area_id:
        q_apr = q_apr.where(Indicador.area_id == area_id)
    por_aprobar = len(db.scalars(q_apr).all())
    empresa = parametros.datos_para_reportes(db)["empresa"]
    libro = excel.general.reporte_general(empresa, meds, inds, metas, sorted(anios), u.nombre, " · ".join(filtros),
                                          por_aprobar, solo_cargadas=bool(estado))
    return _entregar(db, u, libro, "General", "real_vs_meta", {"filtros": filtros, "filas": len(meds)})


def fichas(db: Session, u: Usuario, ejercicio: int | None, area_id: int | None, indicador_id: int | None) -> tuple[bytes, str]:
    """Una hoja por indicador con el formato de la ficha técnica del SGC."""
    q = acceso.restringir(select(Indicador).order_by(Indicador.codigo), u)
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
    libro = excel.bitacora.reporte_bitacora(parametros.datos_para_reportes(db)["empresa"], registros, bitacora.codigos_de_indicadores(db), u.nombre, auditoria.verificar(db))
    return _entregar(db, u, libro, "Bitácora", "bitacora", {"registros": len(registros)})
