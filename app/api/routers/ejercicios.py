"""Ejercicios fiscales (listado, verificación, cierre y reapertura) y panel de análisis."""
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ... import schemas
from ...dominio import calendario
from ...errores import Prohibido
from ...models import Usuario
from ...servicios import ejercicios, panel
from .. import serializadores as ser
from ..deps import escritura, get_db, requiere, usuario_actual

router = APIRouter(prefix="/api", tags=["ejercicios fiscales"])


@router.get("/ejercicios")
def listar(detalle: bool = False, db: Session = Depends(get_db), u: Usuario = Depends(usuario_actual)):
    """Ejercicios conocidos. Con `detalle` (gerente/admin): resultados de cada uno."""
    if detalle and u.rol == "jefe":
        raise Prohibido("No tiene permisos para esta acción.")
    hoy, salida = date.today(), []
    for anio in ejercicios.anios_conocidos(db, hoy):
        item = ser.ejercicio(ejercicios.descripcion(db, anio, hoy))
        if detalle:
            item.update(ejercicios.resultados(db, anio, hoy))
        salida.append(item)
    return {"vigente": calendario.ejercicio_de_fecha(hoy), "ejercicios": salida}


@router.get("/ejercicios/{anio}/verificacion")
def verificar(anio: int, db: Session = Depends(get_db), _=Depends(requiere("gerente", "admin"))):
    """Lista de comprobación previa al cierre."""
    v = ejercicios.verificar(db, anio)
    return {**ser.ejercicio(v["descripcion"]), "terminado": v["terminado"], "pendientes": v["pendientes"],
            "faltantes": v["faltantes"], "total_faltantes": v["total_faltantes"], "resumen": v["foto"]["resumen"],
            "puede_cerrar": v["puede_cerrar"]}


@router.post("/ejercicios/{anio}/cerrar")
def cerrar(anio: int, datos: schemas.CierreIn, db: Session = Depends(get_db), u: Usuario = Depends(requiere("admin")),
           _=Depends(escritura)):
    """Cierra el ejercicio: queda de solo lectura y se guarda una foto de sus resultados."""
    ejercicios.cerrar(db, u, anio, datos.nota, datos.aceptar_faltantes)
    return ser.ejercicio(ejercicios.descripcion(db, anio, date.today()))


@router.post("/ejercicios/{anio}/reabrir")
def reabrir(anio: int, datos: schemas.ReaperturaIn, db: Session = Depends(get_db), u: Usuario = Depends(requiere("admin")),
            _=Depends(escritura)):
    ejercicios.reabrir(db, u, anio, datos.nota)
    return ser.ejercicio(ejercicios.descripcion(db, anio, date.today()))


@router.get("/dashboard")
def tablero(area_id: int | None = None, ejercicio: int | None = None, db: Session = Depends(get_db),
            _=Depends(requiere("gerente", "admin"))):
    """Panel de análisis de un ejercicio (por defecto el vigente), con comparativo contra el anterior."""
    anio = ejercicio or calendario.ejercicio_de_fecha(date.today())
    p = panel.construir(db, anio, area_id)
    foto = p["foto"]
    return {"resumen": foto["resumen"], "por_area": foto["por_area"],
            "indicadores": [ser.fila_del_panel(f) for f in foto["filas"]],
            "ejercicio": {**ser.ejercicio(p["descripcion"]), "avance": p["avance"], "meses": p["meses"]},
            "anterior": p["anterior"], "atencion": p["atencion"]}
