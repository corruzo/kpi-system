"""Mediciones: cálculo en vivo, envío de cargas, consulta, revisión del gerente/auditor, reapertura y notas de auditoría."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ... import schemas
from ...models import Usuario
from ...servicios import mediciones
from .. import serializadores as ser
from ..deps import escritura, get_db, requiere, usuario_actual

router = APIRouter(prefix="/api", tags=["mediciones"])
quien_carga = requiere("jefe", "admin")
quien_revisa = requiere("gerente", "admin")


@router.post("/calcular")
def calcular(datos: schemas.CalcIn, db: Session = Depends(get_db), u: Usuario = Depends(quien_carga)):
    """Resultado y semáforo de los datos digitados, sin guardar nada."""
    return mediciones.calcular(db, u, datos.indicador_id, datos.valores)


@router.post("/mediciones", status_code=201)
def cargar(datos: schemas.CargaIn, db: Session = Depends(get_db), u: Usuario = Depends(quien_carga), _=Depends(escritura)):
    return ser.medicion(mediciones.cargar(db, u, datos))


@router.get("/mediciones")
def listar(estado: str | None = None, indicador_id: int | None = None, area_id: int | None = None,
           periodo: str | None = None, semaforo: str | None = None, ejercicio: int | None = None,
           desde: int = 0, limite: int = 100, db: Session = Depends(get_db), u: Usuario = Depends(usuario_actual)):
    return [ser.medicion(m) for m in mediciones.listar(
        db, u, estado=estado, indicador_id=indicador_id, area_id=area_id, periodo=periodo, semaforo_=semaforo,
        ejercicio=ejercicio, desde=desde, limite=limite)]


@router.post("/mediciones/{medicion_id}/revision")
def revisar(medicion_id: int, datos: schemas.RevisionIn, db: Session = Depends(get_db), u: Usuario = Depends(quien_revisa),
            _=Depends(escritura)):
    return ser.medicion(mediciones.revisar(db, u, medicion_id, datos.accion, datos.nota))


@router.post("/mediciones/{medicion_id}/reabrir")
def reabrir(medicion_id: int, datos: schemas.RevisionIn, db: Session = Depends(get_db), u: Usuario = Depends(quien_revisa),
            _=Depends(escritura)):
    return ser.medicion(mediciones.reabrir(db, u, medicion_id, datos.nota))


@router.post("/mediciones/{medicion_id}/notas", status_code=201)
def agregar_nota(medicion_id: int, datos: schemas.NotaIn, db: Session = Depends(get_db), u: Usuario = Depends(quien_revisa),
                 _=Depends(escritura)):
    return ser.medicion(mediciones.agregar_nota(db, u, medicion_id, datos.texto))
