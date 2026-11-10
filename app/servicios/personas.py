"""Personas: cuentas (Desarrollador), asignación de rol / ámbito / indicadores (Coordinador SGC) y soporte.

- Una cuenta nueva no tiene rol: queda «pendiente de asignación» y no accede a nada.
- Quien no es Desarrollador no ve ni toca a los Desarrolladores (para él no existen: 404).
- Nadie se asigna a sí mismo; nadie da un rol con permisos que no posee; el rol Coordinador SGC solo lo da un Desarrollador;
  el rol Desarrollador solo se da o se quita con el procedimiento explícito `designar_desarrollador`.
- El sistema nunca queda sin un Desarrollador activo.
"""
from sqlalchemy import func, select, union
from sqlalchemy.orm import Session

from .. import permisos as cat
from .. import security
from ..errores import Conflicto, Invalido, NoEncontrado, Prohibido
from ..models import (
    Bitacora,
    Ejercicio,
    Indicador,
    IndicadorCargador,
    Medicion,
    Meta,
    NotaAuditoria,
    Rol,
    Unidad,
    Usuario,
    UsuarioUnidad,
)
from . import acceso, auditoria, estructura, reinicio, roles
from .sesion import limite_intentos


# ---------------------------------------------------------------- consulta
def _filtrados(q, u: Usuario, buscar: str | None):
    q = acceso.usuarios_visibles(q, u)
    if buscar and buscar.strip():
        patron = "%" + buscar.strip().lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        q = q.where(func.lower(Usuario.nombre + " " + Usuario.username).like(patron, escape="\\"))
    return q


def listar(db: Session, u: Usuario, *, buscar: str | None = None, desde: int = 0, limite: int | None = None) -> list[Usuario]:
    q = _filtrados(select(Usuario).order_by(Usuario.nombre, Usuario.id), u, buscar)
    if limite is not None:
        q = q.offset(max(desde, 0)).limit(max(1, min(limite, 500)))
    return list(db.scalars(q))


def contar(db: Session, u: Usuario, buscar: str | None = None) -> int:
    return db.scalar(_filtrados(select(func.count(Usuario.id)), u, buscar)) or 0


def obtener(db: Session, u: Usuario, usuario_id: int) -> Usuario:
    """La persona, si quien pregunta puede verla (un Desarrollador es invisible para los demás)."""
    persona = db.scalar(acceso.usuarios_visibles(select(Usuario).where(Usuario.id == usuario_id), u))
    if not persona:
        raise NoEncontrado("Usuario no encontrado.")
    return persona


def detalles(db: Session, personas: list[Usuario]) -> dict[int, dict]:
    """{usuario_id: {rol, clave, ambito, miembro, responsable_de, cargador_de}} de una página de personas (4 consultas)."""
    ids = [p.id for p in personas]
    if not ids:
        return {}
    roles_ = {r.id: r for r in db.scalars(select(Rol))}
    enlaces: dict[int, dict[str, list[int]]] = {}
    for uid, nodo, tipo in db.execute(select(UsuarioUnidad.usuario_id, UsuarioUnidad.unidad_id, UsuarioUnidad.tipo)
                                      .where(UsuarioUnidad.usuario_id.in_(ids))):
        enlaces.setdefault(uid, {"ambito": [], "miembro": []})[tipo].append(nodo)
    resp = dict(db.execute(select(Indicador.responsable_id, func.count()).where(Indicador.responsable_id.in_(ids))
                           .group_by(Indicador.responsable_id)).all())
    carg = dict(db.execute(select(IndicadorCargador.usuario_id, func.count()).where(IndicadorCargador.usuario_id.in_(ids))
                           .group_by(IndicadorCargador.usuario_id)).all())
    salida = {}
    for p in personas:
        rol = roles_.get(p.rol_id)
        e = enlaces.get(p.id, {"ambito": [], "miembro": []})
        salida[p.id] = {"rol_id": p.rol_id, "rol": rol.nombre if rol else None, "rol_clave": rol.clave if rol else None,
                        "pendiente": rol is None, "ambito_raiz": bool(p.ambito_raiz), "ambito": sorted(e["ambito"]),
                        "miembro": sorted(e["miembro"]), "responsable_de": resp.get(p.id, 0), "cargador_de": carg.get(p.id, 0)}
    return salida


