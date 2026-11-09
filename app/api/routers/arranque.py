"""Arranque: TODO lo que la interfaz necesita al ingresar, en UNA sola petición.

Antes se hacían unas 8 peticiones, varias encadenadas; en un servidor remoto (función serverless + base de datos en la
nube) cada una paga su propio viaje de ida y vuelta. Reutiliza las funciones de cada router, de modo que cada dato
sigue pasando por su propia regla de acceso (un encargado de proceso recibe solo lo suyo)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...dominio import calendario
from ...models import Usuario
from ...servicios import mediciones, parametros
from .. import serializadores as ser
from ..deps import AnioConsulta, get_db, usuario_actual
from . import ejercicios as r_ejercicios
from . import indicadores as r_indicadores
from . import organizacion as r_org
from . import presupuestos as r_presupuestos

router = APIRouter(prefix="/api", tags=["sesión"])


def elegir_ejercicio(lista: list[dict], vigente: int, preferido: int | None) -> int:
    """Misma regla que aplica la interfaz: el recordado si ya está creado, si no el vigente, si no el primero creado."""
    creados = [e["anio"] for e in lista if e["creado"]]
    if preferido in creados:
        return preferido
    return vigente if vigente in creados else (creados[0] if creados else vigente)


@router.get("/arranque")
def arranque(ejercicio: AnioConsulta = None, db: Session = Depends(get_db), u: Usuario = Depends(usuario_actual)):
    ej = r_ejercicios.listar(detalle=False, db=db, u=u)
    sel = elegir_ejercicio(ej["ejercicios"], ej["vigente"], ejercicio)
    datos = {"usuario": ser.usuario(u), "parametros": parametros.resumen(db), "ejercicios": ej, "ejercicio": sel,
             "indicadores": []}
    if u.rol in ("jefe", "admin"):   # quienes cargan datos eligen entre sus indicadores; los demás los piden paginados en «Indicadores»
        datos["indicadores"] = r_indicadores.listar(ejercicio=sel, db=db, u=u)
    if u.rol != "jefe":
        datos["areas"] = r_org.listar_areas(db=db)
    if u.rol in ("gerente", "admin"):
        # solo cantidades: la lista de cargas por aprobar se pide paginada al abrir la bandeja
        datos["bandeja_total"] = mediciones.contar(db, u, estado="enviado")
        datos["bandeja_ejercicios"] = [{"ejercicio": e, "etiqueta": calendario.etiqueta_ejercicio(e), "n": n} for e, n in mediciones.resumen_por_ejercicio(db, u, "enviado")]
        datos["resumen"] = r_ejercicios.tablero(ejercicio=sel, db=db)["resumen"]   # lo que muestra la pantalla de inicio
        datos["catalogos"] = r_org.listar_catalogos(db=db)
    if u.rol == "admin":
        datos["marcha"] = r_presupuestos.puesta_en_marcha(db=db)
    return datos
