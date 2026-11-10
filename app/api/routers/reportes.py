"""Reportes en Excel (.xlsx)."""
from fastapi import APIRouter, Depends, File, Response, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from ...models import Usuario
from ...servicios import reportes
from ..deps import AnioConsulta, IdConsulta, get_db, requiere, usuario_actual

router = APIRouter(prefix="/api/reportes", tags=["reportes"])
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _descarga(datos: bytes, nombre: str) -> Response:
    return Response(datos, media_type=XLSX, headers={"Content-Disposition": f'attachment; filename="{nombre}"'})


@router.get("/general.xlsx")
def general(anio: AnioConsulta = None, area_id: IdConsulta = None, estado: str | None = None,
            db: Session = Depends(get_db), u: Usuario = Depends(usuario_actual)):
    """Resumen, mediciones, tendencias, plan de mejora y fichas. El encargado de proceso solo obtiene sus indicadores."""
    return _descarga(*reportes.general(db, u, anio, area_id, estado))


@router.get("/fichas.xlsx")
def fichas(ejercicio: AnioConsulta = None, area_id: IdConsulta = None, indicador_id: IdConsulta = None,
           db: Session = Depends(get_db), u: Usuario = Depends(usuario_actual)):
    """Una hoja por indicador con el formato de la ficha técnica del SGC."""
    return _descarga(*reportes.fichas(db, u, ejercicio, area_id, indicador_id))


@router.post("/verificar")
async def verificar(archivo: UploadFile = File(...), db: Session = Depends(get_db), _: Usuario = Depends(requiere("admin", "gerente"))):
    """Comprueba que un Excel descargado de SPE TPV conserva exactamente lo que el sistema emitió."""
    contenido = await archivo.read(reportes.MAX_BYTES_VERIFICAR + 1)
    return await run_in_threadpool(reportes.verificar, db, contenido)   # openpyxl y la base no deben bloquear el servidor


@router.get("/bitacora.xlsx")
def bitacora(db: Session = Depends(get_db), u: Usuario = Depends(requiere("admin"))):
    return _descarga(*reportes.de_bitacora(db, u))
