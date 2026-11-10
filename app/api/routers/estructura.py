"""Estructura de la empresa: árbol de gerencias → departamentos → jefaturas."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ... import schemas
from ...models import Usuario
from ...servicios import estructura
from .. import serializadores as ser
from ..deps import IdRuta, escritura, get_db, requiere_permiso

router = APIRouter(prefix="/api/unidades", tags=["estructura"])
gestiona = requiere_permiso("estructura.gestionar")


def _uno(db: Session, nodo) -> dict:
    return ser.unidad(nodo, estructura.nombres_de_ruta(estructura.todas(db))[nodo.id])


@router.get("")
def listar(db: Session = Depends(get_db), _=Depends(requiere_permiso("estructura.ver"))):
    """El árbol completo en orden (cada padre antes que sus hijos), con cuántas personas e indicadores tiene cada nodo."""
    nodos = estructura.todas(db)
    rutas, (personas, indicadores) = estructura.nombres_de_ruta(nodos), estructura.conteos(db)
    return [ser.unidad(n, rutas[n.id], personas.get(n.id, 0), indicadores.get(n.id, 0)) for n in nodos]


@router.post("", status_code=201)
def crear(datos: schemas.UnidadIn, db: Session = Depends(get_db), u: Usuario = Depends(gestiona), _=Depends(escritura)):
    return _uno(db, estructura.crear(db, u, datos.nombre, datos.nivel, datos.padre_id))


@router.put("/{unidad_id}")
def renombrar(unidad_id: IdRuta, datos: schemas.UnidadEdit, db: Session = Depends(get_db), u: Usuario = Depends(gestiona),
              _=Depends(escritura)):
    return _uno(db, estructura.renombrar(db, u, unidad_id, datos.nombre))


@router.post("/{unidad_id}/mover")
def mover(unidad_id: IdRuta, datos: schemas.MoverIn, db: Session = Depends(get_db), u: Usuario = Depends(gestiona),
          _=Depends(escritura)):
    """Cuelga el nodo, con todo su subárbol, de otro padre del nivel que le corresponde."""
    return _uno(db, estructura.mover(db, u, unidad_id, datos.padre_id))


@router.delete("/{unidad_id}")
def eliminar(unidad_id: IdRuta, db: Session = Depends(get_db), u: Usuario = Depends(gestiona), _=Depends(escritura)):
    estructura.eliminar(db, u, unidad_id)
    return {"ok": True}
