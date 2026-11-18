"""Ejercicios fiscales: estado, foto de resultados, verificación, cierre y reapertura.

Un ejercicio sin fila en la tabla `ejercicios` está abierto. Cerrarlo lo vuelve de solo lectura y guarda
una foto de sus resultados; reabrirlo exige un motivo. Todo queda en la bitácora.
"""
from collections import defaultdict
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..dominio import calendario
from ..errores import Conflicto, Invalido
from ..models import Ejercicio, Indicador, Medicion, PeriodoJustificado, Usuario, ahora
from . import acceso, auditoria
from .periodos import justificados_de


# ---------------------------------------------------------------- reglas básicas
def exigir_abierto(db: Session, anio: int | None) -> None:
    """Un ejercicio cerrado es de solo lectura: lanza Conflicto si se intenta modificarlo."""
    fila = db.get(Ejercicio, anio) if anio is not None else None
    if fila and fila.estado == "cerrado":
        raise Conflicto(f"El ejercicio fiscal {calendario.etiqueta_ejercicio(anio)} está cerrado: no admite cambios. "
                        "Quien tenga permiso puede reabrirlo desde «Cierre de años».")


def creado(db: Session, anio: int | None) -> bool:
    """¿Existe el período fiscal (paso 1)? Sin crearlo no se fijan metas ni se carga."""
    return anio is not None and db.get(Ejercicio, anio) is not None


def exigir_creado(db: Session, anio: int) -> None:
    if not creado(db, anio):
        raise Conflicto(f"El período fiscal {calendario.etiqueta_ejercicio(anio)} todavía no ha sido creado. "
                        "Debe crearse en «Período y metas» antes de fijar metas o cargar datos.")


def crear(db: Session, usuario: Usuario, anio: int, nota: str = "") -> Ejercicio:
    """Paso 1 del flujo anual: crea (abre) un período fiscal."""
    if not 2000 <= anio <= 2100:
        raise Invalido("Año no válido (entre 2000 y 2100).")
    if creado(db, anio):
        raise Conflicto(f"El período fiscal {calendario.etiqueta_ejercicio(anio)} ya existe.")
    fila = Ejercicio(anio=anio, estado="abierto", creado_por_id=usuario.id, creado_en=ahora(), nota=nota.strip())
    db.add(fila)
    auditoria.registrar(db, usuario, "EJERCICIO_CREADO", "ejercicio", anio,
                        {"ejercicio": calendario.etiqueta_ejercicio(anio), "nota": nota.strip()})
    db.commit()
    return fila


def asegurar_creado(db: Session, usuario: Usuario, anio: int) -> None:
    """Crea el período si falta (lo usa la importación de históricos, que ya trae datos de años anteriores)."""
    if not creado(db, anio):
        db.add(Ejercicio(anio=anio, estado="abierto", creado_por_id=usuario.id, creado_en=ahora(),
                         nota="Creado al importar datos históricos."))
        db.flush()


def anios_cerrados(db: Session) -> set[int]:
    return {e.anio for e in db.scalars(select(Ejercicio)) if e.estado == "cerrado"}


_SIN_DATO = object()   # «no se pasó la fila»: distinto de None, que significa «el ejercicio no tiene fila»


def estado(db: Session, anio: int, hoy: date, fila=_SIN_DATO) -> str:
    """cerrado | vigente | futuro | terminado (ya pasó su último día y sigue abierto)."""
    if fila is _SIN_DATO:
        fila = db.get(Ejercicio, anio)
    if fila and fila.estado == "cerrado":
        return "cerrado"
    ini, fin = calendario.limites(anio)
    return "vigente" if ini <= hoy <= fin else ("futuro" if ini > hoy else "terminado")


def anios_conocidos(db: Session, hoy: date, filas: dict[int, Ejercicio] | None = None) -> list[int]:
    """Ejercicios con datos, con fila propia, el vigente y el siguiente; el más reciente primero."""
    anios = {a for a in db.scalars(select(Medicion.ejercicio).distinct()) if a}
    anios |= set(filas) if filas is not None else set(db.scalars(select(Ejercicio.anio)))
    vigente = calendario.ejercicio_de_fecha(hoy)
    anios |= {vigente, vigente + 1}   # el siguiente se ofrece para crearlo con antelación
    return sorted(anios, reverse=True)


