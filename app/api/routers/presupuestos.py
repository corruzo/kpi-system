"""Presupuesto anual por indicador y guía de puesta en marcha del administrador."""
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ... import schemas
from ...errores import Invalido
from ...models import Usuario
from ...servicios import ejercicios, presupuestos
from ..deps import escritura, get_db, requiere

router = APIRouter(prefix="/api", tags=["presupuesto"])
quien_presupuesta = requiere("gerente", "admin")


@router.get("/ejercicios/{anio}/presupuesto")
def ver(anio: int, area_id: int | None = None, db: Session = Depends(get_db), _=Depends(quien_presupuesta)):
    """Presupuesto del ejercicio: cada indicador con el valor de cada uno de sus períodos."""
    return {**presupuestos.matriz(db, anio, area_id), "creado": ejercicios.creado(db, anio),
            "estado": ejercicios.estado(db, anio, date.today())}


@router.put("/ejercicios/{anio}/presupuesto/{indicador_id}")
def guardar(anio: int, indicador_id: int, datos: schemas.PresupuestoIn, db: Session = Depends(get_db),
            u: Usuario = Depends(quien_presupuesta), _=Depends(escritura)):
    if datos.valores is not None:
        return presupuestos.guardar(db, u, anio, indicador_id, datos.valores)
    if datos.anual is not None:
        return presupuestos.repartir_anual(db, u, anio, indicador_id, datos.anual, datos.reparto)
    raise Invalido("Indique los valores por período o un valor anual.")


@router.post("/ejercicios/{anio}/presupuesto/copiar")
def copiar(anio: int, datos: schemas.CopiaPresupuestoIn, db: Session = Depends(get_db),
           u: Usuario = Depends(quien_presupuesta), _=Depends(escritura)):
    """Copia el presupuesto de otro ejercicio a los indicadores que aún no tienen el de este."""
    return presupuestos.copiar_de(db, u, anio, datos.desde)


@router.get("/puesta-en-marcha")
def puesta_en_marcha(db: Session = Depends(get_db), _=Depends(requiere("admin"))):
    """Estado de los pasos para arrancar el sistema (organización → indicadores → período → presupuesto → carga)."""
    return presupuestos.avance_de_puesta_en_marcha(db, date.today())
