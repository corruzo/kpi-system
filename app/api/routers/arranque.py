"""Arranque: TODO lo que la interfaz necesita al ingresar, en UNA sola petición.

En un servidor remoto (función serverless + base de datos en la nube) cada petición paga su propio viaje de ida y vuelta.
Aquí se entrega únicamente lo que el rol de la persona permite: cada bloque se incluye solo si tiene el permiso
correspondiente y pasa por la misma regla de alcance que su propia ruta. Una cuenta sin rol recibe solo su perfil y la marca.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...dominio import calendario
from ...models import Indicador, Usuario
from ...servicios import acceso, ejercicios, estructura, indicadores, metas, organizacion, parametros
from .. import serializadores as ser
from ..deps import AnioConsulta, cuenta_propia, get_db
from . import ejercicios as r_ejercicios
from . import mediciones as r_mediciones

router = APIRouter(prefix="/api", tags=["sesión"])


def elegir_ejercicio(lista: list[dict], vigente: int, preferido: int | None) -> int:
    """Misma regla que aplica la interfaz: el recordado si ya está creado, si no el vigente, si no el primero creado."""
    creados = [e["anio"] for e in lista if e["creado"]]
    if preferido in creados:
        return preferido
    return vigente if vigente in creados else (creados[0] if creados else vigente)


def unidades_visibles(db: Session, u: Usuario) -> list[dict]:
    """Nodos que la persona puede usar como filtro: todo el árbol si su alcance es global; si no, los de su ámbito más
    los de los indicadores que tiene asignados fuera de él."""
    nodos = estructura.todas(db)
    rutas = estructura.nombres_de_ruta(nodos)
    if not acceso.es_global(u):
        propias = acceso.ambito(u)
        asignados = set(db.scalars(acceso.indicadores_visibles(select(Indicador.nodo_id), u).distinct()))
        nodos = [n for n in nodos if acceso.dentro(n.ruta, propias) or n.id in asignados]
    return [ser.unidad(n, rutas[n.id]) for n in nodos]


@router.get("/arranque")
def arranque(ejercicio: AnioConsulta = None, db: Session = Depends(get_db), u: Usuario = Depends(cuenta_propia)):
    p = parametros.resumen(db)
    datos = {"usuario": ser.sesion(u)}
    if acceso.pendiente(u):   # cuenta pendiente de asignación: solo su perfil y la marca
        datos["parametros"] = {"empresa": p["empresa"], "logo_url": p["logo_url"]}
        return datos
    puede = lambda permiso: acceso.puede(u, permiso)   # noqa: E731
    datos["parametros"] = p
    hoy = calendario.hoy()
    sel = calendario.ejercicio_de_fecha(hoy)
    if puede("ejercicios.ver"):
        ej = r_ejercicios.listar(detalle=False, db=db, u=u)
        sel = elegir_ejercicio(ej["ejercicios"], ej["vigente"], ejercicio)
        datos["ejercicios"] = ej
    datos["ejercicio"] = sel
    if puede("indicadores.ver"):
        datos["unidades"] = unidades_visibles(db, u)
    # quien carga datos elige entre SUS indicadores; las listas largas (indicadores, cargas, personas) se piden paginadas
    datos["indicadores"] = ([ser.indicador_con_pendientes(*fila, u) for fila in indicadores.listar(db, u, sel, cargables=True)]
                            if puede("cargas.cargar") else [])
    if puede("cargas.aprobar"):
        bandeja = r_mediciones.resumen_de_bandeja(db, u)
        datos["bandeja_total"], datos["bandeja_ejercicios"] = bandeja["total"], bandeja["ejercicios"]
    if puede("panel.ver"):
        datos["resumen"] = ejercicios.foto(db, sel, None, hoy, u)["resumen"]   # lo que muestra la pantalla de inicio
    if puede("catalogos.gestionar") or puede("indicadores.crear") or puede("indicadores.editar"):
        datos["catalogos"] = [ser.catalogo(c) for c in organizacion.listar_catalogos(db)]
    if puede("sistema.puesta_en_marcha") or puede("usuarios.asignar"):   # la guía de arranque la usan quienes configuran
        datos["marcha"] = metas.avance_de_puesta_en_marcha(db, u, hoy)
    return datos

