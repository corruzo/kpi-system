"""Importación de fichas históricas desde Excel (permiso `importacion.usar`)."""
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from ... import schemas
from ...models import Usuario
from ...servicios import importacion, lector_excel
from ..deps import escritura, get_db, requiere_permiso

router = APIRouter(prefix="/api/importar", tags=["importación"])


@router.post("/excel")
async def previsualizar(archivo: UploadFile = File(...), db: Session = Depends(get_db), _=Depends(requiere_permiso("importacion.usar"))):
    """Lee un libro con fichas técnicas (una hoja por indicador) y devuelve una vista previa; no guarda nada."""
    contenido = await archivo.read(lector_excel.MAX_BYTES + 1)
    return await run_in_threadpool(importacion.previsualizar, db, contenido, archivo.filename or "")


@router.post("/confirmar", status_code=201)
def confirmar(datos: schemas.ImpIn, db: Session = Depends(get_db), u: Usuario = Depends(requiere_permiso("importacion.usar")),
              _=Depends(escritura)):
    """Crea indicadores, mediciones históricas aprobadas y listas de apoyo; todo o nada."""
    return importacion.confirmar(db, u, datos)
