"""Indicadores: fichas técnicas (consulta, alta, edición, baja), períodos de carga, ficha por ejercicio y fórmulas."""
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
def listar(db: Session = Depends(get_db), u: Usuario = Depends(usuario_actual)):
    return [ser.indicador_con_pendientes(*fila) for fila in indicadores.listar(db, u)]


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
def periodos(indicador_id: int, db: Session = Depends(get_db), u: Usuario = Depends(usuario_actual)):
    d = indicadores.periodos_de_carga(db, u, indicador_id)
    f = d["indicador"].frecuencia
    return {"sugerido": d["pendientes"][0] if d["pendientes"] else None,
            "periodos": [{"periodo": p, "etiqueta": calendario.etiqueta(f, p), "actual": orden == 0,
                          "pendiente": p in d["pendientes"], "corta": calendario.etiqueta_corta(f, p),
                          "ejercicio": calendario.etiqueta_ejercicio(calendario.ejercicio_de(f, p)),
                          "cerrado": calendario.ejercicio_de(f, p) in d["cerrados"],
                          "medicion": ser.medicion(d["medidas"][p]) if p in d["medidas"] else None}
                         for orden, p in enumerate(d["periodos"])]}


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