def opciones(db: Session, u: Usuario) -> list[dict]:
    """Personas a las que quien pregunta puede asignar un indicador: él mismo y quienes están debajo (los roles de
    sistema, cualquiera con rol). Indica si su rol permite cargar datos."""
    debajo = acceso.personas_debajo(db, u)
    q = acceso.usuarios_visibles(select(Usuario).where(Usuario.activo.is_(True), Usuario.rol_id.is_not(None)).order_by(Usuario.nombre), u)
    if debajo is not None:
        q = q.where(Usuario.id.in_(debajo | {u.id}))
    personas = list(db.scalars(q))
    cargan = {r.id for r in db.scalars(select(Rol)) if r.clave or "cargas.cargar" in roles.permisos_de(r)}
    roles_ = dict(db.execute(select(Rol.id, Rol.nombre)).all())
    return [{"id": p.id, "nombre": p.nombre, "rol": roles_.get(p.rol_id), "puede_cargar": p.rol_id in cargan, "yo": p.id == u.id}
            for p in personas]


# ---------------------------------------------------------------- cuentas (Desarrollador)
def _desarrolladores_activos(db: Session, salvo: int | None = None) -> int:
    q = select(func.count()).select_from(Usuario).join(Rol, Rol.id == Usuario.rol_id).where(Rol.clave == acceso.DESARROLLADOR,
                                                                                           Usuario.activo.is_(True))
    if salvo is not None:
        q = q.where(Usuario.id != salvo)
    return db.scalar(q) or 0


def _es_desarrollador(db: Session, persona: Usuario) -> bool:
    rol = db.get(Rol, persona.rol_id) if persona.rol_id else None
    return bool(rol and rol.clave == acceso.DESARROLLADOR)


def _asignaciones(db: Session, persona: Usuario) -> tuple[int, int]:
    """(indicadores de los que es responsable, indicadores activos en los que es el ÚNICO cargador)."""
    responsable = db.scalar(select(func.count()).select_from(Indicador).where(Indicador.responsable_id == persona.id)) or 0
    otros = select(IndicadorCargador.indicador_id).where(IndicadorCargador.usuario_id != persona.id)
    unico = db.scalar(select(func.count()).select_from(IndicadorCargador).join(Indicador, Indicador.id == IndicadorCargador.indicador_id)
                      .where(IndicadorCargador.usuario_id == persona.id, Indicador.activo.is_(True),
                             IndicadorCargador.indicador_id.not_in(otros))) or 0
    return responsable, unico


def _exigir_sin_asignaciones(db: Session, persona: Usuario, accion: str) -> None:
    responsable, unico = _asignaciones(db, persona)
    if responsable or unico:
        partes = [t for n, t in ((responsable, f"es responsable de {responsable} indicador(es)"),
                                 (unico, f"es la única persona que carga {unico} indicador(es)")) if n]
        raise Conflicto(f"«{persona.nombre}» {' y '.join(partes)}: reasígnelos a otra persona antes de {accion}.")


def crear_cuenta(db: Session, dev: Usuario, datos) -> Usuario:
    """Cuenta nueva SIN rol: acceso denegado por defecto hasta que el Coordinador SGC la asigne."""
    if db.scalar(select(Usuario).where(Usuario.username == datos.username)):
        raise Invalido("Ese nombre de usuario ya existe.")
    nuevo = Usuario(username=datos.username, nombre=datos.nombre.strip(), email=datos.email or None,
                    password_hash=security.hash_password(datos.password))
    db.add(nuevo)
    db.flush()
    auditoria.registrar(db, dev, "USUARIO_CREADO", "usuario", nuevo.id, {"username": nuevo.username, "rol": None})
    db.commit()
    return nuevo


