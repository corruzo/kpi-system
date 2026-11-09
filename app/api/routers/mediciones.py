"""Mediciones: cálculo en vivo, envío de cargas, consulta, revisión del gerente/auditor, reapertura y notas de auditoría."""
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from ... import schemas
from ...dominio import calendario
from ...models import Usuario
from ...servicios import mediciones
from .. import serializadores as ser
from ..deps import AnioConsulta, Desde, IdConsulta, IdRuta, Limite, con_total, escritura, get_db, requiere, usuario_actual

router = APIRouter(prefix="/api", tags=["mediciones"])
quien_carga = requiere("jefe", "admin")
quien_revisa = requiere("gerente", "admin")


@router.post("/calcular")
def calcular(datos: schemas.CalcIn, db: Session = Depends(get_db), u: Usuario = Depends(quien_carga)):
    """Resultado y semáforo de los datos digitados, sin guardar nada."""
    return mediciones.calcular(db, u, datos.indicador_id, datos.valores, datos.periodo)


@router.post("/mediciones", status_code=201)
def cargar(datos: schemas.CargaIn, db: Session = Depends(get_db), u: Usuario = Depends(quien_carga), _=Depends(escritura)):
    return ser.medicion(mediciones.cargar(db, u, datos))


@router.get("/mediciones")
def listar(estado: str | None = None, indicador_id: IdConsulta = None, area_id: IdConsulta = None,
           periodo: str | None = None, semaforo: str | None = None, ejercicio: AnioConsulta = None,
           desde: Desde = 0, limite: Limite = 100, response: Response = None, db: Session = Depends(get_db),
           u: Usuario = Depends(usuario_actual)):
    con_total(response, mediciones.contar(db, u, estado=estado, indicador_id=indicador_id, area_id=area_id, periodo=periodo,
                                          semaforo_=semaforo, ejercicio=ejercicio))
    return [ser.medicion(m) for m in mediciones.listar(
        db, u, estado=estado, indicador_id=indicador_id, area_id=area_id, periodo=periodo, semaforo_=semaforo,
        ejercicio=ejercicio, desde=desde, limite=limite)]


@router.get("/mediciones/resumen-ejercicios")
def resumen_ejercicios(estado: str = "enviado", db: Session = Depends(get_db), u: Usuario = Depends(usuario_actual)):
    """Cuántas cargas hay en un estado por ejercicio fiscal (la bandeja avisa así de lo que queda en otros ejercicios)."""
    return [{"ejercicio": e, "etiqueta": calendario.etiqueta_ejercicio(e), "n": n}
            for e, n in mediciones.resumen_por_ejercicio(db, u, estado)]


@router.post("/mediciones/{medicion_id}/revision")
def revisar(medicion_id: IdRuta, datos: schemas.RevisionIn, db: Session = Depends(get_db), u: Usuario = Depends(quien_revisa),
            _=Depends(escritura)):
    return ser.medicion(mediciones.revisar(db, u, medicion_id, datos.accion, datos.nota))


@router.post("/mediciones/{medicion_id}/reabrir")
def reabrir(medicion_id: IdRuta, datos: schemas.RevisionIn, db: Session = Depends(get_db), u: Usuario = Depends(quien_revisa),
            _=Depends(escritura)):
    return ser.medicion(mediciones.reabrir(db, u, medicion_id, datos.nota))


@router.post("/mediciones/{medicion_id}/notas", status_code=201)
def agregar_nota(medicion_id: IdRuta, datos: schemas.NotaIn, db: Session = Depends(get_db), u: Usuario = Depends(quien_revisa),
                 _=Depends(escritura)):
    return ser.medicion(mediciones.agregar_nota(db, u, medicion_id, datos.texto))
