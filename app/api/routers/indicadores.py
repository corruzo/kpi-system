"""Indicadores: fichas técnicas (consulta, alta, edición, baja), períodos de carga, ficha por ejercicio y fórmulas."""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from ... import schemas
from ...dominio import calendario
from ...errores import Invalido
from ...models import Usuario
from ...servicios import indicadores, parametros
from .. import serializadores as ser
from ..deps import AnioConsulta, Desde, IdConsulta, IdRuta, Limite, con_total, escritura, get_db, requiere_permiso

router = APIRouter(prefix="/api", tags=["indicadores"])
ve = requiere_permiso("indicadores.ver")


@router.get("/indicadores")
def listar(ejercicio: AnioConsulta = None, gestion: bool = False, cargables: bool = False, q: str | None = None,
           nodo_id: IdConsulta = None, frecuencia: str | None = None, activo: bool | None = None, desde: Desde = 0,
           limite: Limite | None = None, response: Response = None, db: Session = Depends(get_db), u: Usuario = Depends(ve)):
    """Indicadores que la persona puede ver, con sus períodos pendientes del ejercicio pedido (y cuántos quedan en otros).
    Con `limite` se pagina (el total va en `X-Total-Count`); `gestion` incluye los archivados de su ámbito o propios;
    `cargables` deja solo aquellos a los que puede cargar datos; `nodo_id` abarca todo el subárbol del nodo."""
    filtros = {"gestion": gestion, "q": q, "nodo_id": nodo_id, "frecuencia": frecuencia, "activo": activo, "cargables": cargables}
    if limite is not None:
        con_total(response, indicadores.contar(db, u, **filtros))
    return [ser.indicador_con_pendientes(*fila, u) for fila in indicadores.listar(db, u, ejercicio, desde=desde, limite=limite, **filtros)]


@router.get("/indicadores/codigo-sugerido")
def codigo_sugerido(nodo_id: IdConsulta, db: Session = Depends(get_db), _=Depends(requiere_permiso("indicadores.crear"))):
    """Código que recibirá el próximo indicador del nodo (el definitivo lo asigna el servidor al guardar)."""
    if nodo_id is None:
        raise Invalido("Indique el nodo de la estructura.")
    return {"codigo": indicadores.sugerir_codigo(db, nodo_id)}


@router.post("/indicadores", status_code=201)
def crear(datos: schemas.IndicadorIn, db: Session = Depends(get_db), u: Usuario = Depends(requiere_permiso("indicadores.crear")),
          _=Depends(escritura)):
    """Crea la ficha y la asigna: solo a sí mismo o a personas debajo de él (los roles de sistema, sin restricción)."""
    return ser.indicador(indicadores.crear(db, u, datos), u)


@router.put("/indicadores/{indicador_id}")
def editar(indicador_id: IdRuta, datos: schemas.IndicadorIn, db: Session = Depends(get_db),
           u: Usuario = Depends(requiere_permiso("indicadores.editar")), _=Depends(escritura)):
    """Cambia la ficha. Solo el responsable del indicador (404 si no lo ve; 403 si lo ve pero no es suyo)."""
    return ser.indicador(indicadores.editar(db, u, indicador_id, datos), u)


@router.put("/indicadores/{indicador_id}/asignacion")
def asignar(indicador_id: IdRuta, datos: schemas.AsignacionIndicadorIn, db: Session = Depends(get_db),
            u: Usuario = Depends(requiere_permiso("indicadores.asignar")), _=Depends(escritura)):
    """Nodo, responsable y quienes cargan."""
    return ser.indicador(indicadores.asignar(db, u, indicador_id, datos.nodo_id, datos.responsable_id, datos.cargadores), u)


@router.post("/indicadores/{indicador_id}/archivar")
def archivar(indicador_id: IdRuta, db: Session = Depends(get_db), u: Usuario = Depends(requiere_permiso("indicadores.archivar")),
             _=Depends(escritura)):
    return ser.indicador(indicadores.archivar(db, u, indicador_id, True), u)