def recalcular(db: Session) -> int:
    """Reasigna a cada medición el ejercicio de su período (tras cambiar el mes de inicio del ejercicio fiscal)."""
    cambios = 0
    for m in db.scalars(select(Medicion)):
        anio = calendario.ejercicio_de(m.indicador.frecuencia, m.periodo)
        if m.ejercicio != anio:
            m.ejercicio, cambios = anio, cambios + 1
    db.commit()
    return cambios


# ---------------------------------------------------------------- foto de resultados
def _resumen_vacio() -> dict:
    return {"total": 0, "verde": 0, "amarillo": 0, "rojo": 0, "sin_datos": 0, "por_aprobar": 0, "devueltas": 0,
            "cargas": 0, "esperados": 0, "faltantes": 0}


def _periodos_esperados(ind: Indicador, anio: int, hoy: date, tiene_cargas: bool, justificados=frozenset()) -> list[str]:
    """Períodos ya cerrados que debieron cargarse. No se exigen: los anteriores a la creación de un indicador nuevo, los que
    empiezan después de que se archivó y los justificados (parada de planta, no aplica…)."""
    if ind.frecuencia == "eventual":
        return []
    esperados = [p for p in calendario.periodos_del_ejercicio(ind.frecuencia, anio)
                 if calendario.rango(ind.frecuencia, p)[1] < hoy]
    if not tiene_cargas and ind.creado_en:
        esperados = [p for p in esperados if calendario.rango(ind.frecuencia, p)[1] >= ind.creado_en.date()]
    if not ind.activo and ind.archivado_en:
        esperados = [p for p in esperados if calendario.rango(ind.frecuencia, p)[0] <= ind.archivado_en.date()]
    return [p for p in esperados if p not in justificados]


def _fila_indicador(ind: Indicador, mediciones: list[Medicion], anio: int, hoy: date, justificados=frozenset()) -> dict:
    ms = sorted(mediciones, key=lambda m: m.periodo)
    validas = [m for m in ms if m.estado in ("enviado", "aprobado")]
    ultimo = validas[-1] if validas else None
    cubiertos = {m.periodo for m in validas}
    esperados = _periodos_esperados(ind, anio, hoy, bool(ms), justificados)
    faltan = [p for p in esperados if p not in cubiertos]
    celdas = [None] * 12   # mapa de calor: un semáforo por mes del ejercicio
    for m in ms:
        if m.estado != "observado":
            celdas[calendario.indice_de_mes(ind.frecuencia, m.periodo)] = {
                "semaforo": m.semaforo, "resultado": m.resultado, "periodo": m.periodo,
                "etiqueta": calendario.etiqueta(ind.frecuencia, m.periodo)}
    tendencia = None
    if len(validas) >= 2:
        delta = round(validas[-1].resultado - validas[-2].resultado, 4)
        mejora = (delta > 0) if ind.sentido == "mayor" else (delta < 0)
        tendencia = {"delta": delta, "mejora": mejora if delta else None}
    return {"indicador": ind, "ultimo": ultimo, "validas": validas, "celdas": celdas, "faltantes": faltan,
            "esperados": len(esperados), "tendencia": tendencia,
            "por_aprobar": sum(m.estado == "enviado" for m in ms), "devueltas": sum(m.estado == "observado" for m in ms)}


