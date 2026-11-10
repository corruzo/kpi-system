"""Mediciones: cálculo en vivo, envío de cargas, consulta, bandeja y aprobación jerárquica, reapertura y notas de auditoría."""
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from ... import schemas
from ...dominio import calendario
from ...models import Usuario
from ...servicios import mediciones
from .. import serializadores as ser
from ..deps import AnioConsulta, Desde, IdConsulta, IdRuta, Limite, con_total, escritura, get_db, requiere_permiso

router = APIRouter(prefix="/api", tags=["mediciones"])
carga = requiere_permiso("cargas.cargar")
ve = requiere_permiso("cargas.ver")
aprueba = requiere_permiso("cargas.aprobar")


@router.post("/calcular")
def calcular(datos: schemas.CalcIn, db: Session = Depends(get_db), u: Usuario = Depends(carga)):
    """Resultado y semáforo de los datos digitados, sin guardar nada (solo quien carga ese indicador)."""
    return mediciones.calcular(db, u, datos.indicador_id, datos.valores, datos.periodo)


@router.post("/mediciones", status_code=201)
def cargar(datos: schemas.CargaIn, db: Session = Depends(get_db), u: Usuario = Depends(carga), _=Depends(escritura)):
    return ser.medicion(mediciones.cargar(db, u, datos))


@router.get("/mediciones")
def listar(estado: str | None = None, indicador_id: IdConsulta = None, nodo_id: IdConsulta = None,
           periodo: str | None = None, semaforo: str | None = None, ejercicio: AnioConsulta = None,
           desde: Desde = 0, limite: Limite = 100, response: Response = None, db: Session = Depends(get_db),
           u: Usuario = Depends(ve)):
    """Cargas de los indicadores que la persona puede ver (su ámbito y sus asignados)."""
    con_total(response, mediciones.contar(db, u, estado=estado, indicador_id=indicador_id, nodo_id=nodo_id, periodo=periodo,
                                          semaforo_=semaforo, ejercicio=ejercicio))
    return [ser.medicion(m) for m in mediciones.listar(
        db, u, estado=estado, indicador_id=indicador_id, nodo_id=nodo_id, periodo=periodo, semaforo_=semaforo,
        ejercicio=ejercicio, desde=desde, limite=limite)]


@router.get("/mediciones/resumen-ejercicios")
def resumen_ejercicios(estado: str = "enviado", db: Session = Depends(get_db), u: Usuario = Depends(ve)):
    """Cuántas cargas visibles hay en un estado por ejercicio fiscal."""
    return [{"ejercicio": e, "etiqueta": calendario.etiqueta_ejercicio(e), "n": n}
            for e, n in mediciones.resumen_por_ejercicio(db, u, estado)]


def resumen_de_bandeja(db: Session, u: Usuario) -> dict:
    por_ejercicio = mediciones.bandeja_por_ejercicio(db, u)
    return {"total": sum(n for _, n in por_ejercicio),
            "ejercicios": [{"ejercicio": e, "etiqueta": calendario.etiqueta_ejercicio(e), "n": n} for e, n in por_ejercicio]}


@router.get("/bandeja")
def bandeja(ejercicio: AnioConsulta = None, desde: Desde = 0, limite: Limite = 100, response: Response = None,
            db: Session = Depends(get_db), u: Usuario = Depends(aprueba)):
    """Cargas enviadas que a ESTA persona le corresponde aprobar: es el superior más cercano de quien cargó, o el
    Coordinador SGC (respaldo). Nunca incluye cargas propias."""
    todas = mediciones.bandeja(db, u, ejercicio)
    con_total(response, len(todas))
    return [ser.medicion(m) for m in todas[desde:desde + limite]]


@router.get("/bandeja/resumen")
def bandeja_resumen(db: Session = Depends(get_db), u: Usuario = Depends(aprueba)):
    """Cuántas cargas esperan la aprobación de esta persona, en total y por ejercicio fiscal."""
    return resumen_de_bandeja(db, u)


@router.post("/mediciones/{medicion_id}/revision")
def revisar(medicion_id: IdRuta, datos: schemas.RevisionIn, db: Session = Depends(get_db), u: Usuario = Depends(aprueba),
            _=Depends(escritura)):
    return ser.medicion(mediciones.revisar(db, u, medicion_id, datos.accion, datos.nota))


@router.post("/mediciones/{medicion_id}/reabrir")
def reabrir(medicion_id: IdRuta, datos: schemas.RevisionIn, db: Session = Depends(get_db),
            u: Usuario = Depends(requiere_permiso("cargas.reabrir")), _=Depends(escritura)):
    return ser.medicion(mediciones.reabrir(db, u, medicion_id, datos.nota))


@router.post("/mediciones/{medicion_id}/notas", status_code=201)
def agregar_nota(medicion_id: IdRuta, datos: schemas.NotaIn, db: Session = Depends(get_db),
                 u: Usuario = Depends(requiere_permiso("cargas.notas")), _=Depends(escritura)):
    return ser.medicion(mediciones.agregar_nota(db, u, medicion_id, datos.texto))
