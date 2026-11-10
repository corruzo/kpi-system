"""Meta anual por indicador (paso 3 del flujo): qué se espera lograr en cada período del ejercicio.

La meta se guarda por período de la frecuencia del indicador (12 valores si es mensual, 4 si es trimestral,
1 si es anual…). Se puede escribir período a período o dar un valor anual y repartirlo. Cada cambio queda en la bitácora.
Un período que ya tiene dato real cargado no admite cambios: se compara contra la meta que se fijó al inicio.
"""
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..dominio import calendario, meta
from ..errores import Conflicto, Invalido, NoEncontrado, Prohibido
from ..models import Indicador, Medicion, Meta, Rol, Unidad, Usuario, ahora
from . import acceso, auditoria, ejercicios


def lleva_meta(ind: Indicador) -> bool:
    """Los indicadores «eventuales» se cargan cuando ocurren: no tienen calendario que fijar metas."""
    return ind.frecuencia != "eventual"


def periodos_de(ind: Indicador, anio: int) -> list[str]:
    return calendario.periodos_del_ejercicio(ind.frecuencia, anio) if lleva_meta(ind) else []


def del_periodo(db: Session, indicador_id: int, periodo: str) -> float | None:
    fila = db.scalar(select(Meta).where(Meta.indicador_id == indicador_id, Meta.periodo == periodo))
    return fila.valor if fila else None


def exigir_meta(db: Session, ind: Indicador, periodo: str) -> float | None:
    """Meta del período; si el indicador debe tenerla y falta, lanza Conflicto."""
    if not lleva_meta(ind):
        return None
    valor = del_periodo(db, ind.id, periodo)
    if valor is None:
        raise Conflicto("Este período todavía no tiene meta. Debe ingresarse en «Período y metas» antes de cargar el dato real.")
    return valor


# ---------------------------------------------------------------- consulta
def _indicadores(db: Session, u: Usuario, nodo_id: int | None) -> list[Indicador]:
    q = acceso.indicadores_visibles(select(Indicador).order_by(Indicador.codigo), u)
    if nodo_id:
        q = q.where(acceso.en_nodo(nodo_id))
    return list(db.scalars(q))


def matriz(db: Session, u: Usuario, anio: int, nodo_id: int | None = None) -> dict:
    """Metas del ejercicio de los indicadores que la persona ve: por indicador, sus períodos con valor (o vacío), si ya
    tienen dato real y si ella puede cambiarlas (`editable`: propios y de quienes están debajo)."""
    inds = _indicadores(db, u, nodo_id)
    ids = [i.id for i in inds]
    guardados = {(p.indicador_id, p.periodo): p.valor
                 for p in db.scalars(select(Meta).where(Meta.ejercicio == anio, Meta.indicador_id.in_(ids)))} if ids else {}
    cargados = set(db.execute(select(Medicion.indicador_id, Medicion.periodo)
                              .where(Medicion.ejercicio == anio, Medicion.indicador_id.in_(ids))).all()) if ids else set()
    puede = acceso.puede(u, "metas.cargar")
    debajo = acceso.personas_debajo(db, u) if puede else set()
    filas, completos, total = [], 0, 0
    for ind in inds:
        periodos = periodos_de(ind, anio)
        if not periodos:
            continue
        items = [{"periodo": p, "etiqueta": calendario.etiqueta(ind.frecuencia, p), "corta": calendario.etiqueta_corta(ind.frecuencia, p),
                  "valor": guardados.get((ind.id, p)), "bloqueado": (ind.id, p) in cargados} for p in periodos]
        con_valor = sum(i["valor"] is not None for i in items)
        total += 1
        completos += con_valor == len(items)
        filas.append({"indicador_id": ind.id, "codigo": ind.codigo, "nombre": ind.nombre, "area": ind.nodo.nombre,
                      "nodo_id": ind.nodo_id, "unidad": ind.unidad, "frecuencia": ind.frecuencia, "sentido": ind.sentido,
                      "decimales": ind.precision, "periodos": items, "completo": con_valor == len(items), "con_valor": con_valor,
                      "editable": puede and acceso.puede_fijar_meta(db, u, ind, debajo)})
    return {"ejercicio": anio, "etiqueta": calendario.etiqueta_ejercicio(anio), "indicadores": filas,
            "resumen": {"total": total, "completos": completos, "pendientes": total - completos}}


