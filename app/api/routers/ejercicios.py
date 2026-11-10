"""Ejercicios fiscales (listado, verificación, cierre y reapertura) y panel de análisis."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ... import schemas
from ...dominio import calendario
from ...models import Ejercicio, Usuario
from ...servicios import ejercicios, panel
from .. import serializadores as ser
from ..deps import AnioConsulta, AnioRuta, IdConsulta, escritura, get_db, requiere_permiso

router = APIRouter(prefix="/api", tags=["ejercicios fiscales"])


@router.get("/ejercicios")
def listar(detalle: bool = False, db: Session = Depends(get_db), u: Usuario = Depends(requiere_permiso("ejercicios.ver"))):
    """Ejercicios conocidos. Con `detalle`: resultados de cada uno, calculados solo con lo que la persona puede ver."""
    hoy, salida = calendario.hoy(), []
    filas = {e.anio: e for e in db.scalars(select(Ejercicio))}   # una consulta para todos (antes, una por ejercicio)
    for anio in ejercicios.anios_conocidos(db, hoy, filas):
        item = ser.ejercicio(ejercicios.descripcion(db, anio, hoy, filas))
        if detalle:
            item.update(ejercicios.resultados(db, anio, hoy, u))
        salida.append(item)
    return {"vigente": calendario.ejercicio_de_fecha(hoy), "ejercicios": salida}


@router.post("/ejercicios", status_code=201)
def crear(datos: schemas.EjercicioIn, db: Session = Depends(get_db), u: Usuario = Depends(requiere_permiso("ejercicios.crear")),
          _=Depends(escritura)):
    """Paso 1 del flujo anual: crea el período fiscal (hay que crearlo antes de fijar metas o cargar datos)."""
    ejercicios.crear(db, u, datos.anio, datos.nota)
    return ser.ejercicio(ejercicios.descripcion(db, datos.anio, calendario.hoy()))


@router.get("/ejercicios/{anio}/verificacion")
def verificar(anio: AnioRuta, db: Session = Depends(get_db), _=Depends(requiere_permiso("ejercicios.cerrar"))):
    """Lista de comprobación previa al cierre."""
    v = ejercicios.verificar(db, anio)
    return {**ser.ejercicio(v["descripcion"]), "terminado": v["terminado"], "pendientes": v["pendientes"],
            "faltantes": v["faltantes"], "total_faltantes": v["total_faltantes"], "resumen": v["foto"]["resumen"],
            "puede_cerrar": v["puede_cerrar"]}


@router.post("/ejercicios/{anio}/cerrar")
def cerrar(anio: AnioRuta, datos: schemas.CierreIn, db: Session = Depends(get_db), u: Usuario = Depends(requiere_permiso("ejercicios.cerrar")),
           _=Depends(escritura)):
    """Cierra el ejercicio: queda de solo lectura y se guarda una foto de sus resultados."""
    ejercicios.cerrar(db, u, anio, datos.nota, datos.aceptar_faltantes)
    return ser.ejercicio(ejercicios.descripcion(db, anio, calendario.hoy()))


@router.post("/ejercicios/{anio}/reabrir")
def reabrir(anio: AnioRuta, datos: schemas.ReaperturaIn, db: Session = Depends(get_db),
            u: Usuario = Depends(requiere_permiso("ejercicios.reabrir")),
            _=Depends(escritura)):
    ejercicios.reabrir(db, u, anio, datos.nota)
    return ser.ejercicio(ejercicios.descripcion(db, anio, calendario.hoy()))


@router.get("/dashboard")
def tablero(nodo_id: IdConsulta = None, ejercicio: AnioConsulta = None, db: Session = Depends(get_db),
            u: Usuario = Depends(requiere_permiso("panel.ver"))):
    """Panel de análisis de un ejercicio (por defecto el vigente), con comparativo contra el anterior. Solo incluye los
    indicadores que la persona puede ver."""
    anio = ejercicio or calendario.ejercicio_de_fecha(calendario.hoy())
    p = panel.construir(db, u, anio, nodo_id)
    foto = p["foto"]
    return {"resumen": foto["resumen"], "por_area": foto["por_area"],
            "indicadores": [ser.fila_del_panel(f) for f in foto["filas"]],
            "ejercicio": {**ser.ejercicio(p["descripcion"]), "avance": p["avance"], "meses": p["meses"]},
            "anterior": p["anterior"], "atencion": p["atencion"]}
