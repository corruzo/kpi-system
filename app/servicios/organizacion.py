"""Estructura de la empresa: áreas, usuarios y listas de apoyo de la ficha (gerencias, procesos, objetivos, cargos)."""
from sqlalchemy import func, select, union
from sqlalchemy.orm import Session

from .. import security
from ..errores import Conflicto, Invalido, NoEncontrado
from ..models import Area, Bitacora, Catalogo, Ejercicio, Indicador, Medicion, NotaAuditoria, Presupuesto, Usuario
from . import auditoria
from .sesion import limite_intentos


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
def _usuarios_filtrados(q, buscar: str | None):
    if buscar and buscar.strip():
        patron = "%" + buscar.strip().lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        q = q.where(func.lower(Usuario.nombre + " " + Usuario.username).like(patron, escape="\\"))
    return q


def listar_usuarios(db: Session, *, buscar: str | None = None, desde: int = 0, limite: int | None = None) -> list[Usuario]:
    q = _usuarios_filtrados(select(Usuario).order_by(Usuario.nombre, Usuario.id), buscar)
    if limite is not None:
        q = q.offset(max(desde, 0)).limit(max(1, min(limite, 500)))
    return list(db.scalars(q))


def contar_usuarios(db: Session, buscar: str | None = None) -> int:
    return db.scalar(_usuarios_filtrados(select(func.count(Usuario.id)), buscar)) or 0


def _validar_rol_y_area(db: Session, rol: str, area_id: int | None) -> None:
    if rol == "jefe" and not area_id:
        raise Invalido("Un encargado de proceso debe tener un área asignada.")
    if area_id and not db.get(Area, area_id):
        raise Invalido("Área inexistente.")


def crear_usuario(db: Session, admin: Usuario, datos) -> Usuario:
    if db.scalar(select(Usuario).where(Usuario.username == datos.username)):
        raise Invalido("Ese nombre de usuario ya existe.")
    _validar_rol_y_area(db, datos.rol, datos.area_id)
    nuevo = Usuario(username=datos.username, nombre=datos.nombre.strip(), rol=datos.rol, email=datos.email or None,
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
    n_asignados = db.scalar(select(func.count(Indicador.id)).where(Indicador.encargado_id == u.id)) or 0
    if n_asignados and (datos.rol != "jefe" or not datos.activo or datos.area_id != u.area_id):
        raise Conflicto(f"Tiene {n_asignados} indicador(es) asignado(s) como encargado de proceso: reasígnelos a otra persona "
                        "(Indicadores → editar) antes de cambiarle el rol o el área, o de inhabilitarlo.")
    nuevos = {"nombre": datos.nombre.strip(), "rol": datos.rol, "activo": datos.activo,
              "area_id": datos.area_id if datos.rol == "jefe" else None}
    if datos.email is not None:   # sin el campo no se toca; con "" se borra
        nuevos["email"] = datos.email or None
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


def ids_con_historial(db: Session, ids: list[int] | None = None) -> set[int]:
    """Usuarios que figuran en algún registro (bitácora, cargas, revisiones, notas, ejercicios o presupuestos). A esos no se
    les puede borrar sin romper la trazabilidad: se inhabilitan."""
    consultas = [select(Bitacora.usuario_id), select(Medicion.cargado_por_id), select(Medicion.revisado_por_id),
                 select(NotaAuditoria.usuario_id), select(Ejercicio.creado_por_id), select(Ejercicio.cerrado_por_id),
                 select(Ejercicio.reabierto_por_id), select(Presupuesto.actualizado_por_id)]
    if ids is not None:   # solo los usuarios de la página: cada consulta se acota con su propio filtro
        columnas = [Bitacora.usuario_id, Medicion.cargado_por_id, Medicion.revisado_por_id, NotaAuditoria.usuario_id,
                    Ejercicio.creado_por_id, Ejercicio.cerrado_por_id, Ejercicio.reabierto_por_id, Presupuesto.actualizado_por_id]
        consultas = [select(c).where(c.in_(ids)) for c in columnas]
    return {i for i in db.scalars(union(*consultas)) if i is not None}


def ultimos_ingresos(db: Session, ids: list[int] | None = None) -> dict[int, object]:
    """{usuario_id: fecha de su último ingreso}, en una sola consulta (para el soporte a usuarios)."""
    q = select(Bitacora.usuario_id, func.max(Bitacora.fecha)).where(Bitacora.accion == "INICIO_SESION")
    if ids is not None:
        q = q.where(Bitacora.usuario_id.in_(ids))
    filas = db.execute(q.group_by(Bitacora.usuario_id))
    return {uid: fecha for uid, fecha in filas if uid is not None}


def cerrar_sesiones(db: Session, admin: Usuario, usuario_id: int) -> None:
    """Soporte: saca a un usuario de todos sus dispositivos (sube su versión de sesión). Debe volver a ingresar."""
    u = db.get(Usuario, usuario_id)
    if not u:
        raise NoEncontrado("Usuario no encontrado.")
    if u.id == admin.id:
        raise Invalido("Para cerrar su propia sesión use «Cerrar sesión» del menú de su perfil.")
    u.sesion_v += 1
    auditoria.registrar(db, admin, "SESIONES_CERRADAS", "usuario", u.id, {"username": u.username})
    db.commit()


def desbloquear_accesos(db: Session, admin: Usuario) -> None:
    """Soporte: levanta el bloqueo por intentos fallidos de ingreso (de todos los usuarios y orígenes)."""
    limite_intentos.reiniciar()
    auditoria.registrar(db, admin, "ACCESOS_DESBLOQUEADOS", "sistema", None, {})
    db.commit()


def eliminar_usuario(db: Session, admin: Usuario, usuario_id: int) -> None:
    """Borra definitivamente a un usuario que nunca tuvo actividad (por ejemplo, uno creado por error).
    Quien ya aparece en la bitácora, en cargas o en revisiones no puede borrarse: debe inhabilitarse."""
    u = db.get(Usuario, usuario_id)
    if not u:
        raise NoEncontrado("Usuario no encontrado.")
    if u.id == admin.id:
        raise Invalido("No puede eliminar su propia cuenta.")
    if db.scalar(select(Indicador.id).where(Indicador.encargado_id == u.id).limit(1)):
        raise Conflicto("Es encargado de proceso de uno o más indicadores: reasígnelos antes de eliminarlo.")
    if u.id in ids_con_historial(db):
        raise Conflicto("Este usuario tiene actividad registrada (ingresos, cargas o revisiones) y no puede eliminarse sin perder la "
                        "trazabilidad. Inhabilítelo: no podrá ingresar y su historial se conserva.")
    auditoria.registrar(db, admin, "USUARIO_ELIMINADO", "usuario", u.id, {"username": u.username, "nombre": u.nombre, "rol": u.rol})
    db.delete(u)
    db.commit()


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
