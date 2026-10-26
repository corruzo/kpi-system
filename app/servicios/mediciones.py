"""Cargas de indicadores: cálculo, envío, revisión del gerente/auditor, reapertura y notas de auditoría."""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..dominio import calendario, formulas, semaforo
from ..errores import Conflicto, Invalido, NoEncontrado, Prohibido
from ..models import Indicador, Medicion, NotaAuditoria, Usuario, ahora
from . import auditoria, ejercicios, indicadores

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
    color = semaforo.clasificar(resultado, ind.meta, ind.limite, ind.sentido, ind.meta_tope, ind.limite_tope)
    return {"ok": True, "resultado": resultado, "semaforo": color, "requiere_analisis": color != "verde", "valores": finales}


def calcular(db: Session, u: Usuario, indicador_id: int, valores: dict) -> dict:
    return evaluar_carga(indicadores.obtener_visible(db, u, indicador_id), valores)


# ---------------------------------------------------------------- envío de una carga
def _exigir_periodo_cargable(ind: Indicador, periodo: str) -> None:
    if not calendario.periodo_valido(ind.frecuencia, periodo) or calendario.es_futuro(ind.frecuencia, periodo, date.today()):
        raise Invalido("Período no válido para la frecuencia del indicador.")


def _copiar_foto_del_indicador(m: Medicion, ind: Indicador) -> None:
    """La medición conserva la meta, el semáforo y la fórmula vigentes al cargar: editar la ficha no cambia el pasado."""
    m.meta, m.limite, m.sentido = ind.meta, ind.limite, ind.sentido
    m.meta_tope, m.limite_tope = ind.meta_tope, ind.limite_tope
    m.formula, m.constantes, m.decimales = ind.formula, ind.constantes or [], ind.precision


def cargar(db: Session, u: Usuario, datos) -> Medicion:
    """Registra (o reenvía, si fue devuelta) la carga de un indicador para un período."""
    ind = indicadores.obtener_visible(db, u, datos.indicador_id)
    if not ind.activo:
        raise Conflicto("El indicador está archivado.")
    _exigir_periodo_cargable(ind, datos.periodo)
    anio = calendario.ejercicio_de(ind.frecuencia, datos.periodo)
    ejercicios.exigir_abierto(db, anio)
    r = evaluar_carga(ind, datos.valores)
    if not r["ok"]:
        raise Invalido(r["error"])
    analisis, plan = datos.analisis.strip(), datos.plan_mejora.strip()
    if r["requiere_analisis"] and (len(analisis) < MIN_TEXTO_ANALISIS or len(plan) < MIN_TEXTO_ANALISIS):
        raise Invalido("El indicador está fuera de meta: el análisis de resultados y las correcciones / plan de "
                       "mejora son obligatorios (ISO 9001:2015, 9.1.3 y 10.2).")
    m = db.scalar(select(Medicion).where(Medicion.indicador_id == ind.id, Medicion.periodo == datos.periodo))
    if m and m.estado != "observado":
        raise Conflicto("Este período ya fue cargado y no puede modificarse.")
    reenvio = m is not None
    if m is None:
        m = Medicion(indicador_id=ind.id, periodo=datos.periodo, version=1)
        db.add(m)
    else:
        m.version += 1
    m.valores, m.resultado, m.semaforo, m.ejercicio = r["valores"], r["resultado"], r["semaforo"], anio
    _copiar_foto_del_indicador(m, ind)
    m.estado, m.analisis, m.plan_mejora = "enviado", analisis, plan
    m.cargado_por_id, m.cargado_en = u.id, ahora()
    m.revisado_por_id = m.revisado_en = None
    m.nota_revision = ""
    db.flush()
    auditoria.registrar(db, u, "REENVIO" if reenvio else "CARGA", "medicion", m.id,
                        {"periodo": m.periodo, "valores": m.valores, "resultado": m.resultado, "semaforo": m.semaforo,
                         "analisis": analisis, "plan_mejora": plan, "version": m.version}, ind)
    db.commit()
    return m


# ---------------------------------------------------------------- consulta
def listar(db: Session, u: Usuario, *, estado=None, indicador_id=None, area_id=None, periodo=None,
           semaforo_=None, ejercicio=None, desde=0, limite=100) -> list[Medicion]:
    q = (select(Medicion).join(Indicador).order_by(Medicion.cargado_en.desc(), Medicion.id.desc())
         .offset(max(desde, 0)).limit(min(limite, 500)))
    if u.rol == "jefe":
        q = q.where(Indicador.area_id == u.area_id)
    elif area_id:
        q = q.where(Indicador.area_id == area_id)
    for columna, valor in ((Medicion.estado, estado), (Medicion.indicador_id, indicador_id), (Medicion.periodo, periodo),
                           (Medicion.semaforo, semaforo_), (Medicion.ejercicio, ejercicio)):
        if valor:
            q = q.where(columna == valor)
    return list(db.scalars(q))


# ---------------------------------------------------------------- revisión
def _obtener_modificable(db: Session, medicion_id: int) -> Medicion:
    m = db.get(Medicion, medicion_id)
    if not m:
        raise NoEncontrado("Carga no encontrada.")
    ejercicios.exigir_abierto(db, m.ejercicio)
    return m


def revisar(db: Session, u: Usuario, medicion_id: int, accion: str, nota: str) -> Medicion:
    """Aprueba o devuelve una carga enviada. Quien la cargó no puede revisarla (segregación de funciones)."""
    m = _obtener_modificable(db, medicion_id)
    if m.cargado_por_id == u.id:
        raise Prohibido("Segregación de funciones: una carga propia debe revisarla otra persona.")
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
    """Devuelve al jefe una carga ya aprobada (p. ej. se detectó un error): queda como «devuelta»."""
    m = _obtener_modificable(db, medicion_id)
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
    m = _obtener_modificable(db, medicion_id)
    nota = NotaAuditoria(medicion_id=m.id, usuario_id=u.id, texto=texto.strip(), fecha=ahora())
    db.add(nota)
    db.flush()
    auditoria.registrar(db, u, "NOTA_AUDITORIA", "medicion", m.id, {"periodo": m.periodo, "texto": nota.texto}, m.indicador)
    db.commit()
    db.refresh(m)
    return m
