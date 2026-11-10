"""Metas por indicador y período (antes «presupuesto») y guía de puesta en marcha."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ... import schemas
from ...dominio import calendario
from ...errores import Invalido
from ...models import Usuario
from ...servicios import ejercicios, metas
from ..deps import AnioRuta, IdConsulta, IdRuta, escritura, get_db, requiere_permiso

router = APIRouter(prefix="/api", tags=["metas"])
fija = requiere_permiso("metas.cargar")


@router.get("/ejercicios/{anio}/metas")
def ver(anio: AnioRuta, nodo_id: IdConsulta = None, db: Session = Depends(get_db), u: Usuario = Depends(requiere_permiso("metas.ver"))):
    """Metas del ejercicio de los indicadores que la persona ve: cada uno con el valor de sus períodos y si puede cambiarlo."""
    return {**metas.matriz(db, u, anio, nodo_id), "creado": ejercicios.creado(db, anio),
            "estado": ejercicios.estado(db, anio, calendario.hoy())}


@router.put("/ejercicios/{anio}/metas/{indicador_id}")
def guardar(anio: AnioRuta, indicador_id: IdRuta, datos: schemas.MetaIn, db: Session = Depends(get_db),
            u: Usuario = Depends(fija), _=Depends(escritura)):
    """Meta por período o anual repartida. Solo indicadores propios y de quienes están debajo (el Coordinador SGC, siempre)."""
    if datos.valores is not None:
        return metas.guardar(db, u, anio, indicador_id, datos.valores)
    if datos.anual is not None:
        return metas.repartir_anual(db, u, anio, indicador_id, datos.anual, datos.reparto)
    raise Invalido("Indique los valores por período o un valor anual.")


@router.post("/ejercicios/{anio}/metas/copiar")
def copiar(anio: AnioRuta, datos: schemas.CopiaMetaIn, db: Session = Depends(get_db),
           u: Usuario = Depends(requiere_permiso("metas.copiar")), _=Depends(escritura)):
    """Copia las metas de otro ejercicio a los indicadores que aún no tienen las de este (los que la persona puede fijar)."""
    return metas.copiar_de(db, u, anio, datos.desde)


@router.get("/puesta-en-marcha")
def puesta_en_marcha(db: Session = Depends(get_db), u: Usuario = Depends(requiere_permiso("sistema.puesta_en_marcha"))):
    """Estado de los pasos para arrancar el sistema (cuentas → estructura → personas → indicadores → período → metas → carga)."""
    return metas.avance_de_puesta_en_marcha(db, u, calendario.hoy())