def resumen(db: Session, u: Usuario, anio: int) -> dict:
    return matriz(db, u, anio)["resumen"]


# ---------------------------------------------------------------- escritura
def _fijable(db: Session, u: Usuario, indicador_id: int, debajo: set[int] | None = None) -> Indicador:
    """El indicador, si la persona lo ve (si no, 404) y puede fijar su meta: es suyo o de alguien debajo (si no, 403)."""
    ind = acceso.exigir_visible(u, db.get(Indicador, indicador_id))
    if not ind.activo:
        raise NoEncontrado("Indicador no encontrado.")
    if not acceso.puede_fijar_meta(db, u, ind, debajo):
        raise Prohibido("Solo puede fijar la meta de sus indicadores y de los de quienes están debajo de usted.")
    return ind


def guardar(db: Session, u: Usuario, anio: int, indicador_id: int, valores: dict[str, float], confirmar: bool = True,
            debajo: set[int] | None = None) -> dict:
    """Guarda (crea o cambia) la meta de un indicador. `valores`: {período: valor}.
    `confirmar=False` deja la transacción abierta para que quien llama confirme una sola vez (todo o nada)."""
    ind = _fijable(db, u, indicador_id, debajo)
    ejercicios.exigir_creado(db, anio)
    ejercicios.exigir_abierto(db, anio)
    if not lleva_meta(ind):
        raise Invalido("Los indicadores eventuales no llevan meta: se cargan cuando ocurren.")
    validos = set(periodos_de(ind, anio))
    if not valores:
        raise Invalido("No hay valores que guardar.")
    desconocidos = sorted(set(valores) - validos)
    if desconocidos:
        raise Invalido("Períodos que no pertenecen a este indicador en el ejercicio: " + ", ".join(desconocidos) + ".")
    existentes = {p.periodo: p for p in db.scalars(select(Meta).where(Meta.indicador_id == ind.id, Meta.periodo.in_(list(valores))))}
    cargados = set(db.scalars(select(Medicion.periodo).where(Medicion.indicador_id == ind.id, Medicion.periodo.in_(list(valores)))))
    cambios = {}
    for periodo, valor in valores.items():
        previo = existentes.get(periodo)
        if previo and previo.valor == valor:
            continue
        if periodo in cargados:
            raise Conflicto(f"El período {calendario.etiqueta(ind.frecuencia, periodo)} ya tiene dato real cargado: "
                            "su meta no puede cambiarse.")
        cambios[periodo] = {"antes": previo.valor if previo else None, "despues": valor}
        if previo:
            previo.valor, previo.actualizado_por_id, previo.actualizado_en = valor, u.id, ahora()
        else:
            db.add(Meta(ejercicio=anio, indicador_id=ind.id, periodo=periodo, valor=valor, actualizado_por_id=u.id, actualizado_en=ahora()))
    if cambios:
        auditoria.registrar(db, u, "META_GUARDADA", "meta", ind.id, {"ejercicio": calendario.etiqueta_ejercicio(anio), "cambios": cambios}, ind)
    if confirmar:
        db.commit()
    return {"guardados": len(cambios)}


def repartir_anual(db: Session, u: Usuario, anio: int, indicador_id: int, valor: float, modo: str) -> dict:
    """Atajo: un valor anual repartido entre todos los períodos del ejercicio del indicador."""
    ind = _fijable(db, u, indicador_id)
    periodos = periodos_de(ind, anio)
    if not periodos:
        raise Invalido("Los indicadores eventuales no llevan meta.")
    try:
        partes = meta.repartir(valor, len(periodos), modo, ind.precision + 2)
    except ValueError as e:
        raise Invalido(str(e)) from None
    return guardar(db, u, anio, indicador_id, dict(zip(periodos, partes, strict=True)))


