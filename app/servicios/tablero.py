"""Panel de control: todo lo que el sistema sabe, visto por rango de fechas y por la granularidad que se elija.

Un solo cálculo (`construir`) devuelve, para un rango de meses y filtros (área, frecuencia, seguimiento, indicador…):
  · indicadores clave y su comparación con el rango anterior de igual duración;
  · serie por período (mes, bimestre, trimestre, cuatrimestre, semestre o año fiscal): semáforos, cumplimiento de la meta,
    estado de las cargas y carga al día;
  · estado actual (última medición de cada indicador), comparativo por área / gerencia / seguimiento / frecuencia / proceso;
  · detalle por indicador (mapa de calor, tendencia, desviación contra meta), responsables (puntualidad) y atención requerida.
Los períodos de los indicadores (mensual, trimestral…) se asignan al período de la vista según el mes en que CIERRAN.
"""
import re
from datetime import date, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..dominio import calendario
from ..dominio.meta import comparar
from ..errores import Invalido
from ..models import Indicador, Medicion

AGRUPACIONES = {"mes": "mensual", "bimestre": "bimestral", "trimestre": "trimestral", "cuatrimestre": "cuatrimestral",
                "semestre": "semestral", "anio": "anual"}
DIMENSIONES = {
    "area": lambda i: i.area.nombre,
    "gerencia": lambda i: i.gerencia or "Sin gerencia",
    "seguimiento": lambda i: {"proceso": "Desempeño de proceso", "objetivo": "Objetivo organizacional",
                              "proveedor": "Proveedor externo"}.get(i.seguimiento or "proceso", "Desempeño de proceso"),
    "frecuencia": lambda i: i.frecuencia.capitalize(),
    "proceso": lambda i: i.ref_nombre or "Sin proceso u objetivo",
}
PLAZO_DIAS = 10        # una carga es «a tiempo» si se registra dentro de los 10 días siguientes al cierre de su período
PREFIJO_IMPORTADA = "Importado desde Excel"   # las cargas históricas importadas no cuentan en puntualidad ni en tiempos de aprobación
MAX_MESES = 60
_MES_RX = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")
VALIDAS = ("enviado", "aprobado")


# ---------------------------------------------------------------- fechas y períodos de la vista
def _mes(texto: str, nombre: str) -> date:
    m = _MES_RX.match(texto or "")
    if not m or not 2000 <= int(m.group(1)) <= 2100:
        raise Invalido(f"«{nombre}» debe ser un mes válido (AAAA-MM).")
    return date(int(m.group(1)), int(m.group(2)), 1)


def _ultimo_dia(d: date) -> date:
    return calendario.suma_meses(d, 1) - timedelta(days=1)


def _meses_entre(ini: date, fin: date) -> list[date]:
    out, d = [], ini
    while d <= fin:
        out.append(d)
        d = calendario.suma_meses(d, 1)
    return out


def _cubeta(agrupar: str, d: date) -> tuple[str, str]:
    """(código, etiqueta) del período de la vista que contiene la fecha."""
    freq = AGRUPACIONES[agrupar]
    codigo = calendario.codigo(freq, d)
    if agrupar == "mes":
        return codigo, f"{calendario.MES3[d.month - 1]} {d.year % 100:02d}"
    return codigo, calendario.etiqueta(freq, codigo)


def _pct(a: int, b: int) -> float | None:
    return round(100 * a / b, 1) if b else None


def _prom(valores: list[float]) -> float | None:
    return round(sum(valores) / len(valores), 1) if valores else None


