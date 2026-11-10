"""Fichas técnicas de indicadores: consulta según el alcance de cada persona, alta, edición, asignación (nodo, responsable
y cargadores), archivado y ficha por ejercicio. Quién ve y quién modifica lo decide `acceso`."""

import unicodedata

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from ..dominio import calendario, formulas, semaforo
from ..errores import Conflicto, Invalido, Prohibido
from ..models import Indicador, Medicion, Meta, Unidad, Usuario
from . import acceso, auditoria, ejercicios

# Responsable y cargadores se cargan explícitamente (y en bloque) solo en las listas que los muestran
CON_ASIGNACION = (joinedload(Indicador.responsable), selectinload(Indicador.cargadores))


# ---------------------------------------------------------------- acceso y consulta
def obtener_visible(db: Session, u: Usuario, indicador_id: int) -> Indicador:
    """El indicador, si el usuario puede verlo (ver `acceso`); si no, 404 como si no existiera."""
    return acceso.exigir_visible(u, db.get(Indicador, indicador_id))


def estados_de_todos(db: Session, ids: list[int] | None = None) -> dict[int, dict[str, str]]:
    """{indicador_id: {período: estado}} de las cargas (de los indicadores `ids`, si se dan), en una sola consulta."""
    por_indicador: dict[int, dict[str, str]] = {}
    q = select(Medicion.indicador_id, Medicion.periodo, Medicion.estado)
    if ids is not None:
        q = q.where(Medicion.indicador_id.in_(ids))
    for indicador_id, periodo, estado in db.execute(q):
        por_indicador.setdefault(indicador_id, {})[periodo] = estado
    return por_indicador


def _dividir_pendientes(ind: Indicador, pendientes: list[str], ejercicio: int) -> tuple[list[str], dict[int, int]]:
    """Separa los períodos pendientes del ejercicio mostrado de los de otros ejercicios ({ejercicio: cantidad})."""
    aqui = [p for p in pendientes if calendario.ejercicio_de(ind.frecuencia, p) == ejercicio]
    otros: dict[int, int] = {}
    for p in pendientes:
        anio = calendario.ejercicio_de(ind.frecuencia, p)
        if anio != ejercicio:
            otros[anio] = otros.get(anio, 0) + 1
    return aqui, otros


def _consulta(u: Usuario, *, gestion: bool, q: str | None, nodo_id: int | None, frecuencia: str | None, activo: bool | None,
              cargables: bool = False):
    """Indicadores visibles y filtrados. `gestion` incluye los archivados (para quien los tiene en su ámbito o es su
    responsable); `cargables` deja solo aquellos a los que la persona puede cargar datos; `nodo_id` abarca su subárbol."""
    consulta = select(Indicador).where(acceso.condicion_carga(u) if cargables else acceso.condicion_visible(u, archivados=gestion))
    if q and q.strip():
        patron = "%" + q.strip().lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        consulta = consulta.join(Unidad, Unidad.id == Indicador.nodo_id).where(
            func.lower(Indicador.codigo + " " + Indicador.nombre + " " + Unidad.nombre).like(patron, escape="\\"))
    if nodo_id:
        consulta = consulta.where(acceso.en_nodo(nodo_id))
    if frecuencia:
        consulta = consulta.where(Indicador.frecuencia == frecuencia)
    if activo is not None:
        consulta = consulta.where(Indicador.activo.is_(activo))
    return consulta


def contar(db: Session, u: Usuario, *, gestion=False, q=None, nodo_id=None, frecuencia=None, activo=None, cargables=False) -> int:
    base = _consulta(u, gestion=gestion, q=q, nodo_id=nodo_id, frecuencia=frecuencia, activo=activo, cargables=cargables).order_by(None)
    return db.scalar(select(func.count()).select_from(base.subquery())) or 0