def copiar_de(db: Session, u: Usuario, anio: int, origen: int) -> dict:
    """Copia la meta de otro ejercicio a este, período a período por posición: solo indicadores sin meta aquí y solo los
    que la persona puede fijar (propios y de quienes están debajo)."""
    ejercicios.exigir_creado(db, anio)
    ejercicios.exigir_abierto(db, anio)
    debajo = acceso.personas_debajo(db, u)
    inds = [i for i in _indicadores(db, u, None) if acceso.puede_fijar_meta(db, u, i, debajo)]
    ids = [i.id for i in inds]
    anteriores = {(p.indicador_id, p.periodo): p.valor
                  for p in db.scalars(select(Meta).where(Meta.ejercicio == origen, Meta.indicador_id.in_(ids)))} if ids else {}
    con_meta = set(db.scalars(select(Meta.indicador_id).where(Meta.ejercicio == anio, Meta.indicador_id.in_(ids)).distinct())) if ids else set()
    copiados = 0
    for ind in inds:
        destino, fuente = periodos_de(ind, anio), periodos_de(ind, origen)
        if not destino or ind.id in con_meta:
            continue
        valores = [anteriores.get((ind.id, p)) for p in fuente]
        if any(v is None for v in valores):
            continue
        guardar(db, u, anio, ind.id, dict(zip(destino, valores, strict=True)), confirmar=False, debajo=debajo)
        copiados += 1
    db.commit()      # una sola transacción: o se copian todos los indicadores o ninguno
    return {"indicadores": copiados}


# ---------------------------------------------------------------- puesta en marcha (guía del Desarrollador)
def avance_de_puesta_en_marcha(db: Session, u: Usuario, hoy: date) -> dict:
    """Estado de cada paso para arrancar el sistema, en el orden en que deben hacerse (conteos, sin traer filas)."""
    def contar(tabla, *cond):
        return db.scalar(select(func.count()).select_from(tabla).where(*cond)) or 0
    coordinadores = contar(Usuario, Usuario.activo.is_(True), Usuario.rol_id.in_(select(Rol.id).where(Rol.clave == acceso.COORDINADOR)))
    n_nodos, n_roles = contar(Unidad), contar(Rol, Rol.de_sistema.is_(False))
    asignadas = contar(Usuario, Usuario.activo.is_(True), Usuario.rol_id.in_(select(Rol.id).where(Rol.clave.is_(None))))
    pendientes = contar(Usuario, Usuario.activo.is_(True), Usuario.rol_id.is_(None))
    n_ind = contar(Indicador, Indicador.activo.is_(True))
    anio = calendario.ejercicio_de_fecha(hoy)
    periodo_creado = ejercicios.creado(db, anio)
    pres = resumen(db, u, anio) if periodo_creado else {"total": 0, "completos": 0, "pendientes": 0}
    cargas = contar(Medicion, Medicion.ejercicio == anio)
    return {"ejercicio": anio, "etiqueta": calendario.etiqueta_ejercicio(anio), "pasos": [
        {"id": "cuentas", "hecho": coordinadores > 0, "detalle": f"{coordinadores} Coordinador(es) SGC · {pendientes} cuenta(s) pendiente(s) de asignación"},
        {"id": "estructura", "hecho": n_nodos > 0, "detalle": f"{n_nodos} nodo(s) en la estructura"},
        {"id": "personas", "hecho": n_roles > 0 and asignadas > 0, "detalle": f"{n_roles} rol(es) definido(s) · {asignadas} persona(s) asignada(s)"},
        {"id": "fichas", "hecho": n_ind > 0, "detalle": f"{n_ind} indicador(es)"},
        {"id": "periodo", "hecho": periodo_creado, "detalle": calendario.etiqueta_ejercicio(anio) + (" creado" if periodo_creado else " sin crear")},
        {"id": "meta", "hecho": periodo_creado and pres["total"] > 0 and pres["pendientes"] == 0,
         "detalle": f"{pres['completos']} de {pres['total']} indicadores con meta"},
        {"id": "carga", "hecho": cargas > 0, "detalle": f"{cargas} carga(s) en el ejercicio"},
    ]}