# ---------------------------------------------------------------- cálculo
def construir(db: Session, *, desde: str, hasta: str, agrupar: str = "mes", area_id: int | None = None,
              frecuencia: str | None = None, seguimiento: str | None = None, indicador_id: int | None = None,
              solo_aprobadas: bool = False, dimension: str = "area", hoy: date | None = None, _anterior: bool = False) -> dict:
    hoy = hoy or calendario.hoy()
    ini, fin = _mes(desde, "desde"), _ultimo_dia(_mes(hasta, "hasta"))
    if agrupar not in AGRUPACIONES:
        raise Invalido("Agrupación no válida.")
    if dimension not in DIMENSIONES:
        raise Invalido("Dimensión no válida.")
    if fin < ini:
        raise Invalido("La fecha «hasta» no puede ser anterior a «desde».")
    meses = _meses_entre(ini, fin)
    if len(meses) > MAX_MESES:
        raise Invalido(f"El rango no puede superar {MAX_MESES} meses.")

    # --- indicadores en alcance
    q = select(Indicador).order_by(Indicador.codigo)
    for columna, valor in ((Indicador.area_id, area_id), (Indicador.frecuencia, frecuencia),
                           (Indicador.seguimiento, seguimiento), (Indicador.id, indicador_id)):
        if valor:
            q = q.where(columna == valor)
    inds = {i.id: i for i in db.scalars(q)}

    # --- cubetas (períodos de la vista)
    cubetas: dict[str, dict] = {}
    for m in meses:
        codigo, etiqueta = _cubeta(agrupar, m)
        cubetas.setdefault(codigo, {"codigo": codigo, "etiqueta": etiqueta, "verde": 0, "amarillo": 0, "rojo": 0, "con_meta": 0,
                                    "cumplen": 0, "aprobadas": 0, "en_revision": 0, "devueltas": 0, "esperados": 0, "cubiertos": 0})

    # --- mediciones del rango (todas las cargas; las «válidas» alimentan semáforos y meta)
    anio_ini, anio_fin = calendario.ejercicio_de_fecha(ini), calendario.ejercicio_de_fecha(fin)
    meds = []
    if inds:
        for m in db.scalars(select(Medicion).where(Medicion.indicador_id.in_(list(inds)),
                                                   or_(Medicion.ejercicio.is_(None), Medicion.ejercicio.between(anio_ini - 1, anio_fin + 1)))):
            ind = inds[m.indicador_id]
            if not calendario.periodo_valido(ind.frecuencia, m.periodo):
                continue
            p_ini, p_fin = calendario.rango(ind.frecuencia, m.periodo)
            if ini <= p_fin <= fin:
                meds.append((m, ind, p_ini, p_fin))
    meds.sort(key=lambda t: (t[3], t[1].codigo))

    datos: dict[int, dict] = {}     # por indicador

    def ficha(ind: Indicador) -> dict:
        return datos.setdefault(ind.id, {
            "ind": ind, "validas": [], "verde": 0, "amarillo": 0, "rojo": 0, "con_meta": 0, "cumplen": 0, "porcentajes": [],
            "devueltas": 0, "esperados": 0, "cubiertos": 0, "celdas": {}, "serie": []})

    responsables: dict[int, dict] = {}
    horas_aprobacion: list[float] = []
    for m, ind, _, p_fin in meds:
        codigo, _ = _cubeta(agrupar, p_fin)
        cub, d = cubetas[codigo], ficha(ind)
        cub[{"aprobado": "aprobadas", "enviado": "en_revision", "observado": "devueltas"}[m.estado]] += 1
        if m.estado == "observado":
            d["devueltas"] += 1
        if not (m.nota_revision or "").startswith(PREFIJO_IMPORTADA):
            resp = responsables.setdefault(m.cargado_por_id, {"nombre": m.cargado_por.nombre.split(" (")[0], "area": ind.area.nombre,
                                                               "cargas": 0, "a_tiempo": 0, "dias_retraso": 0, "devueltas": 0})
            resp["cargas"] += 1
            retraso = max(0, (m.cargado_en.date() - p_fin).days)
            resp["a_tiempo"] += retraso <= PLAZO_DIAS
            resp["dias_retraso"] += retraso
            resp["devueltas"] += m.estado == "observado"
            if m.estado == "aprobado" and m.revisado_en:
                horas_aprobacion.append((m.revisado_en - m.cargado_en).total_seconds() / 3600)
        if m.estado not in VALIDAS or (solo_aprobadas and m.estado != "aprobado"):
            continue
        d["validas"].append(m)
        for contador in (cub, d):
            contador[m.semaforo] += 1
        c = comparar(m.resultado, m.meta, m.sentido)
        if c:
            for contador in (cub, d):
                contador["con_meta"] += 1
                contador["cumplen"] += c["cumple"]
            if c["porcentaje"] is not None:
                d["porcentajes"].append(c["porcentaje"])
        d["celdas"][codigo] = {"semaforo": m.semaforo, "resultado": m.resultado, "etiqueta": calendario.etiqueta(ind.frecuencia, m.periodo)}
        d["serie"].append({"periodo": m.periodo, "etiqueta": calendario.etiqueta(ind.frecuencia, m.periodo), "resultado": m.resultado,
                           "meta": m.meta, "nivel_optimo": m.nivel_optimo, "limite": m.limite, "semaforo": m.semaforo})
    # --- carga al día: períodos ya cerrados que debieron cargarse
    for ind in inds.values():
        if ind.frecuencia == "eventual":
            continue
        cubiertos = {m.periodo for m, i, _, _ in meds if i.id == ind.id and m.estado in VALIDAS}
        tiene = ind.id in datos and bool(datos[ind.id]["validas"] or any(i.id == ind.id for _, i, _, _ in meds))
        for anio in range(anio_ini - 1, anio_fin + 2):
            for p in calendario.periodos_del_ejercicio(ind.frecuencia, anio):
                _, p_fin = calendario.rango(ind.frecuencia, p)
                if not (ini <= p_fin <= fin) or p_fin >= hoy or (not tiene and ind.creado_en and p_fin < ind.creado_en.date()):
                    continue
                d, (codigo, _) = ficha(ind), _cubeta(agrupar, p_fin)
                for contador in (d, cubetas[codigo]):
                    contador["esperados"] += 1
                    contador["cubiertos"] += p in cubiertos

    # un indicador archivado sin datos en el rango no cuenta
    datos = {k: v for k, v in datos.items() if v["ind"].activo or v["validas"]}
    for ind in inds.values():
        if ind.activo and ind.id not in datos:
            ficha(ind)

    # ---------------------------------------------------------------- resultados
    lista = []
    for d in datos.values():
        ind, v = d["ind"], d["validas"]
        ultimo = v[-1] if v else None
        penultimo = v[-2] if len(v) > 1 else None
        tendencia = None
        if ultimo and penultimo:
            delta = round(ultimo.resultado - penultimo.resultado, 4)
            tendencia = {"delta": delta, "mejora": ((delta > 0) if ind.sentido == "mayor" else (delta < 0)) if delta else None}
        total = d["verde"] + d["amarillo"] + d["rojo"]
        lista.append({
            "id": ind.id, "codigo": ind.codigo, "nombre": ind.nombre, "area": ind.area.nombre, "unidad": ind.unidad,
            "decimales": ind.precision, "frecuencia": ind.frecuencia, "sentido": ind.sentido, "gerencia": ind.gerencia or "",
            "n": total, "verde": d["verde"], "amarillo": d["amarillo"], "rojo": d["rojo"], "pct_verde": _pct(d["verde"], total),
            "con_meta": d["con_meta"], "cumplen_meta": d["cumplen"], "pct_meta": _pct(d["cumplen"], d["con_meta"]),
            "real_vs_meta": _prom(d["porcentajes"]), "faltantes": d["esperados"] - d["cubiertos"], "esperados": d["esperados"],
            "devueltas": d["devueltas"], "tendencia": tendencia,
            "ultimo": ({"etiqueta": calendario.etiqueta(ind.frecuencia, ultimo.periodo), "resultado": ultimo.resultado,
                        "semaforo": ultimo.semaforo, "meta": ultimo.meta} if ultimo else None),
            "celdas": d["celdas"], "serie": d["serie"]})

    resumen_actual = {"verde": 0, "amarillo": 0, "rojo": 0, "sin_datos": 0}
    for i in lista:
        resumen_actual[i["ultimo"]["semaforo"] if i["ultimo"] else "sin_datos"] += 1

    def sumar(campo):
        return sum(c[campo] for c in cubetas.values())
    total_val, con_meta = sumar("verde") + sumar("amarillo") + sumar("rojo"), sumar("con_meta")
    esperados, cubiertos = sumar("esperados"), sumar("cubiertos")
    cargas = sumar("aprobadas") + sumar("en_revision") + sumar("devueltas")
    a_tiempo = sum(r["a_tiempo"] for r in responsables.values())
    cargas_propias = sum(r["cargas"] for r in responsables.values())      # sin las importadas
    porcentajes = [p for d in datos.values() for p in d["porcentajes"]]
    kpis = {
        "indicadores": len(lista), "mediciones": total_val, "cargas": cargas,
        "verde": sumar("verde"), "amarillo": sumar("amarillo"), "rojo": sumar("rojo"),
        "cumplimiento": _pct(sumar("verde"), total_val), "con_meta": con_meta, "cumplen_meta": sumar("cumplen"),
        "cumplimiento_meta": _pct(sumar("cumplen"), con_meta), "real_vs_meta": _prom(porcentajes),
        "esperados": esperados, "faltantes": esperados - cubiertos,
        "carga_al_dia": _pct(cubiertos, esperados) if esperados else None,
        "a_tiempo": _pct(a_tiempo, cargas_propias),
        "dias_retraso": round(sum(r["dias_retraso"] for r in responsables.values()) / cargas_propias, 1) if cargas_propias else None,
        "horas_aprobacion": _prom(horas_aprobacion), "por_aprobar": sumar("en_revision"), "devueltas": sumar("devueltas"),
    }
    if _anterior:
        return {"kpis": kpis}

    # --- serie por período de la vista
    serie = []
    for c in cubetas.values():
        total = c["verde"] + c["amarillo"] + c["rojo"]
        serie.append({**c, "total": total, "cumplimiento": _pct(c["verde"], total), "cumplimiento_meta": _pct(c["cumplen"], c["con_meta"]),
                      "faltantes": c["esperados"] - c["cubiertos"], "carga_al_dia": _pct(c["cubiertos"], c["esperados"])})

    # --- comparativo por dimensión
    grupos: dict[str, dict] = {}
    for i in lista:
        g = grupos.setdefault(DIMENSIONES[dimension](datos[i["id"]]["ind"]),
                              {"nombre": "", "indicadores": 0, "verde": 0, "amarillo": 0, "rojo": 0, "con_meta": 0, "cumplen": 0, "faltantes": 0})
        g["indicadores"] += 1
        for k, kk in (("verde", "verde"), ("amarillo", "amarillo"), ("rojo", "rojo"), ("con_meta", "con_meta"),
                      ("cumplen", "cumplen_meta"), ("faltantes", "faltantes")):
            g[k] += i[kk]
    por_dimension = []
    for nombre, g in sorted(grupos.items()):
        total = g["verde"] + g["amarillo"] + g["rojo"]
        por_dimension.append({**g, "nombre": nombre, "total": total, "cumplimiento": _pct(g["verde"], total),
                              "cumplimiento_meta": _pct(g["cumplen"], g["con_meta"])})

    # --- atención requerida
    atencion = []
    for i in lista:
        base = {k: i[k] for k in ("id", "codigo", "nombre", "area", "unidad", "decimales")}
        u = i["ultimo"]
        if u and u["semaforo"] == "rojo":
            atencion.append({**base, "nivel": 3, "motivo": f"Crítico en {u['etiqueta']}", "semaforo": "rojo", "resultado": u["resultado"]})
        elif u and u["semaforo"] == "amarillo" and i["tendencia"] and i["tendencia"]["mejora"] is False:
            atencion.append({**base, "nivel": 2, "motivo": f"En alerta y empeorando ({u['etiqueta']})", "semaforo": "amarillo", "resultado": u["resultado"]})
        if i["faltantes"] > 0:
            atencion.append({**base, "nivel": 1, "semaforo": None, "resultado": None, "motivo": f"{i['faltantes']} período(s) sin cargar"})
        if i["devueltas"]:
            atencion.append({**base, "nivel": 1, "semaforo": None, "resultado": None, "motivo": f"{i['devueltas']} carga(s) devuelta(s) sin corregir"})
    atencion.sort(key=lambda a: -a["nivel"])

    # --- rango anterior de igual duración (para las variaciones de los indicadores clave)
    n = len(meses)
    anterior = None
    if n <= MAX_MESES and ini.year > 2000:
        try:
            a_hasta = calendario.suma_meses(ini, -1)
            a_desde = calendario.suma_meses(ini, -n)
            anterior = construir(db, desde=f"{a_desde.year}-{a_desde.month:02d}", hasta=f"{a_hasta.year}-{a_hasta.month:02d}", agrupar=agrupar,
                                 area_id=area_id, frecuencia=frecuencia, seguimiento=seguimiento, indicador_id=indicador_id,
                                 solo_aprobadas=solo_aprobadas, dimension=dimension, hoy=hoy, _anterior=True)["kpis"]
        except Invalido:
            anterior = None

    return {
        "rango": {"desde": ini.isoformat(), "hasta": fin.isoformat(), "meses": n, "agrupar": agrupar, "plazo_dias": PLAZO_DIAS},
        "kpis": kpis, "anterior": anterior, "actual": resumen_actual, "serie": serie, "por_dimension": por_dimension,
        "dimension": dimension, "indicadores": lista, "atencion": atencion[:15],
        "responsables": sorted(({**r, "a_tiempo_pct": _pct(r["a_tiempo"], r["cargas"]),
                                 "retraso_promedio": round(r["dias_retraso"] / r["cargas"], 1)} for r in responsables.values()),
                               key=lambda r: (-r["cargas"], r["nombre"])),
    }