def editar_cuenta(db: Session, dev: Usuario, usuario_id: int, datos) -> Usuario:
    """Nombre, correo, habilitar / inhabilitar y restablecer la contraseña. El rol y el ámbito no se tocan aquí."""
    p = obtener(db, dev, usuario_id)
    if not datos.activo and p.activo:
        if p.id == dev.id:
            raise Invalido("No puede inhabilitarse a sí mismo.")
        if _es_desarrollador(db, p) and not _desarrolladores_activos(db, salvo=p.id):
            raise Conflicto("El sistema no puede quedar sin un Desarrollador activo.")
        _exigir_sin_asignaciones(db, p, "inhabilitarlo")
    nuevos = {"nombre": datos.nombre.strip(), "activo": datos.activo}
    if datos.email is not None:   # sin el campo no se toca; con "" se borra
        nuevos["email"] = datos.email or None
    cambios = {}
    for campo, valor in nuevos.items():
        if getattr(p, campo) != valor:
            cambios[campo] = [getattr(p, campo), valor]
            setattr(p, campo, valor)
    if datos.password:
        p.password_hash = security.hash_password(datos.password)
        p.sesion_v += 1   # cierra sus sesiones activas
        cambios["password"] = "restablecida"
    if "activo" in cambios and not datos.activo:
        p.sesion_v += 1
    if cambios:
        auditoria.registrar(db, dev, "USUARIO_EDITADO", "usuario", p.id, {"username": p.username, "cambios": cambios})
    db.commit()
    return p


def ids_con_historial(db: Session, ids: list[int] | None = None) -> set[int]:
    """Usuarios que figuran en algún registro (bitácora, cargas, revisiones, notas, ejercicios o metas). A esos no se
    les puede borrar sin romper la trazabilidad: se inhabilitan."""
    columnas = [Bitacora.usuario_id, Medicion.cargado_por_id, Medicion.revisado_por_id, NotaAuditoria.usuario_id,
                Ejercicio.creado_por_id, Ejercicio.cerrado_por_id, Ejercicio.reabierto_por_id, Meta.actualizado_por_id]
    consultas = [select(c) if ids is None else select(c).where(c.in_(ids)) for c in columnas]
    return {i for i in db.scalars(union(*consultas)) if i is not None}


def ultimos_ingresos(db: Session, ids: list[int] | None = None) -> dict[int, object]:
    """{usuario_id: fecha de su último ingreso}, en una sola consulta (para el soporte a usuarios)."""
    q = select(Bitacora.usuario_id, func.max(Bitacora.fecha)).where(Bitacora.accion == "INICIO_SESION")
    if ids is not None:
        q = q.where(Bitacora.usuario_id.in_(ids))
    return {uid: fecha for uid, fecha in db.execute(q.group_by(Bitacora.usuario_id)) if uid is not None}


def eliminar_cuenta(db: Session, dev: Usuario, usuario_id: int) -> None:
    """Borra definitivamente una cuenta que nunca tuvo actividad (creada por error). Con historial, se inhabilita."""
    p = obtener(db, dev, usuario_id)
    if p.id == dev.id:
        raise Invalido("No puede eliminar su propia cuenta.")
    if _es_desarrollador(db, p) and p.activo and not _desarrolladores_activos(db, salvo=p.id):
        raise Conflicto("El sistema no puede quedar sin un Desarrollador activo.")
    if db.scalar(select(Indicador.id).where(Indicador.responsable_id == p.id).limit(1)) or \
            db.scalar(select(IndicadorCargador.indicador_id).where(IndicadorCargador.usuario_id == p.id).limit(1)):
        raise Conflicto("Tiene indicadores asignados (como responsable o cargador): reasígnelos antes de eliminarlo.")
    if p.id in ids_con_historial(db, [p.id]):
        raise Conflicto("Este usuario tiene actividad registrada (ingresos, cargas o revisiones) y no puede eliminarse sin perder la "
                        "trazabilidad. Inhabilítelo: no podrá ingresar y su historial se conserva.")
    auditoria.registrar(db, dev, "USUARIO_ELIMINADO", "usuario", p.id, {"username": p.username, "nombre": p.nombre})
    db.delete(p)
    db.commit()


