"""Estructura de la empresa: árbol de gerencias → departamentos → jefaturas (tabla `unidades`).

La empresa (raíz) es implícita. Cada nodo guarda su `ruta` («/1/4/9/»), de modo que el subárbol de un nodo se consulta
por prefijo. Reglas: el nivel de un nodo corresponde al de su padre, no hay ciclos, los nombres no se repiten entre
hermanos y no se borra un nodo con hijos, personas o indicadores. Mover un nodo reajusta la ruta de todo su subárbol
en la misma transacción. Todo cambio queda en la bitácora.
"""
import unicodedata

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..errores import Conflicto, Invalido, NoEncontrado
from ..models import NIVEL_DEL_PADRE, NIVELES, Indicador, Unidad, Usuario, UsuarioUnidad
from . import auditoria


# ---------------------------------------------------------------- consulta
def todas(db: Session) -> list[Unidad]:
    """Todos los nodos, en orden de árbol (cada padre antes que sus hijos, hermanos por nombre)."""
    nodos = list(db.scalars(select(Unidad)))
    hijos: dict[int | None, list[Unidad]] = {}
    for n in nodos:
        hijos.setdefault(n.padre_id, []).append(n)
    salida: list[Unidad] = []

    def bajar(padre_id):
        for n in sorted(hijos.get(padre_id, []), key=lambda x: _clave_orden(x.nombre)):
            salida.append(n)
            bajar(n.id)
    bajar(None)
    return salida


