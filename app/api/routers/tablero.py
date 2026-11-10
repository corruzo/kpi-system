"""Panel de control: vista completa por rango de fechas, granularidad y filtros (permiso `panel.ver`; cada quien, su alcance)."""
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...dominio import calendario
from ...models import Usuario
from ...servicios import tablero
from ..deps import IdConsulta, get_db, requiere_permiso

router = APIRouter(prefix="/api", tags=["panel de control"])
Mes = Annotated[str | None, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="AAAA-MM")]


@router.get("/tablero")
def ver(desde: Mes = None, hasta: Mes = None, agrupar: Literal[tuple(tablero.AGRUPACIONES)] = "mes", nodo_id: IdConsulta = None,
        frecuencia: Literal[tuple(calendario.FRECUENCIAS)] | None = None,
        seguimiento: Literal["proceso", "objetivo", "proveedor"] | None = None, indicador_id: IdConsulta = None,
        solo_aprobadas: bool = False, dimension: Literal[tuple(tablero.DIMENSIONES)] = "area",
        db: Session = Depends(get_db), u: Usuario = Depends(requiere_permiso("panel.ver"))):
    """Sin fechas se usa el ejercicio fiscal vigente completo. Solo incluye los indicadores que la persona puede ver."""
    if not (desde and hasta):
        ini, fin = calendario.limites(calendario.ejercicio_de_fecha(calendario.hoy()))
        desde, hasta = desde or f"{ini.year}-{ini.month:02d}", hasta or f"{fin.year}-{fin.month:02d}"
    return tablero.construir(db, u, desde=desde, hasta=hasta, agrupar=agrupar, nodo_id=nodo_id, frecuencia=frecuencia,
                             seguimiento=seguimiento, indicador_id=indicador_id, solo_aprobadas=solo_aprobadas, dimension=dimension)