def designar_desarrollador(db: Session, dev: Usuario, usuario_id: int, activar: bool, password: str) -> Usuario:
    """Procedimiento explícito (solo entre Desarrolladores, reconfirmando la contraseña): dar o quitar el rol Desarrollador.
    Al quitarlo, la cuenta queda pendiente de asignación."""
    if not acceso.es_desarrollador(dev):
        raise Prohibido(acceso.SIN_PERMISO)
    reinicio.exigir_password(dev, password, f"desarrollador|{dev.id}")
    p = obtener(db, dev, usuario_id)
    es_dev = _es_desarrollador(db, p)
    if activar == es_dev:
        raise Conflicto("La cuenta ya es de un Desarrollador." if es_dev else "La cuenta no es de un Desarrollador.")
    if activar:
        if not p.activo:
            raise Invalido("Habilite la cuenta antes de designarla.")
        p.rol_id, p.ambito_raiz = roles.de_sistema(db, acceso.DESARROLLADOR).id, False
    else:
        if p.id == dev.id:
            raise Invalido("No puede quitarse a sí mismo el rol Desarrollador: debe hacerlo otro Desarrollador.")
        if p.activo and not _desarrolladores_activos(db, salvo=p.id):
            raise Conflicto("El sistema no puede quedar sin un Desarrollador activo.")
        _exigir_sin_asignaciones(db, p, "quitarle el rol")
        p.rol_id = None
    p.sesion_v += 1
    auditoria.registrar(db, dev, "DESARROLLADOR_DESIGNADO" if activar else "DESARROLLADOR_RETIRADO", "usuario", p.id, {"username": p.username})
    db.commit()
    return p


# ---------------------------------------------------------------- soporte (Desarrollador)
def cerrar_sesiones(db: Session, dev: Usuario, usuario_id: int) -> None:
    """Saca a un usuario de todos sus dispositivos (sube su versión de sesión). Debe volver a ingresar."""
    p = obtener(db, dev, usuario_id)
    if p.id == dev.id:
        raise Invalido("Para cerrar su propia sesión use «Cerrar sesión» del menú de su perfil.")
    p.sesion_v += 1
    auditoria.registrar(db, dev, "SESIONES_CERRADAS", "usuario", p.id, {"username": p.username})
    db.commit()


def desbloquear_accesos(db: Session, dev: Usuario) -> None:
    """Levanta el bloqueo por intentos fallidos de ingreso (de todos los usuarios y orígenes)."""
    limite_intentos.reiniciar()
    auditoria.registrar(db, dev, "ACCESOS_DESBLOQUEADOS", "sistema", None, {})
    db.commit()


# ---------------------------------------------------------------- asignación (Coordinador SGC)
def _exigir_asignable(db: Session, u: Usuario, usuario_id: int) -> Usuario:
    p = obtener(db, u, usuario_id)
    if _es_desarrollador(db, p):
        raise Conflicto("El rol y el ámbito de un Desarrollador no se asignan aquí: use «Designar Desarrollador».")
    if p.id == u.id:
        raise Prohibido("No puede cambiar su propio rol, ámbito ni indicadores: debe hacerlo otra persona autorizada.")
    return p


def asignar(db: Session, u: Usuario, usuario_id: int, rol_id: int | None, raiz: bool, ambito: list[int], miembro: list[int]) -> Usuario:
    """Rol y posición en el árbol de una persona. `ambito`: nodos que ve completos; `miembro`: nodos donde solo trabaja."""
    p = _exigir_asignable(db, u, usuario_id)
    rol = db.get(Rol, rol_id) if rol_id else None
    if rol_id and (not rol or rol.clave == acceso.DESARROLLADOR):
        raise Invalido("Rol inexistente." if not rol or not acceso.es_desarrollador(u) else
                       "El rol Desarrollador solo se da con «Designar Desarrollador».")
    anterior = db.get(Rol, p.rol_id) if p.rol_id else None
    if rol is not anterior:
        for r in (rol, anterior):   # dar o quitar el rol Coordinador SGC es cosa del Desarrollador
            if r is not None and r.clave == acceso.COORDINADOR and not acceso.es_desarrollador(u):
                raise Prohibido("Solo un Desarrollador puede dar o quitar el rol Coordinador SGC.")
        if rol is not None:
            propios = acceso.contexto(u).permisos
            ajenos = [cat.POR_CODIGO[c].etiqueta for c, n in roles.permisos_de(rol).items() if not cat.alcanza(propios.get(c), n)]
            if ajenos:
                raise Prohibido("No puede dar un rol con permisos que usted no tiene: " + ", ".join(ajenos[:4]) + ".")
        responsable, _ = _asignaciones(db, p)
        carga = db.scalar(select(func.count()).select_from(IndicadorCargador).where(IndicadorCargador.usuario_id == p.id)) or 0
        if rol is None and (responsable or carga):
            raise Conflicto(f"«{p.nombre}» tiene indicadores asignados: reasígnelos antes de dejarlo sin rol.")
        if rol is not None and carga and not (rol.clave or "cargas.cargar" in roles.permisos_de(rol)):
            raise Conflicto(f"«{p.nombre}» carga {carga} indicador(es) y el rol «{rol.nombre}» no permite cargar datos: "
                            "reasigne esos indicadores o elija otro rol.")
    ambito, miembro = sorted(set(ambito)), sorted(set(miembro))
    if set(ambito) & set(miembro):
        raise Invalido("Un mismo nodo no puede ser a la vez ámbito y lugar de trabajo de la persona.")
    pedidos = set(ambito) | set(miembro)
    if pedidos and len(set(db.scalars(select(Unidad.id).where(Unidad.id.in_(pedidos))))) != len(pedidos):
        raise Invalido("Alguno de los nodos indicados no existe.")
    antes = {"rol": anterior.nombre if anterior else None, "raiz": bool(p.ambito_raiz),
             "ambito": sorted(e.unidad_id for e in p.enlaces if e.tipo == "ambito"),
             "miembro": sorted(e.unidad_id for e in p.enlaces if e.tipo == "miembro")}
    despues = {"rol": rol.nombre if rol else None, "raiz": bool(raiz), "ambito": ambito, "miembro": miembro}
    if antes != despues:
        p.rol_id, p.ambito_raiz = (rol.id if rol else None), bool(raiz)
        p.enlaces = [UsuarioUnidad(unidad_id=n, tipo="ambito") for n in ambito] + [UsuarioUnidad(unidad_id=n, tipo="miembro") for n in miembro]
        auditoria.registrar(db, u, "USUARIO_ASIGNADO", "usuario", p.id,
                            {"username": p.username, "cambios": {k: [antes[k], despues[k]] for k in antes if antes[k] != despues[k]}})
    db.commit()
    return p


