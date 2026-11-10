"""Motor de permisos: el ÚNICO lugar donde se decide qué puede ver y hacer cada persona.

Tres cosas se cruzan en cada decisión:

1. **Rol** → qué funciones tiene (`puede`): permisos del catálogo (`app/permisos.py`) con su nivel. Sin rol no se puede nada.
2. **Árbol** → qué alcanza a ver (`ambito`): cada nodo de ámbito y todo lo que cuelga de él. La visibilidad solo baja.
3. **Asignación** → qué es suyo: los indicadores de los que es responsable (los modifica) o cargador (les carga datos).

Reglas fijas (no configurables):
- Visible = está en su ámbito, o es su responsable, o es su cargador, o la persona tiene alcance global
  (Desarrollador, Coordinador SGC, o ámbito en la raíz de la empresa).
- Modificar una ficha: solo su responsable. Cargar: solo sus cargadores. Los roles de sistema (Desarrollador y
  Coordinador SGC) tienen **alcance total**: esas dos restricciones no les aplican.
- Lo que no se ve responde 404 (como si no existiera); lo que se ve pero no se puede hacer, 403.

Los permisos y el ámbito se leen UNA vez por petición (`preparar`) y quedan en `usuario.acceso`.
"""
from dataclasses import dataclass, field

from sqlalchemy import Select, and_, false, or_, select, true
from sqlalchemy.orm import Session, object_session

from .. import permisos as cat
from ..errores import Invalido, NoEncontrado, Prohibido
from ..models import Indicador, IndicadorCargador, Rol, RolPermiso, Unidad, Usuario, UsuarioUnidad

DESARROLLADOR, COORDINADOR = "desarrollador", "coordinador"
SIN_PERMISO = "No tiene permisos para esta acción."


@dataclass(frozen=True)
class Contexto:
    """Lo que el motor necesita saber de una persona, leído una sola vez por petición."""
    permisos: dict[str, str] = field(default_factory=dict)       # código → nivel
    clave: str | None = None                                      # desarrollador | coordinador | None (rol definido por el Coordinador)
    rol: str = ""                                                 # nombre del rol («» = cuenta pendiente de asignación)
    raiz: bool = False                                            # su ámbito es toda la empresa
    ambito: tuple[tuple[int, str], ...] = ()                      # (unidad_id, ruta) de cada nodo que ve completo
    miembro: tuple[tuple[int, str], ...] = ()                     # (unidad_id, ruta) de los nodos donde solo trabaja

    @property
    def total(self) -> bool:
        return self.clave in (DESARROLLADOR, COORDINADOR)

    @property
    def global_(self) -> bool:
        return self.total or self.raiz


# ---------------------------------------------------------------- contexto (una lectura por petición)
def preparar(db: Session, u: Usuario) -> Contexto:
    """Lee rol, permisos y posición de la persona (dos consultas) y los deja en `u.acceso`."""
    rol = u.rol
    if rol is None:
        ctx = Contexto()
    else:
        concedidos = {p.permiso: p.nivel for p in rol.permisos if cat.existe(p.permiso)}
        if rol.clave == DESARROLLADOR:
            concedidos = cat.completos(tecnicos=True)             # inmutable: no depende de lo guardado en la base
        elif rol.clave == COORDINADOR:
            concedidos = {**{c: cat.POR_CODIGO[c].minimo for c in cat.MINIMOS_DEL_COORDINADOR}, **concedidos}
        if rol.clave != DESARROLLADOR:
            concedidos = {c: n for c, n in concedidos.items() if not cat.POR_CODIGO[c].tecnico}   # lo técnico es solo del Desarrollador
        enlaces = [] if rol.clave else db.execute(   # los roles de sistema ven todo: no necesitan su posición
            select(UsuarioUnidad.tipo, Unidad.id, Unidad.ruta).join(Unidad, Unidad.id == UsuarioUnidad.unidad_id)
            .where(UsuarioUnidad.usuario_id == u.id)).all()
        ctx = Contexto(permisos=concedidos, clave=rol.clave, rol=rol.nombre, raiz=bool(u.ambito_raiz),
                       ambito=tuple((i, r) for t, i, r in enlaces if t == "ambito"),
                       miembro=tuple((i, r) for t, i, r in enlaces if t == "miembro"))
    u.acceso = ctx
    return ctx