def listar(db: Session, u: Usuario, ejercicio: int | None = None, *, gestion=False, q=None, nodo_id=None, frecuencia=None,
           activo=None, desde=0, limite=None, cargables=False) -> list[tuple[Indicador, int, list[str], dict[int, int]]]:
    """(indicador, cargas registradas, pendientes del ejercicio, pendientes de otros ejercicios) de los indicadores
    visibles para el usuario, con filtros y paginación opcionales. Sin `ejercicio` se usa el vigente. Las cargas y los
    estados se consultan solo de los indicadores devueltos (no de toda la tabla)."""
    consulta = _consulta(u, gestion=gestion, q=q, nodo_id=nodo_id, frecuencia=frecuencia, activo=activo,
                         cargables=cargables).options(*CON_ASIGNACION).order_by(Indicador.codigo)
    if limite is not None:
        consulta = consulta.offset(max(desde, 0)).limit(max(1, min(limite, 500)))
    inds = list(db.scalars(consulta))
    ids = [i.id for i in inds]
    cargas = dict(db.execute(select(Medicion.indicador_id, func.count(Medicion.id)).where(Medicion.indicador_id.in_(ids))
                             .group_by(Medicion.indicador_id)).all()) if ids else {}
    hoy = calendario.hoy()
    anio = ejercicio or calendario.ejercicio_de_fecha(hoy)
    estados = estados_de_todos(db, ids) if ids else {}
    return [(i, cargas.get(i.id, 0),
             *_dividir_pendientes(i, calendario.periodos_pendientes(i.frecuencia, hoy, estados.get(i.id, {}), i.creado_en.date()), anio))
            for i in inds]


def periodos_de_carga(db: Session, u: Usuario, indicador_id: int, ejercicio: int | None = None) -> dict:
    """Períodos de UN ejercicio fiscal ofrecidos al cargar un indicador (sin `ejercicio`, el vigente), con su carga
    existente y si el ejercicio está cerrado. Los pendientes de otros ejercicios se informan aparte."""
    ind = obtener_visible(db, u, indicador_id)
    hoy = calendario.hoy()
    medidas = {m.periodo: m for m in db.scalars(select(Medicion).where(Medicion.indicador_id == indicador_id).options(selectinload(Medicion.notas)))}
    anio = ejercicio or calendario.ejercicio_de_fecha(hoy)
    todos = calendario.periodos_pendientes(ind.frecuencia, hoy, {p: m.estado for p, m in medidas.items()}, ind.creado_en.date())
    pendientes, otros = _dividir_pendientes(ind, todos, anio)
    periodos = calendario.periodos_hasta_hoy(ind.frecuencia, anio, hoy)
    con_meta = {p.periodo: p.valor for p in db.scalars(select(Meta).where(Meta.indicador_id == ind.id))}
    return {"indicador": ind, "medidas": medidas, "pendientes": pendientes, "pendientes_otros": otros, "ejercicio": anio,
            "metas": con_meta, "creado": ejercicios.creado(db, anio),
            "cerrados": ejercicios.anios_cerrados(db), "periodos": periodos}


def contexto_ficha(db: Session, ind: Indicador, ejercicio: int | None):
    """(año del ejercicio mostrado, ejercicios disponibles, períodos del ejercicio con su medición)."""
    hoy, f = calendario.hoy(), ind.frecuencia
    medidas = {m.periodo: m for m in db.scalars(select(Medicion).where(Medicion.indicador_id == ind.id).options(selectinload(Medicion.notas)))}
    vigente = calendario.ejercicio_de(f, calendario.periodo_actual(f, hoy))
    con_datos = sorted({calendario.ejercicio_de(f, p) for p in medidas}, reverse=True)
    disponibles = sorted(set(con_datos) | {vigente}, reverse=True)
    # sin ejercicio pedido: el vigente, o el más reciente con datos si el vigente aún está vacío
    anio = ejercicio if ejercicio in disponibles else (vigente if vigente in con_datos or not con_datos else con_datos[0])
    con_meta = {p.periodo: p.valor for p in db.scalars(select(Meta).where(Meta.indicador_id == ind.id))}
    periodos = [{"periodo": p, "etiqueta": calendario.etiqueta(f, p), "corta": calendario.etiqueta_corta(f, p),
                 "meta": con_meta.get(p), "medicion": medidas.get(p)}
                for p in calendario.periodos_del_ejercicio(f, anio)]
    return anio, disponibles, periodos