def indicadores_de(db: Session, u: Usuario, usuario_id: int) -> dict:
    p = obtener(db, u, usuario_id)

    def item(i: Indicador) -> dict:
        return {"id": i.id, "codigo": i.codigo, "nombre": i.nombre, "nodo": i.nodo.nombre, "activo": i.activo}
    resp = db.scalars(select(Indicador).where(Indicador.responsable_id == p.id).order_by(Indicador.codigo)).all()
    carg = db.scalars(select(Indicador).join(IndicadorCargador, IndicadorCargador.indicador_id == Indicador.id)
                      .where(IndicadorCargador.usuario_id == p.id).order_by(Indicador.codigo)).all()
    return {"responsable": [item(i) for i in resp], "cargador": [item(i) for i in carg]}


def asignar_indicadores(db: Session, u: Usuario, usuario_id: int, responsable: list[int], cargador: list[int]) -> dict:
    """Deja a la persona como responsable y como cargador exactamente de los indicadores indicados. La responsabilidad
    no se «quita»: se traspasa asignándosela a otra persona; un indicador no puede quedar sin nadie que lo cargue."""
    p = _exigir_asignable(db, u, usuario_id)
    if not p.activo or not p.rol_id:
        raise Invalido("Asigne primero un rol a la persona (y verifique que su cuenta esté activa).")
    rol = db.get(Rol, p.rol_id)
    responsable, cargador = set(responsable), set(cargador)
    pedidos = responsable | cargador
    inds = {i.id: i for i in db.scalars(select(Indicador).where(Indicador.id.in_(pedidos)))} if pedidos else {}
    if len(inds) != len(pedidos):
        raise Invalido("Alguno de los indicadores indicados no existe.")
    if cargador and not (rol.clave or "cargas.cargar" in roles.permisos_de(rol)):
        raise Invalido(f"El rol «{rol.nombre}» no permite cargar datos: no puede quedar como cargador.")
    actuales_resp = set(db.scalars(select(Indicador.id).where(Indicador.responsable_id == p.id)))
    actuales_carg = set(db.scalars(select(IndicadorCargador.indicador_id).where(IndicadorCargador.usuario_id == p.id)))
    if actuales_resp - responsable:
        codigos = list(db.scalars(select(Indicador.codigo).where(Indicador.id.in_(actuales_resp - responsable)).order_by(Indicador.codigo)))
        raise Conflicto("La responsabilidad no se quita, se traspasa: asigne " + ", ".join(codigos[:6]) + " a otra persona.")
    cambios = {"responsable_de": [], "cargador_de": [], "deja_de_cargar": []}
    for iid in sorted(responsable - actuales_resp):
        inds[iid].responsable_id = p.id
        cambios["responsable_de"].append(inds[iid].codigo)
    for iid in sorted(cargador - actuales_carg):
        db.add(IndicadorCargador(indicador_id=iid, usuario_id=p.id))
        cambios["cargador_de"].append(inds[iid].codigo)
    for iid in sorted(actuales_carg - cargador):
        ind = db.get(Indicador, iid)
        if len(ind.cargadores) <= 1:
            raise Conflicto(f"{ind.codigo} quedaría sin nadie que lo cargue: asígnele antes otro cargador.")
        db.execute(IndicadorCargador.__table__.delete().where(IndicadorCargador.indicador_id == iid, IndicadorCargador.usuario_id == p.id))
        cambios["deja_de_cargar"].append(ind.codigo)
    cambios = {k: v for k, v in cambios.items() if v}
    if cambios:
        auditoria.registrar(db, u, "INDICADORES_ASIGNADOS", "usuario", p.id, {"username": p.username, **cambios})
    db.commit()
    db.expire_all()
    return indicadores_de(db, u, usuario_id)