@router.post("/indicadores/{indicador_id}/restaurar")
def restaurar(indicador_id: IdRuta, db: Session = Depends(get_db), u: Usuario = Depends(requiere_permiso("indicadores.archivar")),
              _=Depends(escritura)):
    return ser.indicador(indicadores.archivar(db, u, indicador_id, False), u)


@router.delete("/indicadores/{indicador_id}")
def eliminar(indicador_id: IdRuta, db: Session = Depends(get_db), u: Usuario = Depends(requiere_permiso("indicadores.eliminar")),
             _=Depends(escritura)):
    """Borra un indicador sin cargas. Con cargas responde 409: hay que archivarlo para conservar la trazabilidad."""
    indicadores.eliminar(db, u, indicador_id)
    return {"ok": True}


@router.get("/indicadores/{indicador_id}/periodos")
def periodos(indicador_id: IdRuta, ejercicio: AnioConsulta = None, db: Session = Depends(get_db),
             u: Usuario = Depends(requiere_permiso("cargas.ver"))):
    """Períodos cargables de un ejercicio fiscal (por defecto el vigente), del más reciente al más antiguo."""
    d = indicadores.periodos_de_carga(db, u, indicador_id, ejercicio)
    f = d["indicador"].frecuencia
    actual = calendario.periodo_actual(f, calendario.hoy())
    return {"sugerido": d["pendientes"][0] if d["pendientes"] else None, "ejercicio": d["ejercicio"],
            "pendientes_otros": [{"ejercicio": a, "etiqueta": calendario.etiqueta_ejercicio(a), "n": n}
                                 for a, n in sorted(d["pendientes_otros"].items())],
            "periodos": [{"periodo": p, "etiqueta": calendario.etiqueta(f, p), "actual": p == actual,
                          "pendiente": p in d["pendientes"], "corta": calendario.etiqueta_corta(f, p),
                          "ejercicio": calendario.etiqueta_ejercicio(calendario.ejercicio_de(f, p)),
                          "cerrado": calendario.ejercicio_de(f, p) in d["cerrados"],
                          "meta": d["metas"].get(p), "creado": d["creado"],
                          "medicion": ser.medicion(d["medidas"][p]) if p in d["medidas"] else None}
                         for p in d["periodos"]]}


@router.get("/indicadores/{indicador_id}/ficha")
def ficha(indicador_id: IdRuta, ejercicio: AnioConsulta = None, db: Session = Depends(get_db), u: Usuario = Depends(ve)):
    """Ficha técnica con el contenido de la ficha en papel: definición, responsables, resultados y análisis del ejercicio."""
    ind = indicadores.obtener_visible(db, u, indicador_id)
    anio, disponibles, periodos_ = indicadores.contexto_ficha(db, ind, ejercicio)
    marca_ = parametros.resumen(db)
    return {"indicador": ser.indicador_en_ficha(ind, u),
            "parametros": {"empresa": marca_["empresa"], "gerencia_emisora": marca_["gerencia_emisora"],
                           "codigo_formato": marca_["codigo_formato"], "logo_url": marca_["logo_url"]},
            "ejercicio": anio, "ejercicio_etiqueta": calendario.etiqueta_ejercicio(anio),
            "ejercicios": [{"valor": e, "etiqueta": calendario.etiqueta_ejercicio(e)} for e in disponibles],
            "periodos": ser.ficha_periodos(periodos_)}


# ---------------------------------------------------------------- fórmulas
@router.post("/formula/validar")
def validar_formula(datos: schemas.FormulaIn, _=Depends(requiere_permiso("formulas.probar"))):
    return indicadores.revisar_formula(datos)


@router.post("/formula/probar")
def probar_formula(datos: schemas.ProbarIn, _=Depends(requiere_permiso("formulas.probar"))):
    return indicadores.probar_formula(datos)
