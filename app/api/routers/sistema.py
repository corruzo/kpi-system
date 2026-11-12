"""Salud del sistema: solo el Desarrollador (permiso técnico)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...servicios import salud
from ..deps import get_db, requiere_permiso

router = APIRouter(prefix="/api/sistema", tags=["sistema"], dependencies=[Depends(requiere_permiso("sistema.salud"))])


@router.get("/salud")
def resumen(db: Session = Depends(get_db)):
    return salud.resumen(db)


@router.get("/externos")
def externos():
    """Estado público de Supabase y Vercel (se pide aparte porque depende de servicios de terceros)."""
    return salud.estado_externo()
