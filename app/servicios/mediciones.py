"""Cargas de indicadores: cálculo, envío, aprobación jerárquica, reapertura y notas de auditoría."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..dominio import calendario, formulas, meta, semaforo
from ..errores import Conflicto, Invalido, NoEncontrado, Prohibido
from ..models import Indicador, Medicion, NotaAuditoria, Usuario, ahora
from . import acceso, auditoria, ejercicios, indicadores, metas

MIN_TEXTO_ANALISIS = 10    # caracteres exigidos al análisis y al plan de mejora cuando el semáforo no es verde
MIN_TEXTO_NOTA = 5


# ---------------------------------------------------------------- cálculo
def evaluar_carga(ind: Indicador, valores: dict) -> dict:
    """Valida los datos ingresados, evalúa la fórmula y clasifica el resultado.
    Devuelve {ok, resultado, semaforo, requiere_analisis, valores} o {ok: False, error}."""
    finales, faltan = {}, []
    for v in ind.variables:
        x = valores.get(v["clave"])
        if x is None:
            if not v.get("opcional"):
                faltan.append(v["etiqueta"])
                continue
            x = v.get("defecto", 0)
        if x < 0 and not v.get("negativo"):
            return {"ok": False, "error": f"«{v['etiqueta']}» no puede ser negativo."}
        finales[v["clave"]] = float(x)
    if faltan:
        return {"ok": False, "error": "Complete: " + ", ".join(faltan) + "."}
    constantes = {c["clave"]: c["valor"] for c in (ind.constantes or [])}
    try:
        resultado = formulas.evaluar(ind.formula, finales, constantes, ind.precision)
    except formulas.FormulaError as e:
        return {"ok": False, "error": str(e)}
    color = semaforo.clasificar(resultado, ind.nivel_optimo, ind.limite, ind.sentido, ind.nivel_optimo_tope, ind.limite_tope)
    return {"ok": True, "resultado": resultado, "semaforo": color, "requiere_analisis": color != "verde", "valores": finales}


def calcular(db: Session, u: Usuario, indicador_id: int, valores: dict, periodo: str | None = None) -> dict:
    """Resultado en vivo; con `periodo` incluye la comparación contra la meta para ese período."""
    ind = indicadores.obtener_visible(db, u, indicador_id)
    acceso.exigir_cargable(u, ind)
    r = evaluar_carga(ind, valores)
    if r["ok"] and periodo and calendario.periodo_valido(ind.frecuencia, periodo):
        existente = db.scalar(select(Medicion).where(Medicion.indicador_id == ind.id, Medicion.periodo == periodo))
        base = existente.meta if existente and existente.meta is not None else metas.del_periodo(db, ind.id, periodo)
        r["vs_meta"] = meta.comparar(r["resultado"], base, ind.sentido)
    return r


# ---------------------------------------------------------------- envío de una carga
def _exigir_periodo_cargable(ind: Indicador, periodo: str) -> None:
    if not calendario.periodo_valido(ind.frecuencia, periodo) or calendario.es_futuro(ind.frecuencia, periodo, calendario.hoy()):
        raise Invalido("Período no válido para la frecuencia del indicador.")


def _copiar_foto_del_indicador(m: Medicion, ind: Indicador) -> None:
    """La medición conserva el nivel óptimo, el semáforo y la fórmula vigentes al cargar: editar la ficha no cambia el pasado."""
    m.nivel_optimo, m.limite, m.sentido = ind.nivel_optimo, ind.limite, ind.sentido
    m.nivel_optimo_tope, m.limite_tope = ind.nivel_optimo_tope, ind.limite_tope
    m.formula, m.constantes, m.decimales = ind.formula, ind.constantes or [], ind.precision


def cargar(db: Session, u: Usuario, datos) -> Medicion:
    """Registra (o reenvía, si fue devuelta) la carga de un indicador para un período."""
    ind = indicadores.obtener_visible(db, u, datos.indicador_id)
    acceso.exigir_cargable(u, ind)
    if not ind.activo:
        raise Conflicto("El indicador está archivado.")
    _exigir_periodo_cargable(ind, datos.periodo)
    anio = calendario.ejercicio_de(ind.frecuencia, datos.periodo)
    ejercicios.exigir_creado(db, anio)
    ejercicios.exigir_abierto(db, anio)
    r = evaluar_carga(ind, datos.valores)
    if not r["ok"]:
        raise Invalido(r["error"])
    analisis, plan = datos.analisis.strip(), datos.plan_mejora.strip()
    if r["requiere_analisis"] and (len(analisis) < MIN_TEXTO_ANALISIS or len(plan) < MIN_TEXTO_ANALISIS):
        raise Invalido("El indicador está fuera del nivel óptimo: el análisis de resultados y las correcciones / plan de "
                       "mejora son obligatorios (ISO 9001:2015, 9.1.3 y 10.2).")
    m = db.scalar(select(Medicion).where(Medicion.indicador_id == ind.id, Medicion.periodo == datos.periodo))
    if m and m.estado != "observado":
        raise Conflicto("Este período ya fue cargado y no puede modificarse.")
    reenvio = m is not None
    if m is None:
        base = metas.exigir_meta(db, ind, datos.periodo)   # sin meta no hay con qué comparar
        m = Medicion(indicador_id=ind.id, periodo=datos.periodo, version=1, meta=base)
        db.add(m)
    else:
        m.version += 1   # un reenvío conserva la meta con que se cargó por primera vez
    m.valores, m.resultado, m.semaforo, m.ejercicio = r["valores"], r["resultado"], r["semaforo"], anio
    _copiar_foto_del_indicador(m, ind)
    m.estado, m.analisis, m.plan_mejora = "enviado", analisis, plan
    m.cargado_por_id, m.cargado_en = u.id, ahora()
    m.revisado_por_id = m.revisado_en = None
    m.nota_revision = ""
    db.flush()
    auditoria.registrar(db, u, "REENVIO" if reenvio else "CARGA", "medicion", m.id,
                        {"periodo": m.periodo, "valores": m.valores, "resultado": m.resultado, "semaforo": m.semaforo,
                         "meta": m.meta, "analisis": analisis, "plan_mejora": plan, "version": m.version}, ind)
    db.commit()
    return m


# ---------------------------------------------------------------- consulta
def listar(db: Session, u: Usuario, *, estado=None, indicador_id=None, nodo_id=None, periodo=None,
           semaforo_=None, ejercicio=None, desde=0, limite=100) -> list[Medicion]:
    q = (select(Medicion).join(Indicador).order_by(Medicion.cargado_en.desc(), Medicion.id.desc())
         .offset(max(desde, 0)).limit(max(1, min(limite, 500))))
    return list(db.scalars(_filtrar(q, u, estado, indicador_id, nodo_id, periodo, semaforo_, ejercicio)))


def contar(db: Session, u: Usuario, *, estado=None, indicador_id=None, nodo_id=None, periodo=None, semaforo_=None, ejercicio=None) -> int:
    q = select(func.count(Medicion.id)).join(Indicador)
    return db.scalar(_filtrar(q, u, estado, indicador_id, nodo_id, periodo, semaforo_, ejercicio)) or 0


def resumen_por_ejercicio(db: Session, u: Usuario, estado: str) -> list[tuple[int, int]]:
    """[(ejercicio, cantidad)] de las cargas visibles en un estado, en una sola consulta."""
    q = acceso.indicadores_visibles(select(Medicion.ejercicio, func.count(Medicion.id)).join(Indicador).where(Medicion.estado == estado), u, True)
    return sorted(db.execute(q.group_by(Medicion.ejercicio)).all(), reverse=True)


def _filtrar(q, u, estado, indicador_id, nodo_id, periodo, semaforo_, ejercicio):
    q = acceso.indicadores_visibles(q, u, archivados=True)   # el historial de un indicador archivado sigue a la vista de su ámbito
    if nodo_id:
        q = q.where(acceso.en_nodo(nodo_id))
    for columna, valor in ((Medicion.estado, estado), (Medicion.indicador_id, indicador_id), (Medicion.periodo, periodo),
                           (Medicion.semaforo, semaforo_), (Medicion.ejercicio, ejercicio)):
        if valor:
            q = q.where(columna == valor)
    return q


# ---------------------------------------------------------------- bandeja: lo que a cada quien le toca aprobar
def bandeja(db: Session, u: Usuario, ejercicio: int | None = None) -> list[Medicion]:
    """Cargas enviadas que ESTA persona puede aprobar según la regla jerárquica (ver `acceso.aprobadores_de`): es el
    aprobador más cercano hacia arriba de quien cargó, o un rol de sistema. Nunca incluye las propias."""
    if not acceso.puede(u, "cargas.aprobar"):
        return []
    q = (select(Medicion).join(Indicador).where(Medicion.estado == "enviado", Medicion.cargado_por_id != u.id)
         .order_by(Medicion.cargado_en.desc(), Medicion.id.desc()))
    q = q.where(acceso.condicion_ambito(u) if not acceso.alcance_total(u) else Indicador.id.is_not(None))
    if ejercicio:
        q = q.where(Medicion.ejercicio == ejercicio)
    candidatas = list(db.scalars(q))
    if acceso.alcance_total(u) or not candidatas:
        return candidatas
    mapa = acceso.mapa_aprobadores(db)
    return [m for m in candidatas if u.id in acceso.aprobadores_de(m.indicador.nodo.ruta, m.cargado_por_id, mapa)]


def bandeja_por_ejercicio(db: Session, u: Usuario) -> list[tuple[int, int]]:
    cuenta: dict[int, int] = {}
    for m in bandeja(db, u):
        cuenta[m.ejercicio] = cuenta.get(m.ejercicio, 0) + 1
    return sorted(cuenta.items(), reverse=True)


# ---------------------------------------------------------------- revisión
def _obtener_visible(db: Session, u: Usuario, medicion_id: int) -> Medicion:
    """La carga, si la persona puede ver su indicador (si no, 404 como si no existiera)."""
    m = db.get(Medicion, medicion_id)
    if not m or not acceso.puede_ver(u, m.indicador):
        raise NoEncontrado("Carga no encontrada.")
    return m


def _obtener_modificable(db: Session, u: Usuario, medicion_id: int) -> Medicion:
    m = _obtener_visible(db, u, medicion_id)
    ejercicios.exigir_abierto(db, m.ejercicio)
    return m


def _exigir_aprobador(db: Session, u: Usuario, m: Medicion) -> None:
    if m.cargado_por_id == u.id:
        raise Prohibido("Segregación de funciones: una carga propia debe revisarla otra persona.")
    if u.id not in acceso.aprobadores_de(m.indicador.nodo.ruta, m.cargado_por_id, acceso.mapa_aprobadores(db)):
        raise Prohibido("Esta carga le corresponde aprobarla al superior más cercano de quien la cargó (o al Coordinador SGC).")


def revisar(db: Session, u: Usuario, medicion_id: int, accion: str, nota: str) -> Medicion:
    """Aprueba o devuelve una carga enviada. Lo hace el aprobador más cercano hacia arriba de quien cargó; el Coordinador
    SGC, siempre. Quien la cargó no puede revisarla (segregación de funciones)."""
    m = _obtener_modificable(db, u, medicion_id)
    _exigir_aprobador(db, u, m)
    if m.estado != "enviado":
        raise Conflicto("Solo se pueden revisar cargas en estado «enviado».")
    nota = nota.strip()
    if accion == "observar" and len(nota) < MIN_TEXTO_NOTA:
        raise Invalido("Indique el motivo de la devolución.")
    m.estado = "aprobado" if accion == "aprobar" else "observado"
    m.revisado_por_id, m.revisado_en, m.nota_revision = u.id, ahora(), nota
    auditoria.registrar(db, u, "APROBACION" if accion == "aprobar" else "OBSERVACION", "medicion", m.id,
                        {"periodo": m.periodo, "nota": nota}, m.indicador)
    db.commit()
    return m


def reabrir(db: Session, u: Usuario, medicion_id: int, nota: str) -> Medicion:
    """Devuelve a quien cargó una carga ya aprobada (p. ej. se detectó un error): queda como «devuelta».
    Rige la misma regla que para aprobar."""
    m = _obtener_modificable(db, u, medicion_id)
    _exigir_aprobador(db, u, m)
    if m.estado != "aprobado":
        raise Conflicto("Solo se pueden reabrir cargas aprobadas.")
    nota = nota.strip()
    if len(nota) < MIN_TEXTO_NOTA:
        raise Invalido("Indique el motivo de la reapertura.")
    m.estado, m.revisado_por_id, m.revisado_en, m.nota_revision = "observado", u.id, ahora(), nota
    auditoria.registrar(db, u, "REAPERTURA", "medicion", m.id, {"periodo": m.periodo, "nota": nota}, m.indicador)
    db.commit()
    return m


def agregar_nota(db: Session, u: Usuario, medicion_id: int, texto: str) -> Medicion:
    m = _obtener_modificable(db, u, medicion_id)
    nota = NotaAuditoria(medicion_id=m.id, usuario_id=u.id, texto=texto.strip(), fecha=ahora())
    db.add(nota)
    db.flush()
    auditoria.registrar(db, u, "NOTA_AUDITORIA", "medicion", m.id, {"periodo": m.periodo, "texto": nota.texto}, m.indicador)
    db.commit()
    db.refresh(m)
    return m
