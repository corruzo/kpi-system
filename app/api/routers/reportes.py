"""Reportes en Excel (.xlsx)."""
from fastapi import APIRouter, Depends, File, Response, UploadFile
from sqlalchemy.orm import Session

from ...models import Usuario
from ...servicios import reportes
from ..deps import get_db, requiere, usuario_actual

router = APIRouter(prefix="/api/reportes", tags=["reportes"])
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _descarga(datos: bytes, nombre: str) -> Response:
    return Response(datos, media_type=XLSX, headers={"Content-Disposition": f'attachment; filename="{nombre}"'})


@router.get("/general.xlsx")
def general(anio: int | None = None, area_id: int | None = None, estado: str | None = None,
            db: Session = Depends(get_db), u: Usuario = Depends(usuario_actual)):
    """Resumen, mediciones, tendencias, plan de mejora y fichas. El jefe solo obtiene su área."""
    return _descarga(*reportes.general(db, u, anio, area_id, estado))


@router.get("/fichas.xlsx")
def fichas(ejercicio: int | None = None, area_id: int | None = None, indicador_id: int | None = None,
           db: Session = Depends(get_db), u: Usuario = Depends(usuario_actual)):
    """Una hoja por indicador con el formato de la ficha técnica del SGC."""
    return _descarga(*reportes.fichas(db, u, ejercicio, area_id, indicador_id))


@router.post("/verificar")
async def verificar(archivo: UploadFile = File(...), db: Session = Depends(get_db), _: Usuario = Depends(requiere("admin", "gerente"))):
    """Comprueba que un Excel descargado del SIGT conserva exactamente lo que el sistema emitió."""
    return reportes.verificar(db, await archivo.read(10_000_000))


@router.get("/bitacora.xlsx")
def bitacora(db: Session = Depends(get_db), u: Usuario = Depends(requiere("admin"))):
    return _descarga(*reportes.de_bitacora(db, u))
