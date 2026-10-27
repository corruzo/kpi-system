"""Fichas técnicas de indicadores: consulta según el rol, alta, edición, archivado y ficha por ejercicio."""
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..dominio import calendario, formulas, semaforo
from ..errores import Invalido, NoEncontrado, Prohibido
from ..models import Area, Indicador, Medicion, Usuario
from . import auditoria, ejercicios


# ---------------------------------------------------------------- acceso y consulta
def obtener_visible(db: Session, u: Usuario, indicador_id: int) -> Indicador:
    """El indicador, si el usuario puede verlo: el jefe solo los de su área; los archivados, solo el admin."""
    ind = db.get(Indicador, indicador_id)
    if not ind or (u.rol != "admin" and not ind.activo):
        raise NoEncontrado("Indicador no encontrado.")
    if u.rol == "jefe" and ind.area_id != u.area_id:
        raise Prohibido("Este indicador pertenece a otra área.")
    return ind


def estados_por_periodo(db: Session, indicador_id: int) -> dict[str, str]:
    return dict(db.execute(select(Medicion.periodo, Medicion.estado).where(Medicion.indicador_id == indicador_id)).all())


def listar(db: Session, u: Usuario) -> list[tuple[Indicador, int, list[str]]]:
    """(indicador, cargas registradas, períodos pendientes) de los indicadores visibles para el usuario."""
    q = select(Indicador).order_by(Indicador.codigo)
    if u.rol == "jefe":
        q = q.where(Indicador.area_id == u.area_id)
    if u.rol != "admin":
        q = q.where(Indicador.activo.is_(True))
    cargas = dict(db.execute(select(Medicion.indicador_id, func.count(Medicion.id)).group_by(Medicion.indicador_id)).all())
    hoy = date.today()
    return [(i, cargas.get(i.id, 0),
             calendario.periodos_pendientes(i.frecuencia, hoy, estados_por_periodo(db, i.id), i.creado_en.date()))
            for i in db.scalars(q)]


def periodos_de_carga(db: Session, u: Usuario, indicador_id: int) -> dict:
    """Períodos ofrecidos al cargar un indicador, con su carga existente y si su ejercicio está cerrado."""
    ind = obtener_visible(db, u, indicador_id)
    hoy = date.today()
    medidas = {m.periodo: m for m in db.scalars(select(Medicion).where(Medicion.indicador_id == indicador_id))}
    pendientes = calendario.periodos_pendientes(ind.frecuencia, hoy, {p: m.estado for p, m in medidas.items()}, ind.creado_en.date())
    return {"indicador": ind, "medidas": medidas, "pendientes": pendientes, "cerrados": ejercicios.anios_cerrados(db),
            "periodos": calendario.periodos_recientes(ind.frecuencia, hoy)}


def contexto_ficha(db: Session, ind: Indicador, ejercicio: int | None):
    """(año del ejercicio mostrado, ejercicios disponibles, períodos del ejercicio con su medición)."""
    hoy, f = date.today(), ind.frecuencia
    medidas = {m.periodo: m for m in db.scalars(select(Medicion).where(Medicion.indicador_id == ind.id))}
    vigente = calendario.ejercicio_de(f, calendario.periodo_actual(f, hoy))
    con_datos = sorted({calendario.ejercicio_de(f, p) for p in medidas}, reverse=True)
    disponibles = sorted(set(con_datos) | {vigente}, reverse=True)
    # sin ejercicio pedido: el vigente, o el más reciente con datos si el vigente aún está vacío
    anio = ejercicio if ejercicio in disponibles else (vigente if vigente in con_datos or not con_datos else con_datos[0])
    periodos = [{"periodo": p, "etiqueta": calendario.etiqueta(f, p), "corta": calendario.etiqueta_corta(f, p),
                 "medicion": medidas.get(p)} for p in calendario.periodos_del_ejercicio(f, anio)]
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
        semaforo.validar_umbrales(datos.meta, datos.limite, datos.sentido, datos.meta_tope, datos.limite_tope)
    except (formulas.FormulaError, ValueError) as e:
        raise Invalido(str(e)) from None
    if not db.get(Area, datos.area_id):
        raise Invalido("Área inexistente.")
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
        semaforo.validar_umbrales(datos.meta, datos.limite, datos.sentido, datos.meta_tope, datos.limite_tope)
        resultado = formulas.evaluar(datos.formula, datos.valores, datos.constantes, datos.decimales)
    except (formulas.FormulaError, ValueError) as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True, "resultado": resultado,
            "semaforo": semaforo.clasificar(resultado, datos.meta, datos.limite, datos.sentido, datos.meta_tope, datos.limite_tope)}


# ---------------------------------------------------------------- alta, edición y baja
def crear(db: Session, admin: Usuario, datos) -> Indicador:
    validar_ficha(db, datos)
    ind = Indicador(**campos_de_ficha(datos))
    db.add(ind)
    db.flush()
    auditoria.registrar(db, admin, "INDICADOR_CREADO", "indicador", ind.id,
                        {"codigo": ind.codigo, "nombre": ind.nombre, "formula": ind.formula, "meta": ind.meta,
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


def editar(db: Session, admin: Usuario, indicador_id: int, datos) -> Indicador:
    ind = db.get(Indicador, indicador_id)
    if not ind:
        raise NoEncontrado("Indicador no encontrado.")
    validar_ficha(db, datos, indicador_id)
    if db.scalar(select(Medicion.id).where(Medicion.indicador_id == indicador_id).limit(1)):
        _proteger_historial(ind, datos)
    nuevos = campos_de_ficha(datos)
    cambios = {k: [getattr(ind, k), v] for k, v in nuevos.items()
               if getattr(ind, k) != v and not (not getattr(ind, k) and not v)}
    for k, v in nuevos.items():
        setattr(ind, k, v)
    if cambios:
        auditoria.registrar(db, admin, "INDICADOR_EDITADO", "indicador", ind.id, {"codigo": ind.codigo, "cambios": cambios}, ind)
    db.commit()
    return ind


def eliminar(db: Session, admin: Usuario, indicador_id: int) -> bool:
    """Elimina el indicador; si ya tiene cargas se archiva para conservar la trazabilidad. Devuelve True si se archivó."""
    ind = db.get(Indicador, indicador_id)
    if not ind:
        raise NoEncontrado("Indicador no encontrado.")
    if db.scalar(select(Medicion.id).where(Medicion.indicador_id == indicador_id).limit(1)):
        ind.activo = False
        auditoria.registrar(db, admin, "INDICADOR_ARCHIVADO", "indicador", ind.id, {"codigo": ind.codigo}, ind)
        db.commit()
        return True
    auditoria.registrar(db, admin, "INDICADOR_ELIMINADO", "indicador", ind.id, {"codigo": ind.codigo, "nombre": ind.nombre}, ind)
    db.delete(ind)
    db.commit()
    return False
