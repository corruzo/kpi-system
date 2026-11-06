"""Política única de visibilidad de indicadores. TODA consulta o acción sobre un indicador pasa por aquí.

- admin: todo (incluso archivados).
- gerente: todos los activos.
- encargado de proceso (rol interno «jefe»): SOLO los indicadores que se le asignaron (`encargado_id` = él mismo)
  y que estén activos. Que dos encargados compartan área no les da acceso a los datos del otro.

Lo que no se puede ver se responde como si no existiera (404), para no revelar que existe.
"""

from sqlalchemy import Select

from ..errores import NoEncontrado
from ..models import Indicador, Usuario


def es_encargado(u: Usuario) -> bool:
    return u.rol == "jefe"


def puede_ver(u: Usuario, ind: Indicador) -> bool:
    if u.rol == "admin":
        return True
    if not ind.activo:
        return False
    if u.rol == "jefe":
        return ind.encargado_id is not None and ind.encargado_id == u.id
    return u.rol == "gerente"


def exigir_visible(u: Usuario, ind: Indicador | None) -> Indicador:
    if ind is None or not puede_ver(u, ind):
        raise NoEncontrado("Indicador no encontrado.")
    return ind


def restringir(q: Select, u: Usuario) -> Select:
    """Agrega a una consulta que ya incluye `Indicador` el filtro de lo que el usuario puede ver."""
    if u.rol == "admin":
        return q
    q = q.where(Indicador.activo.is_(True))
    if u.rol == "jefe":
        q = q.where(Indicador.encargado_id == u.id)
    return q