# ---------------------------------------------------------------- validación de la ficha
def campos_de_ficha(datos) -> dict:
    """Valores de la ficha listos para asignar al modelo (fórmula normalizada, variables como diccionarios)."""
    columnas = {c.name for c in Indicador.__table__.columns}
    base = {k: v for k, v in datos.model_dump(exclude={"variables", "constantes", "formula"}).items() if k in columnas}
    return {**base, "formula": formulas.normalizar(datos.formula),
            "variables": [v.model_dump() for v in datos.variables],
            "constantes": [c.model_dump() for c in datos.constantes]}


def validar_ficha(db: Session, datos, propio_id: int | None = None) -> None:
    variables = [v.clave for v in datos.variables]
    nombres = variables + [c.clave for c in datos.constantes]
    if len(set(nombres)) != len(nombres):
        raise Invalido("Las claves de variables y constantes no pueden repetirse.")
    reservadas = [c for c in nombres if c in formulas.RESERVADAS]
    if reservadas:
        raise Invalido(f"La clave «{reservadas[0]}» está reservada (función o palabra del lenguaje).")
    try:
        formulas.validar(datos.formula, nombres, variables)
        semaforo.validar_umbrales(datos.nivel_optimo, datos.limite, datos.sentido, datos.nivel_optimo_tope, datos.limite_tope)
    except (formulas.FormulaError, ValueError) as e:
        raise Invalido(str(e)) from None
    repetido = db.scalar(select(Indicador).where(Indicador.codigo == datos.codigo))
    if repetido and repetido.id != propio_id:
        raise Invalido(f"Ya existe un indicador con el código {datos.codigo}.")


def revisar_formula(datos) -> dict:
    """Valida una fórmula mientras se escribe (sin guardar nada)."""
    try:
        sin_usar = formulas.validar(datos.formula, datos.claves, datos.variables)
        return {"ok": True, "sin_usar": sin_usar, "normalizada": formulas.normalizar(datos.formula)}
    except formulas.FormulaError as e:
        return {"ok": False, "error": str(e)}


def probar_formula(datos) -> dict:
    """Resultado y semáforo con valores de ejemplo, antes de guardar la ficha."""
    try:
        semaforo.validar_umbrales(datos.nivel_optimo, datos.limite, datos.sentido, datos.nivel_optimo_tope, datos.limite_tope)
        resultado = formulas.evaluar(datos.formula, datos.valores, datos.constantes, datos.decimales)
    except (formulas.FormulaError, ValueError) as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True, "resultado": resultado,
            "semaforo": semaforo.clasificar(resultado, datos.nivel_optimo, datos.limite, datos.sentido, datos.nivel_optimo_tope, datos.limite_tope)}


# ---------------------------------------------------------------- código automático
def _prefijo(nodo: Unidad) -> str:
    """Tres letras del nodo, sin tildes ni símbolos (p. ej. «Calidad y Mejora» → CAL)."""
    base = "".join(c for c in unicodedata.normalize("NFD", nodo.nombre) if c.isalnum() and ord(c) < 128).upper()
    return (base or "IND")[:3]


def sugerir_codigo(db: Session, nodo_id: int) -> str:
    """Próximo código libre del nodo: PREFIJO-NN, con NN consecutivo entre los códigos ya registrados con ese prefijo.
    No reutiliza números de indicadores eliminados ni archivados (los archivados siguen en la tabla)."""
    nodo = db.get(Unidad, nodo_id)
    if not nodo:
        raise Invalido("Nodo de la estructura inexistente.")
    prefijo = _prefijo(nodo)
    usados = list(db.scalars(select(Indicador.codigo).where(Indicador.codigo.like(f"{prefijo}-%"))))
    numeros = [int(c[len(prefijo) + 1:]) for c in usados if c[len(prefijo) + 1:].isdigit()]
    return f"{prefijo}-{max(numeros, default=0) + 1:02d}"