def _clave_orden(nombre: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", nombre.lower()) if unicodedata.category(c) != "Mn")


def nombres_de_ruta(nodos: list[Unidad]) -> dict[int, str]:
    """{id: «Gerencia › Departamento › Jefatura»} para mostrar dónde está cada nodo."""
    por_id = {n.id: n for n in nodos}
    return {n.id: " › ".join(por_id[int(x)].nombre for x in n.ruta.strip("/").split("/") if int(x) in por_id) for n in nodos}


def conteos(db: Session) -> tuple[dict[int, int], dict[int, int]]:
    """({unidad_id: personas}, {unidad_id: indicadores}) asignados DIRECTAMENTE a cada nodo (dos consultas)."""
    personas = dict(db.execute(select(UsuarioUnidad.unidad_id, func.count()).group_by(UsuarioUnidad.unidad_id)).all())
    indicadores = dict(db.execute(select(Indicador.nodo_id, func.count()).group_by(Indicador.nodo_id)).all())
    return personas, indicadores


def obtener(db: Session, unidad_id: int) -> Unidad:
    nodo = db.get(Unidad, unidad_id)
    if not nodo:
        raise NoEncontrado("Nodo de la estructura no encontrado.")
    return nodo


# ---------------------------------------------------------------- validación
def _exigir_nombre_libre(db: Session, nombre: str, padre_id: int | None, propio_id: int | None = None) -> None:
    q = select(Unidad).where(func.lower(Unidad.nombre) == nombre.lower(),
                             Unidad.padre_id.is_(None) if padre_id is None else Unidad.padre_id == padre_id)
    otro = db.scalar(q)
    if otro and otro.id != propio_id:
        raise Invalido(f"Ya existe «{otro.nombre}» en ese mismo lugar de la estructura.")


def _exigir_nivel(nivel: str, padre: Unidad | None) -> None:
    if nivel not in NIVELES:
        raise Invalido("Nivel no válido.")
    esperado = NIVEL_DEL_PADRE[nivel]
    if (padre.nivel if padre else None) != esperado:
        raise Invalido("Una gerencia cuelga directamente de la empresa." if esperado is None else
                       f"{'Un departamento' if nivel == 'departamento' else 'Una jefatura'} debe colgar de "
                       f"{'una gerencia' if esperado == 'gerencia' else 'un departamento'}.")


# ---------------------------------------------------------------- alta, edición, movimiento y baja
def crear(db: Session, usuario: Usuario, nombre: str, nivel: str, padre_id: int | None, origen: str | None = None,
          confirmar: bool = True) -> Unidad:
    """`confirmar=False` deja la transacción abierta (lo usa la importación, que confirma al final)."""
    nombre = " ".join(nombre.split())
    padre = obtener(db, padre_id) if padre_id else None
    _exigir_nivel(nivel, padre)
    _exigir_nombre_libre(db, nombre, padre.id if padre else None)
    nodo = Unidad(nombre=nombre, nivel=nivel, padre_id=padre.id if padre else None, ruta=f"?{nombre}/{padre_id or 0}"[:80])
    db.add(nodo)
    db.flush()                                     # la ruta lleva el id propio: se fija en cuanto la base lo asigna
    nodo.ruta = f"{padre.ruta if padre else '/'}{nodo.id}/"
    db.flush()
    auditoria.registrar(db, usuario, "UNIDAD_CREADA", "unidad", nodo.id,
                        {"nombre": nombre, "nivel": nivel, "padre_id": nodo.padre_id, **({"origen": origen} if origen else {})})
    if confirmar:
        db.commit()
    return nodo


def renombrar(db: Session, usuario: Usuario, unidad_id: int, nombre: str) -> Unidad:
    nodo = obtener(db, unidad_id)
    nombre = " ".join(nombre.split())
    _exigir_nombre_libre(db, nombre, nodo.padre_id, nodo.id)
    if nombre != nodo.nombre:
        antes, nodo.nombre = nodo.nombre, nombre
        auditoria.registrar(db, usuario, "UNIDAD_EDITADA", "unidad", nodo.id, {"antes": antes, "despues": nombre})
    db.commit()
    return nodo


def mover(db: Session, usuario: Usuario, unidad_id: int, padre_id: int) -> Unidad:
    """Cuelga el nodo (con todo su subárbol) de otro padre del nivel que le corresponde. Una gerencia no se mueve:
    cuelga de la empresa. Las rutas del subárbol se reescriben en esta misma transacción."""
    nodo, padre = obtener(db, unidad_id), obtener(db, padre_id)
    if nodo.nivel == "gerencia":
        raise Invalido("Una gerencia cuelga directamente de la empresa: no se puede mover.")
    if padre.ruta.startswith(nodo.ruta):
        raise Invalido("Un nodo no puede colgar de sí mismo ni de uno de sus descendientes.")
    _exigir_nivel(nodo.nivel, padre)
    if padre.id == nodo.padre_id:
        return nodo
    _exigir_nombre_libre(db, nodo.nombre, padre.id, nodo.id)
    vieja, nueva = nodo.ruta, f"{padre.ruta}{nodo.id}/"
    for n in db.scalars(select(Unidad).where(Unidad.ruta.like(vieja + "%"))):
        n.ruta = nueva + n.ruta[len(vieja):]
    anterior, nodo.padre_id = nodo.padre_id, padre.id
    auditoria.registrar(db, usuario, "UNIDAD_MOVIDA", "unidad", nodo.id,
                        {"nombre": nodo.nombre, "padre_antes": anterior, "padre_despues": padre.id})
    db.commit()
    return nodo


def eliminar(db: Session, usuario: Usuario, unidad_id: int) -> None:
    nodo = obtener(db, unidad_id)
    hijos = db.scalar(select(func.count()).select_from(Unidad).where(Unidad.padre_id == nodo.id)) or 0
    personas = db.scalar(select(func.count()).select_from(UsuarioUnidad).where(UsuarioUnidad.unidad_id == nodo.id)) or 0
    indicadores = db.scalar(select(func.count()).select_from(Indicador).where(Indicador.nodo_id == nodo.id)) or 0
    motivos = [t for n, t in ((hijos, f"{hijos} nodo(s) que cuelgan de él"), (personas, f"{personas} persona(s) asignada(s)"),
                              (indicadores, f"{indicadores} indicador(es)")) if n]
    if motivos:
        raise Conflicto(f"«{nodo.nombre}» no puede eliminarse: tiene {', '.join(motivos)}. Muévalos o reasígnelos primero.")
    auditoria.registrar(db, usuario, "UNIDAD_ELIMINADA", "unidad", nodo.id, {"nombre": nodo.nombre, "nivel": nodo.nivel})
    db.delete(nodo)
    db.commit()