# ---------------------------------------------------------------- «qué ve esta persona»
def alcance(db: Session, u: Usuario, usuario_id: int, propuesta: dict | None = None) -> dict:
    """Lo que la persona alcanza con su asignación actual o, con `propuesta` ({rol_id, raiz, ambito, miembro}), con la que
    se está por guardar: permisos en lenguaje natural, nodos e indicadores visibles con el motivo de cada uno."""
    p = obtener(db, u, usuario_id)
    if propuesta is None:
        ctx = acceso.preparar(db, db.get(Usuario, p.id)) if p.id != u.id else acceso.contexto(u)
        sujeto = p
    else:
        rol = db.get(Rol, propuesta.get("rol_id")) if propuesta.get("rol_id") else None
        if rol is not None and rol.clave == acceso.DESARROLLADOR and not acceso.es_desarrollador(u):
            raise Invalido("Rol inexistente.")
        rutas = dict(db.execute(select(Unidad.id, Unidad.ruta).where(Unidad.id.in_([*propuesta.get("ambito", []), *propuesta.get("miembro", [])]))).all())
        ctx = acceso.Contexto(permisos=roles.permisos_de(rol) if rol else {}, clave=rol.clave if rol else None,
                              rol=rol.nombre if rol else "", raiz=bool(propuesta.get("raiz")),
                              ambito=tuple((i, rutas[i]) for i in propuesta.get("ambito", []) if i in rutas),
                              miembro=tuple((i, rutas[i]) for i in propuesta.get("miembro", []) if i in rutas))
        sujeto = Usuario(id=p.id, nombre=p.nombre)
        sujeto.acceso = ctx
    nodos = estructura.todas(db)
    rutas_ambito = [r for _, r in ctx.ambito]
    visibles = list(db.scalars(acceso.indicadores_visibles(select(Indicador).order_by(Indicador.codigo), sujeto)))
    a_cargo = set(db.scalars(select(IndicadorCargador.indicador_id).where(IndicadorCargador.usuario_id == p.id)))

    def motivo(i: Indicador) -> str:
        if i.responsable_id == p.id:
            return "responsable"
        if i.id in a_cargo:
            return "cargador"
        return "alcance global" if ctx.global_ else "ámbito"
    return {"usuario": p.nombre, "rol": ctx.rol or None, "pendiente": not ctx.rol, "global": ctx.global_,
            "resumen": cat.resumen(ctx.permisos) if ctx.rol else ["Cuenta pendiente de asignación: no accede a nada."],
            "nodos": [{"id": n.id, "nombre": n.nombre, "nivel": n.nivel} for n in nodos if ctx.global_ or acceso.dentro(n.ruta, rutas_ambito)],
            "total": len(visibles), "modifica": sum(1 for i in visibles if i.responsable_id == p.id or ctx.total),
            "carga": sum(1 for i in visibles if i.activo and (i.id in a_cargo or ctx.total)),
            "indicadores": [{"id": i.id, "codigo": i.codigo, "nombre": i.nombre, "nodo": i.nodo.nombre, "motivo": motivo(i)}
                            for i in visibles[:300]]}