def foto(db: Session, anio: int, nodo_id: int | None = None, hoy: date | None = None, u: Usuario | None = None) -> dict:
    """Estado de los indicadores en el ejercicio: {resumen, por_area, filas}. Con `u`, solo los que esa persona puede ver
    (su ámbito y sus asignados); sin `u`, todos (foto del cierre). `nodo_id` abarca el subárbol del nodo."""
    hoy = hoy or calendario.hoy()
    q = select(Indicador).order_by(Indicador.codigo)
    if u is not None:
        q = acceso.indicadores_visibles(q, u, archivados=True)
    if nodo_id:
        q = q.where(acceso.en_nodo(nodo_id))
    inds = list(db.scalars(q))
    por_indicador = defaultdict(list)
    q_med = select(Medicion).where(Medicion.ejercicio == anio)
    if u is not None and not acceso.es_global(u) or nodo_id:
        q_med = q_med.where(Medicion.indicador_id.in_([i.id for i in inds]))
    for m in db.scalars(q_med):
        por_indicador[m.indicador_id].append(m)
    justificados = justificados_de(db, [i.id for i in inds]) if inds else {}
    resumen, por_area, filas = _resumen_vacio(), {}, []
    for ind in inds:
        ms = por_indicador.get(ind.id, [])
        if not ind.activo and not ms:
            continue   # un indicador archivado solo cuenta si tiene datos en el ejercicio
        fila = _fila_indicador(ind, ms, anio, hoy, justificados.get(ind.id, {}).keys())
        color = fila["ultimo"].semaforo if fila["ultimo"] else "sin_datos"
        area = por_area.setdefault(ind.nodo.nombre, {"area": ind.nodo.nombre, **dict.fromkeys(("total", "verde", "amarillo", "rojo", "sin_datos", "esperados", "faltantes"), 0)})
        for acumulado in (area, resumen):
            acumulado["total"] += 1
            acumulado[color] += 1
            acumulado["esperados"] += fila["esperados"]
            acumulado["faltantes"] += len(fila["faltantes"])
        resumen["por_aprobar"] += fila["por_aprobar"]
        resumen["devueltas"] += fila["devueltas"]
        resumen["cargas"] += len(fila["validas"])
        filas.append(fila)
    for a in por_area.values():
        a["cumplimiento"] = round(100 * a["verde"] / a["total"], 1) if a["total"] else 0
    resumen["cumplimiento"] = round(100 * resumen["verde"] / resumen["total"], 1) if resumen["total"] else 0
    resumen["carga_al_dia"] = round(100 * (1 - resumen["faltantes"] / resumen["esperados"]), 1) if resumen["esperados"] else 100.0
    return {"resumen": resumen, "por_area": list(por_area.values()), "filas": filas}


# ---------------------------------------------------------------- listado, verificación, cierre y reapertura
def descripcion(db: Session, anio: int, hoy: date, filas: dict[int, Ejercicio] | None = None) -> dict:
    """Datos generales del ejercicio: fechas, estado y, si está cerrado, quién y cuándo. Con `filas` (todas las filas por año)
    no consulta la base por cada ejercicio."""
    ini, fin = calendario.limites(anio)
    fila = filas.get(anio) if filas is not None else db.get(Ejercicio, anio)
    cerrado = bool(fila and fila.estado == "cerrado")
    return {"anio": anio, "etiqueta": calendario.etiqueta_ejercicio(anio), "desde": ini, "hasta": fin,
            "estado": estado(db, anio, hoy, fila), "fila": fila, "creado": fila is not None,
            "cerrado_por": fila.cerrado_por.nombre if cerrado and fila.cerrado_por else None}


def resultados(db: Session, anio: int, hoy: date, u: Usuario) -> dict:
    """{resumen, por_area} del ejercicio, de lo que la persona puede ver. Quien ve toda la empresa recibe la foto
    guardada al cerrar; los demás, siempre el cálculo de su propio alcance."""
    fila = db.get(Ejercicio, anio)
    guardada = fila.resumen if fila and fila.estado == "cerrado" and fila.resumen and acceso.es_global(u) else None
    f = guardada or foto(db, anio, None, hoy, u)
    return {"resumen": f["resumen"], "por_area": f["por_area"]}


