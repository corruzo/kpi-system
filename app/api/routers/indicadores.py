"""Indicadores: fichas técnicas (consulta, alta, edición, baja), períodos de carga, ficha por ejercicio y fórmulas."""
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ... import schemas
from ...dominio import calendario
from ...models import Usuario
from ...servicios import indicadores, parametros
from .. import serializadores as ser
from ..deps import escritura, get_db, requiere, usuario_actual

router = APIRouter(prefix="/api", tags=["indicadores"])
solo_admin = requiere("admin")


@router.get("/indicadores")
def listar(ejercicio: int | None = None, db: Session = Depends(get_db), u: Usuario = Depends(usuario_actual)):
    """Indicadores con sus períodos pendientes del ejercicio pedido (y cuántos quedan en otros ejercicios)."""
    return [ser.indicador_con_pendientes(*fila) for fila in indicadores.listar(db, u, ejercicio)]


@router.post("/indicadores", status_code=201)
def crear(datos: schemas.IndicadorIn, db: Session = Depends(get_db), u: Usuario = Depends(solo_admin), _=Depends(escritura)):
    return ser.indicador(indicadores.crear(db, u, datos))


@router.put("/indicadores/{indicador_id}")
def editar(indicador_id: int, datos: schemas.IndicadorIn, db: Session = Depends(get_db), u: Usuario = Depends(solo_admin),
           _=Depends(escritura)):
    return ser.indicador(indicadores.editar(db, u, indicador_id, datos))


@router.delete("/indicadores/{indicador_id}")
def eliminar(indicador_id: int, db: Session = Depends(get_db), u: Usuario = Depends(solo_admin), _=Depends(escritura)):
    return {"ok": True, "archivado": indicadores.eliminar(db, u, indicador_id)}


@router.get("/indicadores/{indicador_id}/periodos")
def periodos(indicador_id: int, ejercicio: int | None = None, db: Session = Depends(get_db), u: Usuario = Depends(usuario_actual)):
    """Períodos cargables de un ejercicio fiscal (por defecto el vigente), del más reciente al más antiguo."""
    d = indicadores.periodos_de_carga(db, u, indicador_id, ejercicio)
    f = d["indicador"].frecuencia
    actual = calendario.periodo_actual(f, date.today())
    return {"sugerido": d["pendientes"][0] if d["pendientes"] else None, "ejercicio": d["ejercicio"],
            "pendientes_otros": [{"ejercicio": a, "etiqueta": calendario.etiqueta_ejercicio(a), "n": n}
                                 for a, n in sorted(d["pendientes_otros"].items())],
            "periodos": [{"periodo": p, "etiqueta": calendario.etiqueta(f, p), "actual": p == actual,
                          "pendiente": p in d["pendientes"], "corta": calendario.etiqueta_corta(f, p),
                          "ejercicio": calendario.etiqueta_ejercicio(calendario.ejercicio_de(f, p)),
                          "cerrado": calendario.ejercicio_de(f, p) in d["cerrados"],
                          "medicion": ser.medicion(d["medidas"][p]) if p in d["medidas"] else None}
                         for p in d["periodos"]]}


@router.get("/indicadores/{indicador_id}/ficha")
def ficha(indicador_id: int, ejercicio: int | None = None, db: Session = Depends(get_db), u: Usuario = Depends(usuario_actual)):
    """Ficha técnica con el contenido de la ficha en papel: definición, responsables, resultados y análisis del ejercicio."""
    ind = indicadores.obtener_visible(db, u, indicador_id)
    anio, disponibles, periodos_ = indicadores.contexto_ficha(db, ind, ejercicio)
    marca_ = parametros.resumen(db)
    return {"indicador": ser.indicador_en_ficha(ind),
            "parametros": {"empresa": marca_["empresa"], "gerencia_emisora": marca_["gerencia_emisora"],
                           "codigo_formato": marca_["codigo_formato"], "logo_url": marca_["logo_url"]},
            "ejercicio": anio, "ejercicio_etiqueta": calendario.etiqueta_ejercicio(anio),
            "ejercicios": [{"valor": e, "etiqueta": calendario.etiqueta_ejercicio(e)} for e in disponibles],
            "periodos": ser.ficha_periodos(periodos_)}


# ---------------------------------------------------------------- fórmulas
@router.post("/formula/validar")
def validar_formula(datos: schemas.FormulaIn, _=Depends(solo_admin)):
    return indicadores.revisar_formula(datos)


@router.post("/formula/probar")
def probar_formula(datos: schemas.ProbarIn, _=Depends(solo_admin)):
    return indicadores.probar_formula(datos)