def contexto(u: Usuario) -> Contexto:
    ctx = getattr(u, "acceso", None)
    if ctx is None:   # usuario que no pasó por la dependencia de la API (tareas de consola, pruebas de servicio)
        ctx = preparar(object_session(u), u)
    return ctx


# ---------------------------------------------------------------- rol → funciones
def puede(u: Usuario, permiso: str, nivel: str | None = None) -> bool:
    p = cat.POR_CODIGO[permiso]           # un código inexistente es un error de programación: KeyError
    return cat.alcanza(contexto(u).permisos.get(permiso), nivel or p.minimo)


def exigir(u: Usuario, permiso: str, nivel: str | None = None) -> None:
    if not puede(u, permiso, nivel):
        raise Prohibido(SIN_PERMISO)


def pendiente(u: Usuario) -> bool:
    """Cuenta sin rol: «pendiente de asignación»."""
    return not contexto(u).rol


def es_desarrollador(u: Usuario) -> bool:
    return contexto(u).clave == DESARROLLADOR


def alcance_total(u: Usuario) -> bool:
    """Roles de sistema: las restricciones «solo lo propio» no les aplican."""
    return contexto(u).total


def es_global(u: Usuario) -> bool:
    """Ve todos los indicadores (roles de sistema o ámbito en la raíz)."""
    return contexto(u).global_


# ---------------------------------------------------------------- árbol → visibilidad
def ambito(u: Usuario) -> list[str]:
    """Rutas de los nodos que la persona ve completos («/» = toda la empresa)."""
    c = contexto(u)
    return ["/"] if c.global_ else [r for _, r in c.ambito]


def dentro(ruta: str, rutas: list[str] | tuple[str, ...]) -> bool:
    return any(ruta.startswith(r) for r in rutas)


def subarbol(ruta: str):
    """Condición SQL: unidades del subárbol de `ruta` (ella incluida)."""
    return Unidad.ruta.like(ruta.replace("%", "") + "%")


def _nodos_del_ambito(c: Contexto):
    return select(Unidad.id).where(or_(*[subarbol(r) for _, r in c.ambito])) if c.ambito else None


def condicion_visible(u: Usuario, archivados: bool = False):
    """Condición SQL sobre `Indicador` con lo que la persona puede ver. Los archivados solo se incluyen si se piden, y
    nunca para quien únicamente los cargaba (ya no hay nada que cargar)."""
    c = contexto(u)
    if not c.rol:
        return false()
    if c.global_:
        return true() if archivados else Indicador.activo.is_(True)
    nodos = _nodos_del_ambito(c)
    en_ambito = Indicador.nodo_id.in_(nodos) if nodos is not None else false()
    propio = Indicador.responsable_id == u.id
    lo_carga = Indicador.id.in_(select(IndicadorCargador.indicador_id).where(IndicadorCargador.usuario_id == u.id))
    activos = and_(Indicador.activo.is_(True), or_(en_ambito, propio, lo_carga))
    if not archivados:
        return activos
    return or_(activos, and_(Indicador.activo.is_(False), or_(en_ambito, propio)))


def indicadores_visibles(q: Select, u: Usuario, archivados: bool = False) -> Select:
    """Agrega a una consulta que ya incluye `Indicador` el filtro de lo que la persona puede ver."""
    return q.where(condicion_visible(u, archivados))


def condicion_ambito(u: Usuario):
    """Condición SQL: indicadores activos dentro del ámbito (sin contar los asignados fuera de él)."""
    c = contexto(u)
    if c.global_:
        return Indicador.activo.is_(True)
    nodos = _nodos_del_ambito(c)
    return and_(Indicador.activo.is_(True), Indicador.nodo_id.in_(nodos)) if nodos is not None else false()


def condicion_carga(u: Usuario):
    """Condición SQL: indicadores activos a los que la persona puede cargar datos."""
    c = contexto(u)
    if c.total:
        return Indicador.activo.is_(True)
    return and_(Indicador.activo.is_(True),
                Indicador.id.in_(select(IndicadorCargador.indicador_id).where(IndicadorCargador.usuario_id == u.id)))