# ---------------------------------------------------------------- asignación: nodo, responsable y cargadores
def _personas(db: Session, ids: list[int]) -> list[Usuario]:
    encontradas = {x.id: x for x in db.scalars(select(Usuario).where(Usuario.id.in_(ids)))} if ids else {}
    if len(encontradas) != len(set(ids)):
        raise Invalido("Alguna de las personas indicadas no existe.")
    return [encontradas[i] for i in dict.fromkeys(ids)]


def _resolver_asignacion(db: Session, u: Usuario, nodo_id: int, responsable_id: int | None, cargadores: list[int] | None):
    """(nodo, responsable, cargadores) ya validados contra la regla «a sí mismo o a personas debajo de él».
    Sin responsable indicado lo es quien crea; sin cargadores indicados, carga el responsable."""
    nodo = db.get(Unidad, nodo_id)
    if not nodo:
        raise Invalido("Nodo de la estructura inexistente.")
    responsable = _personas(db, [responsable_id or u.id])[0]
    quienes = _personas(db, cargadores if cargadores else [responsable.id])
    if acceso.contexto(responsable).clave == acceso.DESARROLLADOR and not acceso.es_desarrollador(u):
        raise Invalido("Alguna de las personas indicadas no existe.")
    acceso.exigir_asignacion(db, u, nodo, responsable, quienes)
    return nodo, responsable, quienes


def asignar(db: Session, u: Usuario, indicador_id: int, nodo_id: int, responsable_id: int, cargadores: list[int]) -> Indicador:
    """Cambia el nodo, el responsable y quienes cargan. Puede hacerlo quien tiene el indicador en su ámbito o es su
    responsable, y solo hacia sí mismo o personas debajo de él (los roles de sistema, sin restricción)."""
    ind = obtener_visible(db, u, indicador_id)
    if not (acceso.alcance_total(u) or acceso.en_ambito(u, ind) or acceso.es_responsable(u, ind)):
        raise Prohibido("Solo puede reasignar indicadores de su ámbito o de los que es responsable.")
    if not cargadores:
        raise Invalido("Indique al menos una persona que cargue el indicador.")
    nodo, responsable, quienes = _resolver_asignacion(db, u, nodo_id, responsable_id, cargadores)
    antes = {"nodo": ind.nodo.nombre, "responsable": ind.responsable.nombre if ind.responsable else None,
             "cargadores": sorted(x.nombre for x in ind.cargadores)}
    despues = {"nodo": nodo.nombre, "responsable": responsable.nombre, "cargadores": sorted(x.nombre for x in quienes)}
    if antes != despues:
        ind.nodo_id, ind.responsable_id, ind.cargadores = nodo.id, responsable.id, quienes
        ind.nodo, ind.responsable = nodo, responsable
        auditoria.registrar(db, u, "INDICADOR_ASIGNADO", "indicador", ind.id,
                            {"codigo": ind.codigo, "cambios": {k: [antes[k], despues[k]] for k in antes if antes[k] != despues[k]}}, ind)
    db.commit()
    return ind


# ---------------------------------------------------------------- alta, edición y baja
SOLO_AL_CREAR = ("codigo", "nodo_id", "responsable_id", "activo")   # la edición de la ficha no los toca (ver `asignar` y `archivar`)


def crear(db: Session, u: Usuario, datos) -> Indicador:
    nodo, responsable, quienes = _resolver_asignacion(db, u, datos.nodo_id, datos.responsable_id, datos.cargadores)
    if not datos.codigo:
        datos.codigo = sugerir_codigo(db, nodo.id)
    validar_ficha(db, datos)
    campos = campos_de_ficha(datos)
    if not campos.get("gerencia"):   # por defecto, la gerencia de la que cuelga el nodo
        campos["gerencia"] = db.get(Unidad, int(nodo.ruta.strip("/").split("/")[0])).nombre
    ind = Indicador(**{**campos, "responsable_id": responsable.id, "activo": True})
    ind.cargadores = quienes
    db.add(ind)
    db.flush()
    auditoria.registrar(db, u, "INDICADOR_CREADO", "indicador", ind.id,
                        {"codigo": ind.codigo, "nombre": ind.nombre, "nodo": nodo.nombre, "responsable": responsable.nombre,
                         "cargadores": [x.nombre for x in quienes], "formula": ind.formula, "nivel_optimo": ind.nivel_optimo,
                         "limite": ind.limite, "sentido": ind.sentido}, ind)
    db.commit()
    return ind


