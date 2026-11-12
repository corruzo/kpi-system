"""Roles y permisos.

- **Desarrollador** (de sistema): todo, incluido lo técnico. Inmutable: no se edita, no se borra y sus permisos no dependen
  de lo guardado (el motor siempre le da el catálogo completo).
- **Coordinador SGC** (de sistema): todo lo funcional, nada técnico. Solo un Desarrollador puede ajustar sus permisos, y
  nunca por debajo de `MINIMOS_DEL_COORDINADOR`.
- **Roles definidos por el Coordinador**: nombre libre y un nivel por permiso funcional.

Anti-escalada: nadie edita el rol que él mismo tiene, nadie concede un permiso (o nivel) que no posee, y los permisos
técnicos no se conceden a ningún rol. Cada cambio queda en la bitácora y surte efecto en la siguiente petición.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .. import permisos as cat
from ..errores import Conflicto, Invalido, NoEncontrado, Prohibido
from ..models import Rol, RolPermiso, Usuario
from . import acceso, auditoria

NOMBRES_DE_SISTEMA = {acceso.DESARROLLADOR: "Desarrollador", acceso.COORDINADOR: "Coordinador SGC"}
DESCRIPCIONES = {acceso.DESARROLLADOR: "Sistemas / TI: todo, incluido lo técnico. No se puede modificar.",
                 acceso.COORDINADOR: "Normalización: todo lo funcional; define los roles y asigna a las personas."}


# ---------------------------------------------------------------- siembra (arranque)
def sembrar(db: Session) -> None:
    """Crea los roles de sistema si faltan y retira permisos guardados que ya no existen en el catálogo."""
    existentes = {r.clave: r for r in db.scalars(select(Rol).where(Rol.clave.is_not(None)))}
    for clave, nombre in NOMBRES_DE_SISTEMA.items():
        if clave not in existentes:
            rol = Rol(nombre=nombre, descripcion=DESCRIPCIONES[clave], de_sistema=True, clave=clave)
            rol.permisos = [RolPermiso(permiso=c, nivel=n) for c, n in cat.completos(tecnicos=clave == acceso.DESARROLLADOR).items()]
            db.add(rol)
    for huerfano in db.scalars(select(RolPermiso).where(RolPermiso.permiso.not_in(list(cat.POR_CODIGO)))):
        db.delete(huerfano)
    # el Desarrollador siempre refleja el catálogo completo (si se agregan permisos en una versión nueva)
    dev = existentes.get(acceso.DESARROLLADOR)
    if dev:
        guardados = {p.permiso for p in dev.permisos}
        dev.permisos.extend(RolPermiso(permiso=c, nivel=n) for c, n in cat.completos(tecnicos=True).items() if c not in guardados)
    db.commit()


def de_sistema(db: Session, clave: str) -> Rol:
    return db.scalar(select(Rol).where(Rol.clave == clave))


# ---------------------------------------------------------------- consulta
def _visibles(db: Session, u: Usuario) -> list[Rol]:
    roles = list(db.scalars(select(Rol).options(selectinload(Rol.permisos)).order_by(Rol.de_sistema.desc(), Rol.nombre)))
    return roles if acceso.es_desarrollador(u) else [r for r in roles if r.clave != acceso.DESARROLLADOR]


def permisos_de(rol: Rol) -> dict[str, str]:
    if rol.clave == acceso.DESARROLLADOR:
        return cat.completos(tecnicos=True)
    return {p.permiso: p.nivel for p in rol.permisos if cat.existe(p.permiso) and not cat.POR_CODIGO[p.permiso].tecnico}


def editable_por(u: Usuario, rol: Rol) -> tuple[bool, str]:
    if rol.clave == acceso.DESARROLLADOR:
        return False, "El rol Desarrollador no se puede modificar."
    if rol.id == u.rol_id:
        return False, "No puede cambiar los permisos de su propio rol."
    if rol.clave == acceso.COORDINADOR and not acceso.es_desarrollador(u):
        return False, "Solo un Desarrollador puede ajustar el rol Coordinador SGC."
    return True, ""


def listar(db: Session, u: Usuario) -> list[dict]:
    usos = dict(db.execute(select(Usuario.rol_id, func.count()).where(Usuario.rol_id.is_not(None)).group_by(Usuario.rol_id)).all())
    salida = []
    for r in _visibles(db, u):
        concedidos = permisos_de(r)
        editable, motivo = editable_por(u, r)
        salida.append({"id": r.id, "nombre": r.nombre, "descripcion": r.descripcion, "de_sistema": r.de_sistema, "clave": r.clave,
                       "permisos": concedidos, "usuarios": usos.get(r.id, 0), "editable": editable, "motivo": motivo,
                       "resumen": cat.resumen(concedidos)})
    return salida


def catalogo_para(u: Usuario) -> dict:
    """El catálogo que se muestra en la matriz: NUNCA incluye permisos técnicos, ni siquiera para el Desarrollador (son
    suyos por definición y no se conceden a ningún rol). `tope` es el nivel máximo que esta persona puede conceder."""
    propios = acceso.contexto(u).permisos
    lista = [p for p in cat.CATALOGO if not p.tecnico]
    return {"grupos": [g for g in cat.GRUPOS if any(p.grupo == g for p in lista)],
            "permisos": [{"codigo": p.codigo, "grupo": p.grupo, "etiqueta": p.etiqueta, "descripcion": p.descripcion,
                          "alcance": p.alcance, "niveles": list(p.niveles), "tecnico": p.tecnico, "implica": list(p.implica),
                          "tope": propios.get(p.codigo)} for p in lista],
            "cuenta_propia": list(cat.CUENTA_PROPIA), "minimos_coordinador": list(cat.MINIMOS_DEL_COORDINADOR)}


def obtener(db: Session, u: Usuario, rol_id: int) -> Rol:
    rol = db.get(Rol, rol_id)
    if not rol or (rol.clave == acceso.DESARROLLADOR and not acceso.es_desarrollador(u)):
        raise NoEncontrado("Rol no encontrado.")
    return rol


# ---------------------------------------------------------------- validación (anti-escalada)
def _validar(u: Usuario, pedidos: dict[str, str]) -> dict[str, str]:
    propios = acceso.contexto(u).permisos
    for codigo, nivel in pedidos.items():
        p = cat.POR_CODIGO.get(codigo)
        if p is None:
            raise Invalido(f"El permiso «{codigo}» no existe.")
        if p.tecnico:
            raise Prohibido("Los permisos técnicos son exclusivos del rol Desarrollador y no se pueden conceder.")
        if nivel not in p.niveles:
            raise Invalido(f"«{p.etiqueta}» no admite el nivel «{nivel}».")
        if not cat.alcanza(propios.get(codigo), nivel):
            raise Prohibido(f"No puede conceder «{p.etiqueta}»: usted no tiene ese permiso.")
    return cat.con_implicados(pedidos)


def _exigir_nombre_libre(db: Session, nombre: str, propio_id: int | None = None) -> None:
    otro = db.scalar(select(Rol).where(func.lower(Rol.nombre) == nombre.lower()))
    if otro and otro.id != propio_id:
        raise Invalido("Ya existe un rol con ese nombre.")


# ---------------------------------------------------------------- alta, edición, duplicado y baja
def crear(db: Session, u: Usuario, nombre: str, descripcion: str, pedidos: dict[str, str]) -> Rol:
    nombre = " ".join(nombre.split())
    _exigir_nombre_libre(db, nombre)
    finales = _validar(u, pedidos)
    rol = Rol(nombre=nombre, descripcion=descripcion.strip(), de_sistema=False)
    rol.permisos = [RolPermiso(permiso=c, nivel=n) for c, n in sorted(finales.items())]
    db.add(rol)
    db.flush()
    auditoria.registrar(db, u, "ROL_CREADO", "rol", rol.id, {"nombre": nombre, "permisos": finales})
    db.commit()
    return rol


def editar(db: Session, u: Usuario, rol_id: int, nombre: str, descripcion: str, pedidos: dict[str, str]) -> Rol:
    rol = obtener(db, u, rol_id)
    editable, motivo = editable_por(u, rol)
    if not editable:
        raise Prohibido(motivo)
    finales = _validar(u, pedidos)
    if rol.clave == acceso.COORDINADOR:
        faltan = [cat.POR_CODIGO[c].etiqueta for c in cat.MINIMOS_DEL_COORDINADOR if c not in finales]
        if faltan:
            raise Invalido("El Coordinador SGC no puede quedar sin: " + ", ".join(faltan) + ".")
    cambios: dict = {}
    nombre = " ".join(nombre.split())
    if rol.de_sistema:
        nombre = rol.nombre                       # los roles de sistema conservan su nombre
    _exigir_nombre_libre(db, nombre, rol.id)
    for campo, valor in (("nombre", nombre), ("descripcion", descripcion.strip())):
        if getattr(rol, campo) != valor:
            cambios[campo] = [getattr(rol, campo), valor]
            setattr(rol, campo, valor)
    antes = permisos_de(rol)
    difieren = {c: [antes.get(c), finales.get(c)] for c in sorted(set(antes) | set(finales)) if antes.get(c) != finales.get(c)}
    if difieren:
        cambios["permisos"] = difieren
        rol.permisos = [RolPermiso(permiso=c, nivel=n) for c, n in sorted(finales.items())]
    if cambios:
        auditoria.registrar(db, u, "ROL_EDITADO", "rol", rol.id, {"nombre": rol.nombre, "cambios": cambios})
    db.commit()
    return rol


def duplicar(db: Session, u: Usuario, rol_id: int, nombre: str) -> Rol:
    """Copia un rol con otro nombre (rige la misma regla anti-escalada que al crear)."""
    origen = obtener(db, u, rol_id)
    if origen.clave == acceso.DESARROLLADOR:
        raise Prohibido("El rol Desarrollador no se puede duplicar.")
    return crear(db, u, nombre, origen.descripcion, permisos_de(origen))


def eliminar(db: Session, u: Usuario, rol_id: int) -> None:
    rol = obtener(db, u, rol_id)
    if rol.de_sistema:
        raise Prohibido("Los roles de sistema no se pueden eliminar.")
    if rol.id == u.rol_id:
        raise Prohibido("No puede eliminar su propio rol.")
    usos = db.scalar(select(func.count()).select_from(Usuario).where(Usuario.rol_id == rol.id)) or 0
    if usos:
        raise Conflicto(f"{usos} persona(s) tienen este rol: asígneles otro antes de eliminarlo.")
    auditoria.registrar(db, u, "ROL_ELIMINADO", "rol", rol.id, {"nombre": rol.nombre})
    db.delete(rol)
    db.commit()