def en_nodo(nodo_id: int):
    """Condición SQL: indicadores del nodo o de cualquiera que cuelgue de él (filtro «por área» de listados y reportes)."""
    ruta = select(Unidad.ruta).where(Unidad.id == nodo_id).scalar_subquery()
    return Indicador.nodo_id.in_(select(Unidad.id).where(Unidad.ruta.like(ruta + "%")))


def en_ambito(u: Usuario, ind: Indicador) -> bool:
    c = contexto(u)
    return c.global_ or dentro(ind.nodo.ruta, [r for _, r in c.ambito])


def es_responsable(u: Usuario, ind: Indicador) -> bool:
    return ind.responsable_id is not None and ind.responsable_id == u.id


def es_cargador(u: Usuario, ind: Indicador) -> bool:
    return any(x.id == u.id for x in ind.cargadores)


def puede_ver(u: Usuario, ind: Indicador) -> bool:
    c = contexto(u)
    if not c.rol:
        return False
    if c.global_:
        return True
    if en_ambito(u, ind) or es_responsable(u, ind):
        return True
    return ind.activo and es_cargador(u, ind)


def exigir_visible(u: Usuario, ind: Indicador | None) -> Indicador:
    if ind is None or not puede_ver(u, ind):
        raise NoEncontrado("Indicador no encontrado.")
    return ind


# ---------------------------------------------------------------- asignación → modificar
def exigir_modificable(u: Usuario, ind: Indicador) -> None:
    """Editar, archivar o eliminar una ficha: solo su responsable (o un rol de sistema)."""
    if not (alcance_total(u) or es_responsable(u, ind)):
        raise Prohibido("Solo el responsable del indicador puede modificarlo.")


def puede_cargar(u: Usuario, ind: Indicador) -> bool:
    return alcance_total(u) or es_cargador(u, ind)


def exigir_cargable(u: Usuario, ind: Indicador) -> None:
    if not puede_cargar(u, ind):
        raise Prohibido("Solo quienes tienen asignada la carga de este indicador pueden cargar sus datos.")


# ---------------------------------------------------------------- «a sí mismo o a personas debajo de él»
def personas_debajo(db: Session, u: Usuario) -> set[int] | None:
    """Ids de quienes están debajo de la persona en la estructura; None = sin restricción (roles de sistema).
    Está debajo quien trabaja (miembro) en un nodo de su ámbito, o tiene como ámbito un nodo estrictamente inferior.
    Dos personas con el mismo nodo de ámbito son pares: ninguna está debajo de la otra."""
    c = contexto(u)
    if c.total:
        return None
    if not (c.raiz or c.ambito):
        return set()
    debajo: set[int] = set()
    filas = db.execute(select(UsuarioUnidad.usuario_id, UsuarioUnidad.tipo, Unidad.ruta).join(Unidad, Unidad.id == UsuarioUnidad.unidad_id))
    mias = [r for _, r in c.ambito]
    for uid, tipo, ruta in filas:
        if uid == u.id:
            continue
        if c.raiz or (tipo == "miembro" and dentro(ruta, mias)) or (tipo == "ambito" and any(ruta.startswith(r) and ruta != r for r in mias)):
            debajo.add(uid)
    return debajo


def exigir_asignacion(db: Session, u: Usuario, nodo: Unidad, responsable: Usuario | None, cargadores: list[Usuario]) -> None:
    """Regla de quien crea o asigna un indicador: en un nodo propio, y a sí mismo o a personas debajo de él.
    Además (para todos): las personas deben estar activas y con rol, y quien carga debe tener permiso de cargar."""
    for p in [x for x in [responsable, *cargadores] if x is not None]:
        if not p.activo or not p.rol_id:
            raise Invalido(f"«{p.nombre}» no está activo o aún no tiene un rol asignado.")
    con_permiso = set(db.scalars(select(Usuario.id).join(Rol, Rol.id == Usuario.rol_id).outerjoin(
        RolPermiso, and_(RolPermiso.rol_id == Rol.id, RolPermiso.permiso == "cargas.cargar"))
        .where(Usuario.id.in_([x.id for x in cargadores]), or_(RolPermiso.permiso.is_not(None), Rol.clave.is_not(None))))) if cargadores else set()
    for p in cargadores:
        if p.id not in con_permiso:
            raise Invalido(f"El rol de «{p.nombre}» no tiene permiso para cargar datos.")
    c = contexto(u)
    if c.total:
        return
    propios = [r for _, r in c.ambito]
    if not (c.raiz or dentro(nodo.ruta, propios) or nodo.id in {i for i, _ in c.miembro}):
        raise Prohibido("Solo puede crear o asignar indicadores en su propio nodo o en los que cuelgan de él.")
    debajo = personas_debajo(db, u)
    for p in [x for x in [responsable, *cargadores] if x is not None]:
        if p.id != u.id and p.id not in debajo:
            raise Prohibido(f"Solo puede asignar indicadores a sí mismo o a personas que están debajo de usted («{p.nombre}» no lo está).")


