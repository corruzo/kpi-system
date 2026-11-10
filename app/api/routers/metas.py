"""Meta anual por indicador y guía de puesta en marcha del administrador."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ... import schemas
from ...dominio import calendario
from ...errores import Invalido
from ...models import Usuario
from ...servicios import ejercicios, metas
from ..deps import AnioRuta, IdConsulta, IdRuta, escritura, get_db, requiere

router = APIRouter(prefix="/api", tags=["meta"])
quien_fija_metas = requiere("gerente", "admin")


@router.get("/ejercicios/{anio}/metas")
def ver(anio: AnioRuta, area_id: IdConsulta = None, db: Session = Depends(get_db), _=Depends(quien_fija_metas)):
    """Meta del ejercicio: cada indicador con el valor de cada uno de sus períodos."""
    return {**metas.matriz(db, anio, area_id), "creado": ejercicios.creado(db, anio),
            "estado": ejercicios.estado(db, anio, calendario.hoy())}


@router.put("/ejercicios/{anio}/metas/{indicador_id}")
def guardar(anio: AnioRuta, indicador_id: IdRuta, datos: schemas.MetaIn, db: Session = Depends(get_db),
            u: Usuario = Depends(quien_fija_metas), _=Depends(escritura)):
    if datos.valores is not None:
        return metas.guardar(db, u, anio, indicador_id, datos.valores)
    if datos.anual is not None:
        return metas.repartir_anual(db, u, anio, indicador_id, datos.anual, datos.reparto)
    raise Invalido("Indique los valores por período o un valor anual.")


@router.post("/ejercicios/{anio}/metas/copiar")
def copiar(anio: AnioRuta, datos: schemas.CopiaMetaIn, db: Session = Depends(get_db),
           u: Usuario = Depends(quien_fija_metas), _=Depends(escritura)):
    """Copia la meta de otro ejercicio a los indicadores que aún no tienen el de este."""
    return metas.copiar_de(db, u, anio, datos.desde)


@router.get("/puesta-en-marcha")
def puesta_en_marcha(db: Session = Depends(get_db), _=Depends(requiere("admin"))):
    """Estado de los pasos para arrancar el sistema (organización → indicadores → período → meta → carga)."""
    return metas.avance_de_puesta_en_marcha(db, calendario.hoy())