def verificar(db: Session, anio: int, hoy: date | None = None) -> dict:
    """Lista de comprobación previa al cierre: qué falta revisar, corregir o cargar."""
    hoy = hoy or calendario.hoy()
    desc = descripcion(db, anio, hoy)
    f = foto(db, anio, None, hoy)
    pendientes = [{"codigo": m.indicador.codigo, "indicador": m.indicador.nombre, "area": m.indicador.nodo.nombre,
                   "periodo": calendario.etiqueta(m.indicador.frecuencia, m.periodo), "estado": m.estado}
                  for m in db.scalars(select(Medicion).where(Medicion.ejercicio == anio,
                                                              Medicion.estado.in_(("enviado", "observado"))))]
    faltantes = [{"indicador_id": x["indicador"].id, "codigo": x["indicador"].codigo, "indicador": x["indicador"].nombre,
                  "area": x["indicador"].nodo.nombre,
                  "periodos": [calendario.etiqueta(x["indicador"].frecuencia, p) for p in x["faltantes"]],
                  "items": [{"periodo": p, "etiqueta": calendario.etiqueta(x["indicador"].frecuencia, p)} for p in x["faltantes"]]}
                 for x in f["filas"] if x["faltantes"]]
    justificados = [{"indicador_id": j.indicador_id, "codigo": ind.codigo, "indicador": ind.nombre, "periodo": j.periodo,
                     "etiqueta": calendario.etiqueta(ind.frecuencia, j.periodo), "tipo": j.tipo, "motivo": j.motivo,
                     "por": j.por.nombre, "en": j.en}
                    for j, ind in db.execute(select(PeriodoJustificado, Indicador).join(Indicador, Indicador.id == PeriodoJustificado.indicador_id)
                                             .where(PeriodoJustificado.ejercicio == anio).order_by(Indicador.codigo, PeriodoJustificado.periodo))]
    terminado = desc["hasta"] < hoy
    total_faltantes = sum(len(x["periodos"]) for x in faltantes)
    # sin forzado posible: un ejercicio solo se cierra con todos sus períodos cargados y aprobados, o justificados
    return {"descripcion": desc, "terminado": terminado, "pendientes": pendientes, "faltantes": faltantes, "justificados": justificados,
            "total_faltantes": total_faltantes, "foto": f,
            "puede_cerrar": terminado and not pendientes and not total_faltantes and desc["estado"] != "cerrado"}


def cerrar(db: Session, usuario: Usuario, anio: int, nota: str, hoy: date | None = None) -> None:
    hoy = hoy or calendario.hoy()
    exigir_creado(db, anio)
    v = verificar(db, anio, hoy)
    if v["descripcion"]["estado"] == "cerrado":
        raise Conflicto("El ejercicio ya está cerrado.")
    if not v["terminado"]:
        raise Invalido("El ejercicio aún no ha terminado: solo puede cerrarse después de su último día.")
    if v["pendientes"]:
        raise Invalido(f"Hay {len(v['pendientes'])} carga(s) en revisión o devueltas: resuélvalas antes de cerrar.")
    if v["total_faltantes"]:
        raise Invalido(f"Faltan {v['total_faltantes']} período(s) por cargar: cárguelos y apruébelos, o justifíquelos "
                       "(parada de planta, no aplica) para poder cerrar el ejercicio.")
    f = v["foto"]
    instantanea = {"resumen": f["resumen"], "por_area": f["por_area"], "faltantes": v["total_faltantes"],
                   "indicadores": [{"codigo": x["indicador"].codigo, "nombre": x["indicador"].nombre,
                                    "area": x["indicador"].nodo.nombre,
                                    "ultimo": ({"etiqueta": calendario.etiqueta(x["indicador"].frecuencia, x["ultimo"].periodo),
                                                "resultado": x["ultimo"].resultado, "semaforo": x["ultimo"].semaforo}
                                               if x["ultimo"] else None)} for x in f["filas"]]}
    fila = db.get(Ejercicio, anio) or Ejercicio(anio=anio)
    fila.estado, fila.cerrado_por_id, fila.cerrado_en, fila.nota, fila.resumen = \
        "cerrado", usuario.id, ahora(), nota.strip(), instantanea
    db.add(fila)
    auditoria.registrar(db, usuario, "EJERCICIO_CERRADO", "ejercicio", anio,
                        {"ejercicio": calendario.etiqueta_ejercicio(anio), "nota": nota.strip(),
                         "faltantes": v["total_faltantes"], "cumplimiento": f["resumen"]["cumplimiento"]})
    db.commit()


def reabrir(db: Session, usuario: Usuario, anio: int, nota: str) -> None:
    fila = db.get(Ejercicio, anio)
    if not fila or fila.estado != "cerrado":
        raise Conflicto("El ejercicio no está cerrado.")
    fila.estado, fila.reabierto_por_id, fila.reabierto_en, fila.nota_reapertura = "abierto", usuario.id, ahora(), nota.strip()
    auditoria.registrar(db, usuario, "EJERCICIO_REABIERTO", "ejercicio", anio,
                        {"ejercicio": calendario.etiqueta_ejercicio(anio), "nota": nota.strip()})
    db.commit()