def puede_fijar_meta(db: Session, u: Usuario, ind: Indicador, debajo: set[int] | None = None) -> bool:
    """Metas: indicadores propios y de quienes están debajo (el Coordinador SGC, siempre)."""
    if alcance_total(u) or es_responsable(u, ind):
        return True
    if not en_ambito(u, ind):
        return False
    debajo = personas_debajo(db, u) if debajo is None else debajo
    return ind.responsable_id is None or ind.responsable_id in debajo


# ---------------------------------------------------------------- personas visibles
def usuarios_visibles(q: Select, u: Usuario) -> Select:
    """Quien no es Desarrollador no ve ni toca a los Desarrolladores (consulta que ya incluye `Usuario`)."""
    if es_desarrollador(u):
        return q
    desarrolladores = select(Rol.id).where(Rol.clave == DESARROLLADOR)
    return q.where(or_(Usuario.rol_id.is_(None), Usuario.rol_id.not_in(desarrolladores)))


# ---------------------------------------------------------------- aprobación jerárquica
@dataclass
class Aprobadores:
    """Quién tiene `cargas.aprobar`, por nodo de ámbito (leído una vez por petición)."""
    por_nodo: dict[int, set[int]] = field(default_factory=dict)
    raiz: set[int] = field(default_factory=set)
    siempre: set[int] = field(default_factory=set)        # Coordinador SGC (respaldo) y Desarrollador


def mapa_aprobadores(db: Session) -> Aprobadores:
    mapa = Aprobadores()
    con_permiso = select(RolPermiso.rol_id).where(RolPermiso.permiso == "cargas.aprobar")
    filas = db.execute(select(Usuario.id, Usuario.ambito_raiz, Rol.clave).join(Rol, Rol.id == Usuario.rol_id)
                       .where(Usuario.activo.is_(True), or_(Rol.clave.is_not(None), Rol.id.in_(con_permiso)))).all()
    capaces = set()
    for uid, raiz, clave in filas:
        if clave is not None:
            mapa.siempre.add(uid)
            continue
        capaces.add(uid)
        if raiz:
            mapa.raiz.add(uid)
    if capaces:
        for uid, nodo in db.execute(select(UsuarioUnidad.usuario_id, UsuarioUnidad.unidad_id)
                                    .where(UsuarioUnidad.tipo == "ambito", UsuarioUnidad.usuario_id.in_(capaces))):
            mapa.por_nodo.setdefault(nodo, set()).add(uid)
    return mapa


def aprobadores_de(ruta_del_nodo: str, autor_id: int, mapa: Aprobadores) -> set[int]:
    """Quién puede aprobar una carga hecha por `autor_id` en un indicador del nodo dado: el nivel más cercano hacia arriba
    (el propio nodo, su padre… la raíz) que tenga al menos un aprobador distinto del autor; si hay varios en ese nivel,
    cualquiera. Siempre se suman los roles de sistema. Nadie aprueba una carga propia."""
    elegibles: set[int] = set()
    for nodo in reversed([int(x) for x in ruta_del_nodo.strip("/").split("/") if x]):
        elegibles = mapa.por_nodo.get(nodo, set()) - {autor_id}
        if elegibles:
            break
    else:
        elegibles = mapa.raiz - {autor_id}
    return (elegibles | mapa.siempre) - {autor_id}


def puede_aprobar(db: Session, u: Usuario, ind: Indicador, autor_id: int, mapa: Aprobadores | None = None) -> bool:
    if u.id == autor_id or not puede(u, "cargas.aprobar"):
        return False
    return u.id in aprobadores_de(ind.nodo.ruta, autor_id, mapa or mapa_aprobadores(db))
