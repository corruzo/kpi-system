"""Estructura de la empresa: áreas, usuarios y listas de apoyo de la ficha (gerencias, procesos, objetivos, cargos)."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import security
from ..errores import Conflicto, Invalido, NoEncontrado
from ..models import Area, Catalogo, Indicador, Usuario
from . import auditoria


# ---------------------------------------------------------------- áreas
def listar_areas(db: Session) -> list[Area]:
    return list(db.scalars(select(Area).order_by(Area.nombre)))


def _exigir_nombre_libre(db: Session, nombre: str, propio_id: int | None = None) -> None:
    otra = db.scalar(select(Area).where(func.lower(Area.nombre) == nombre.lower()))
    if otra and otra.id != propio_id:
        raise Invalido("Ya existe un área con ese nombre.")


def crear_area(db: Session, usuario: Usuario, nombre: str, origen: str | None = None, confirmar: bool = True) -> Area:
    """`confirmar=False` deja la transacción abierta (lo usa la importación, que confirma al final)."""
    nombre = nombre.strip()
    _exigir_nombre_libre(db, nombre)
    area = Area(nombre=nombre)
    db.add(area)
    db.flush()
    auditoria.registrar(db, usuario, "AREA_CREADA", "area", area.id, {"nombre": nombre, **({"origen": origen} if origen else {})})
    if confirmar:
        db.commit()
    return area


def editar_area(db: Session, usuario: Usuario, area_id: int, nombre: str) -> Area:
    area = db.get(Area, area_id)
    if not area:
        raise NoEncontrado("Área no encontrada.")
    _exigir_nombre_libre(db, nombre.strip(), area.id)
    antes, area.nombre = area.nombre, nombre.strip()
    auditoria.registrar(db, usuario, "AREA_EDITADA", "area", area.id, {"antes": antes, "despues": area.nombre})
    db.commit()
    return area


def eliminar_area(db: Session, usuario: Usuario, area_id: int) -> None:
    area = db.get(Area, area_id)
    if not area:
        raise NoEncontrado("Área no encontrada.")
    if db.scalar(select(Indicador.id).where(Indicador.area_id == area.id).limit(1)) or \
            db.scalar(select(Usuario.id).where(Usuario.area_id == area.id).limit(1)):
        raise Conflicto("El área tiene indicadores o usuarios asignados; no puede eliminarse.")
    auditoria.registrar(db, usuario, "AREA_ELIMINADA", "area", area.id, {"nombre": area.nombre})
    db.delete(area)
    db.commit()


# ---------------------------------------------------------------- usuarios
def listar_usuarios(db: Session) -> list[Usuario]:
    return list(db.scalars(select(Usuario).order_by(Usuario.nombre)))


def _validar_rol_y_area(db: Session, rol: str, area_id: int | None) -> None:
    if rol == "jefe" and not area_id:
        raise Invalido("Un Jefe de Área debe tener un área asignada.")
    if area_id and not db.get(Area, area_id):
        raise Invalido("Área inexistente.")


def crear_usuario(db: Session, admin: Usuario, datos) -> Usuario:
    if db.scalar(select(Usuario).where(Usuario.username == datos.username)):
        raise Invalido("Ese nombre de usuario ya existe.")
    _validar_rol_y_area(db, datos.rol, datos.area_id)
    nuevo = Usuario(username=datos.username, nombre=datos.nombre.strip(), rol=datos.rol,
                    area_id=datos.area_id if datos.rol == "jefe" else None,
                    password_hash=security.hash_password(datos.password))
    db.add(nuevo)
    db.flush()
    auditoria.registrar(db, admin, "USUARIO_CREADO", "usuario", nuevo.id,
                        {"username": nuevo.username, "rol": nuevo.rol, "area_id": nuevo.area_id})
    db.commit()
    return nuevo


def editar_usuario(db: Session, admin: Usuario, usuario_id: int, datos) -> Usuario:
    u = db.get(Usuario, usuario_id)
    if not u:
        raise NoEncontrado("Usuario no encontrado.")
    if u.id == admin.id and (not datos.activo or datos.rol != "admin"):
        raise Invalido("No puede desactivarse ni quitarse el rol de administrador a sí mismo.")
    _validar_rol_y_area(db, datos.rol, datos.area_id)
    nuevos = {"nombre": datos.nombre.strip(), "rol": datos.rol, "activo": datos.activo,
              "area_id": datos.area_id if datos.rol == "jefe" else None}
    cambios = {}
    for campo, valor in nuevos.items():
        if getattr(u, campo) != valor:
            cambios[campo] = [getattr(u, campo), valor]
            setattr(u, campo, valor)
    if datos.password:
        u.password_hash = security.hash_password(datos.password)
        u.sesion_v += 1   # cierra sus sesiones activas
        cambios["password"] = "restablecida"
    if not datos.activo:
        u.sesion_v += 1
    if cambios:
        auditoria.registrar(db, admin, "USUARIO_EDITADO", "usuario", u.id, {"username": u.username, "cambios": cambios})
    db.commit()
    return u


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
