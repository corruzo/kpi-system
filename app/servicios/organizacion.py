"""Listas de apoyo de la ficha técnica (gerencias, procesos, objetivos, cargos). La estructura de la empresa está en
`estructura.py` y las personas en `personas.py`."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..errores import Invalido, NoEncontrado
from ..models import Catalogo, Usuario
from . import auditoria


# ---------------------------------------------------------------- listas de apoyo
def listar_catalogos(db: Session) -> list[Catalogo]:
    return list(db.scalars(select(Catalogo).order_by(Catalogo.tipo, Catalogo.valor)))


def crear_catalogo(db: Session, usuario: Usuario, datos) -> Catalogo:
    if db.scalar(select(Catalogo).where(Catalogo.tipo == datos.tipo, func.lower(Catalogo.valor) == datos.valor.strip().lower())):
        raise Invalido("Ese elemento ya existe en la lista.")
    elemento = Catalogo(tipo=datos.tipo, valor=datos.valor.strip(), detalle=datos.detalle.strip())
    db.add(elemento)
    db.flush()
    auditoria.registrar(db, usuario, "CATALOGO_CREADO", "catalogo", elemento.id, {"tipo": elemento.tipo, "valor": elemento.valor})
    db.commit()
    return elemento


def editar_catalogo(db: Session, usuario: Usuario, elemento_id: int, datos) -> Catalogo:
    elemento = db.get(Catalogo, elemento_id)
    if not elemento:
        raise NoEncontrado("Elemento no encontrado.")
    antes = [elemento.valor, elemento.detalle]
    elemento.valor, elemento.detalle = datos.valor.strip(), datos.detalle.strip()
    auditoria.registrar(db, usuario, "CATALOGO_EDITADO", "catalogo", elemento.id,
                        {"tipo": elemento.tipo, "antes": antes, "despues": [elemento.valor, elemento.detalle]})
    db.commit()
    return elemento


def eliminar_catalogo(db: Session, usuario: Usuario, elemento_id: int) -> None:
    elemento = db.get(Catalogo, elemento_id)
    if not elemento:
        raise NoEncontrado("Elemento no encontrado.")
    auditoria.registrar(db, usuario, "CATALOGO_ELIMINADO", "catalogo", elemento.id, {"tipo": elemento.tipo, "valor": elemento.valor})
    db.delete(elemento)   # las fichas conservan el texto copiado: no dependen de la lista
    db.commit()