def _proteger_historial(ind: Indicador, datos) -> None:
    """Con cargas registradas no se pueden alterar la frecuencia ni las claves (rompería el histórico)."""
    if datos.frecuencia != ind.frecuencia:
        raise Invalido("No se puede cambiar la frecuencia de un indicador con cargas registradas.")
    claves_nuevas = ({v.clave for v in datos.variables}, {c.clave for c in datos.constantes})
    claves_actuales = ({v["clave"] for v in ind.variables}, {c["clave"] for c in (ind.constantes or [])})
    if claves_nuevas != claves_actuales:
        raise Invalido("No se pueden agregar, quitar ni renombrar claves de variables de un indicador con cargas "
                       "registradas. Archívelo y cree uno nuevo.")


def _modificable(db: Session, u: Usuario, indicador_id: int) -> Indicador:
    """El indicador, si la persona lo ve (si no, 404) y además es su responsable (si no, 403)."""
    ind = obtener_visible(db, u, indicador_id)
    acceso.exigir_modificable(u, ind)
    return ind


def editar(db: Session, u: Usuario, indicador_id: int, datos) -> Indicador:
    """Cambia la ficha (no el nodo, el responsable, los cargadores ni el estado: eso va por `asignar` y `archivar`)."""
    ind = _modificable(db, u, indicador_id)
    datos.codigo = ind.codigo   # el código identifica al indicador en bitácora y reportes: no se cambia
    validar_ficha(db, datos, indicador_id)
    if db.scalar(select(Medicion.id).where(Medicion.indicador_id == indicador_id).limit(1)):
        _proteger_historial(ind, datos)
    nuevos = {k: v for k, v in campos_de_ficha(datos).items() if k not in SOLO_AL_CREAR}
    cambios = {k: [getattr(ind, k), v] for k, v in nuevos.items()
               if getattr(ind, k) != v and not (not getattr(ind, k) and not v)}
    if "frecuencia" in cambios:   # sus períodos cambian: la meta por período ya no corresponde y debe ingresarse de nuevo
        db.execute(delete(Meta).where(Meta.indicador_id == ind.id))
    for k, v in nuevos.items():
        setattr(ind, k, v)
    if cambios:
        auditoria.registrar(db, u, "INDICADOR_EDITADO", "indicador", ind.id, {"codigo": ind.codigo, "cambios": cambios}, ind)
    db.commit()
    return ind


def archivar(db: Session, u: Usuario, indicador_id: int, archivado: bool) -> Indicador:
    """Archiva (deja de ofrecerse para cargar; conserva su historial) o restaura un indicador."""
    ind = _modificable(db, u, indicador_id)
    if ind.activo == archivado:
        ind.activo = not archivado
        auditoria.registrar(db, u, "INDICADOR_ARCHIVADO" if archivado else "INDICADOR_RESTAURADO", "indicador", ind.id, {"codigo": ind.codigo}, ind)
    db.commit()
    return ind


def eliminar(db: Session, u: Usuario, indicador_id: int) -> None:
    """Elimina definitivamente un indicador sin cargas. Con cargas no se borra (trazabilidad): se archiva."""
    ind = _modificable(db, u, indicador_id)
    if db.scalar(select(Medicion.id).where(Medicion.indicador_id == indicador_id).limit(1)):
        raise Conflicto(f"{ind.codigo} tiene cargas registradas: no se puede eliminar sin perder la trazabilidad. Archívelo.")
    auditoria.registrar(db, u, "INDICADOR_ELIMINADO", "indicador", ind.id, {"codigo": ind.codigo, "nombre": ind.nombre}, ind)
    db.execute(delete(Meta).where(Meta.indicador_id == ind.id))   # sin cargas: su meta se va con él
    db.delete(ind)   # la relación `cargadores` borra también sus filas de asignación
    db.commit()
