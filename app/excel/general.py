"""Reporte general en Excel: real contra presupuesto. Blanco y negro, sin logo ni gráficos (los gráficos viven en la aplicación).

Hojas:
  Resumen              totales y cumplimiento del presupuesto por área y por indicador.
  Real vs Presupuesto  una fila por indicador y período: presupuestado, real, diferencia, % y si cumple.
  Matriz <ejercicio>   por indicador, tres filas (presupuestado / real / diferencia) con los meses del ejercicio en columnas.
  Plan de mejora       análisis y correcciones de las cargas que no quedaron en verde (ISO 9001, 9.1.3 y 10.2).
  Indicadores          definición de cada indicador incluido.
Diferencia, porcentaje y «cumple» son fórmulas vivas de Excel: si alguien corrige un valor, se recalculan.
"""
from datetime import date, datetime

from openpyxl import Workbook
from openpyxl.utils import get_column_letter

from ..dominio import calendario
from ..dominio.ficha_texto import formula_en_palabras
from ..dominio.presupuesto import comparar
from .comun import (
    ESTADO,
    SEMAFORO,
    SENTIDO,
    ajustar,
    celda,
    configurar_impresion,
    encabezado_hoja,
    encabezado_tabla,
    formato_numero,
    fuente,
    hora_local,
)

PCT = "0.0%"


# ------------------------------------------------------------------ preparación de los datos
def _filas(indicadores, mediciones, presupuestos: dict, ejercicios: set[int], solo_cargadas: bool, hoy: date) -> list[dict]:
    """Una fila por (indicador, período): presupuesto guardado, medición (si existe) y su comparación."""
    por_medicion = {(m.indicador_id, m.periodo): m for m in mediciones}
    filas = []
    for ind in indicadores:
        periodos = {p for (i, p) in presupuestos if i == ind.id} | {p for (i, p) in por_medicion if i == ind.id}
        for p in periodos:
            if not calendario.periodo_valido(ind.frecuencia, p):
                continue
            anio = calendario.ejercicio_de(ind.frecuencia, p)
            m = por_medicion.get((ind.id, p))
            if anio not in ejercicios or (solo_cargadas and m is None):
                continue
            ppto = m.presupuesto if m is not None and m.presupuesto is not None else presupuestos.get((ind.id, p))
            real = m.resultado if m is not None and m.estado != "observado" else None
            ini, fin = calendario.rango(ind.frecuencia, p)
            estado = ESTADO[m.estado] if m else ("Sin cargar" if fin < hoy else "Por venir")
            filas.append({"ind": ind, "periodo": p, "ejercicio": anio, "inicio": ini, "m": m, "presupuesto": ppto,
                          "real": real, "estado": estado,
                          "cmp": comparar(real, ppto, ind.sentido) if real is not None and ppto is not None else None})
    filas.sort(key=lambda f: (f["ejercicio"], f["ind"].codigo, f["inicio"]))
    return filas


def _formulas_comparacion(fila: int, col_ppto: str, col_real: str, mayor: bool) -> tuple[str, str, str]:
    """Diferencia, porcentaje y «cumple» como fórmulas de Excel (vacío si falta el presupuesto o el real)."""
    p, r = f"{col_ppto}{fila}", f"{col_real}{fila}"
    falta = f'OR({p}="",{r}="")'
    return (f'=IF({falta},"",{r}-{p})',
            f'=IF(OR({falta},{p}=0),"",{r}/{p})',
            f'=IF({falta},"",IF({r}{">=" if mayor else "<="}{p},"Sí","No"))')


# ------------------------------------------------------------------ hojas
def _hoja_resumen(ws, empresa, filas, indicadores, subtitulo, por_aprobar, n_cargas):
    fila0 = encabezado_hoja(ws, empresa, "Indicadores de gestión: real contra presupuesto", subtitulo)
    con_real = [f for f in filas if f["cmp"]]
    cumplen = sum(f["cmp"]["cumple"] for f in con_real)
    totales = [("Indicadores incluidos", len(indicadores)),
               ("Períodos presupuestados", sum(f["presupuesto"] is not None for f in filas)),
               ("Períodos con dato real y presupuesto", len(con_real)),
               ("Períodos que cumplen el presupuesto", cumplen),
               ("Períodos que no alcanzan el presupuesto", len(con_real) - cumplen),
               ("Cargas registradas", n_cargas), ("Cargas por aprobar", por_aprobar)]
    ws.cell(fila0, 1, "TOTALES").font = fuente(True, 11)
    fila = fila0 + 1
    for etiqueta, valor in totales:
        celda(ws, fila, 1, etiqueta, negrita=True)
        celda(ws, fila, 2, valor, "#,##0", alinear="center")
        fila += 1
    celda(ws, fila, 1, "% de cumplimiento del presupuesto", negrita=True)
    cumplen_ref, total_ref = f"B{fila0 + 4}", f"B{fila0 + 3}"
    celda(ws, fila, 2, f'=IF({total_ref}=0,"",{cumplen_ref}/{total_ref})', PCT, True, "center")

    fila += 2
    ws.cell(fila, 1, "CUMPLIMIENTO DEL PRESUPUESTO POR ÁREA").font = fuente(True, 11)
    fila += 1
    encabezado_tabla(ws, fila, ["Área", "Indicadores", "Períodos con real", "Cumplen", "No alcanzan", "% cumplimiento"],
                     [44, 16, 18, 14, 14, 18])
    areas: dict[str, dict] = {}
    for i in indicadores:
        areas.setdefault(i.area.nombre, {"ind": 0, "real": 0, "cumplen": 0})["ind"] += 1
    for f in con_real:
        a = areas[f["ind"].area.nombre]
        a["real"] += 1
        a["cumplen"] += f["cmp"]["cumple"]
    for nombre, a in sorted(areas.items()):
        fila += 1
        for j, v in enumerate([nombre, a["ind"], a["real"], a["cumplen"], f"=C{fila}-D{fila}", f'=IF(C{fila}=0,"",D{fila}/C{fila})'], 1):
            celda(ws, fila, j, v, PCT if j == 6 else ("#,##0" if j > 1 else None), j == 1, "left" if j == 1 else "center")

    fila += 2
    ws.cell(fila, 1, "CUMPLIMIENTO DEL PRESUPUESTO POR INDICADOR").font = fuente(True, 11)
    fila += 1
    encabezado_tabla(ws, fila, ["Indicador", "Área", "Períodos presupuestados", "Con real", "Cumplen", "No alcanzan", "% cumplimiento"])
    ws.column_dimensions["B"].width = 26
    por_ind: dict[int, dict] = {}
    for f in filas:
        d = por_ind.setdefault(f["ind"].id, {"ppto": 0, "real": 0, "cumplen": 0})
        d["ppto"] += f["presupuesto"] is not None
        if f["cmp"]:
            d["real"] += 1
            d["cumplen"] += f["cmp"]["cumple"]
    for i in indicadores:
        d = por_ind.get(i.id, {"ppto": 0, "real": 0, "cumplen": 0})
        fila += 1
        vals = [f"{i.codigo} · {i.nombre}", i.area.nombre, d["ppto"], d["real"], d["cumplen"], f"=D{fila}-E{fila}",
                f'=IF(D{fila}=0,"",E{fila}/D{fila})']
        for j, v in enumerate(vals, 1):
            celda(ws, fila, j, v, PCT if j == 7 else ("#,##0" if j > 2 else None), j == 1, "left" if j <= 2 else "center", ajustar_texto=j <= 2)
    configurar_impresion(ws, 0, empresa=empresa)
    ajustar(ws)


def _hoja_detalle(ws, empresa, filas, subtitulo):
    fila0 = encabezado_hoja(ws, empresa, "Real vs presupuesto por indicador y período", subtitulo)
    cols = ["Ejercicio", "Código", "Indicador", "Área", "Unidad", "Sentido", "Período", "Presupuestado", "Real", "Diferencia",
            "Real / presupuesto", "Cumple presupuesto", "Semáforo", "Estado"]
    encabezado_tabla(ws, fila0, cols, [12, 11, 44, 24, 10, 17, 24, 16, 14, 14, 14, 14, 12, 14])
    for k, f in enumerate(filas, fila0 + 1):
        ind, m = f["ind"], f["m"]
        fmt = formato_numero(ind.unidad, ind.precision)
        dif, pct, cumple = _formulas_comparacion(k, "H", "I", ind.sentido == "mayor")
        valores = [calendario.etiqueta_ejercicio(f["ejercicio"]), ind.codigo, ind.nombre, ind.area.nombre, ind.unidad,
                   SENTIDO[ind.sentido], calendario.etiqueta(ind.frecuencia, f["periodo"]), f["presupuesto"], f["real"], dif, pct,
                   cumple, SEMAFORO.get(m.semaforo, "") if m and f["real"] is not None else "", f["estado"]]
        for j, v in enumerate(valores, 1):
            c = celda(ws, k, j, v, fmt if j in (8, 9, 10) else (PCT if j == 11 else None),
                      alinear="left" if j in (3, 4, 6, 7) else "center", ajustar_texto=j == 3)
            if j == 12 and f["cmp"] and not f["cmp"]["cumple"]:
                c.font = fuente(True)                    # «No» destaca en negrita (el reporte es solo blanco y negro)
    ws.freeze_panes = ws.cell(fila0 + 1, 4)
    ws.auto_filter.ref = f"A{fila0}:{get_column_letter(len(cols))}{max(fila0 + 1, fila0 + len(filas))}"
    configurar_impresion(ws, fila0, empresa=empresa)
    ajustar(ws)


def _hoja_matriz(ws, empresa, anio, filas, subtitulo):
    """Meses del ejercicio en columnas; por indicador: presupuestado, real y diferencia."""
    fila0 = encabezado_hoja(ws, empresa, f"Matriz real vs presupuesto · ejercicio {calendario.etiqueta_ejercicio(anio)}",
                            [*subtitulo, "Cada período se ubica en el mes en que cierra (un trimestre aparece en su último mes)."])
    meses = calendario.meses_del_ejercicio()
    cols = ["Código", "Indicador", "Unidad", "Concepto", *meses, "Períodos con real", "Cumplen"]
    encabezado_tabla(ws, fila0, cols, [11, 42, 10, 16, *[12] * 12, 12, 12])
    fila = fila0
    for ind in sorted({f["ind"] for f in filas}, key=lambda i: i.codigo):
        propios = [f for f in filas if f["ind"].id == ind.id]
        fmt = formato_numero(ind.unidad, ind.precision)
        celdas: dict[int, dict] = {calendario.indice_de_mes(ind.frecuencia, f["periodo"]): f for f in propios}
        r_ppto, r_real = fila + 1, fila + 2
        for k, concepto in enumerate(("Presupuestado", "Real", "Diferencia")):
            r = fila + 1 + k
            celda(ws, r, 1, ind.codigo)
            celda(ws, r, 2, ind.nombre if k == 0 else "", ajustar_texto=True)
            celda(ws, r, 3, ind.unidad, alinear="center")
            celda(ws, r, 4, concepto, negrita=(k == 1))
            for mes in range(12):
                f = celdas.get(mes)
                col = 5 + mes
                letra = get_column_letter(col)
                if k == 0:
                    v = f["presupuesto"] if f else None
                elif k == 1:
                    v = f["real"] if f else None
                else:
                    v = f'=IF(OR({letra}{r_ppto}="",{letra}{r_real}=""),"",{letra}{r_real}-{letra}{r_ppto})'
                celda(ws, r, col, v, fmt, negrita=(k == 1), alinear="center")
            con_real = [f for f in propios if f["cmp"]]
            if k == 0:
                celda(ws, r, 17, len(con_real), "#,##0", alinear="center")
                celda(ws, r, 18, sum(f["cmp"]["cumple"] for f in con_real), "#,##0", alinear="center")
            else:
                celda(ws, r, 17, None)
                celda(ws, r, 18, None)
        fila += 3
    ws.freeze_panes = ws.cell(fila0 + 1, 5)
    configurar_impresion(ws, fila0, empresa=empresa)
    ajustar(ws)


def _hoja_plan(ws, empresa, filas, subtitulo):
    fila0 = encabezado_hoja(ws, empresa, "Plan de mejora: cargas fuera de meta (ISO 9001:2015, 9.1.3 y 10.2)", subtitulo)
    cols = ["Ejercicio", "Código", "Indicador", "Período", "Presupuestado", "Real", "Semáforo", "Resultados del análisis",
            "Correcciones / plan de mejora", "Estado"]
    encabezado_tabla(ws, fila0, cols, [12, 11, 36, 24, 16, 14, 12, 50, 50, 14])
    fuera = [f for f in filas if f["m"] and f["real"] is not None and f["m"].semaforo != "verde"]
    for k, f in enumerate(fuera, fila0 + 1):
        ind, m = f["ind"], f["m"]
        fmt = formato_numero(ind.unidad, ind.precision)
        valores = [calendario.etiqueta_ejercicio(f["ejercicio"]), ind.codigo, ind.nombre, calendario.etiqueta(ind.frecuencia, f["periodo"]),
                   f["presupuesto"], f["real"], SEMAFORO[m.semaforo], m.analisis, m.plan_mejora, f["estado"]]
        for j, v in enumerate(valores, 1):
            celda(ws, k, j, v, fmt if j in (5, 6) else None, alinear="center" if j in (1, 2, 5, 6, 7, 10) else "left",
                  ajustar_texto=j in (3, 4, 8, 9))
    if not fuera:
        ws.cell(fila0 + 1, 1, "No hay cargas fuera de meta en este reporte.").font = fuente(cursiva=True)
    configurar_impresion(ws, fila0, empresa=empresa)
    ajustar(ws)


def _hoja_indicadores(ws, empresa, indicadores, subtitulo):
    fila0 = encabezado_hoja(ws, empresa, "Indicadores incluidos", subtitulo)
    cols = ["Código", "Nombre", "Área", "Unidad", "Frecuencia", "Sentido", "Fórmula", "Meta (verde)", "Límite crítico", "Activo"]
    encabezado_tabla(ws, fila0, cols, [11, 40, 24, 10, 14, 17, 50, 14, 14, 9])
    for k, i in enumerate(indicadores, fila0 + 1):
        fmt = formato_numero(i.unidad, i.precision)
        valores = [i.codigo, i.nombre, i.area.nombre, i.unidad, i.frecuencia.capitalize(), SENTIDO[i.sentido],
                   formula_en_palabras(i.formula, i.variables, i.constantes or []), i.meta, i.limite, "Sí" if i.activo else "No"]
        for j, v in enumerate(valores, 1):
            celda(ws, k, j, v, fmt if j in (8, 9) else None, alinear="left" if j in (2, 3, 6, 7) else "center",
                  ajustar_texto=j in (2, 7))
    configurar_impresion(ws, fila0, empresa=empresa)
    ajustar(ws)


# ------------------------------------------------------------------ libro
def reporte_general(empresa: str, mediciones, indicadores, presupuestos: dict, ejercicios: list[int], generado_por: str,
                    filtros: str, por_aprobar: int, solo_cargadas: bool = False, hoy: date | None = None) -> Workbook:
    """mediciones: [Medicion]; indicadores: [Indicador] incluidos; presupuestos: {(indicador_id, período): valor};
    ejercicios: años fiscales que abarca el reporte."""
    hoy = hoy or date.today()
    wb = Workbook()
    wb.properties.creator = empresa
    wb.properties.title = "Real contra presupuesto"
    ahora = hora_local(datetime.utcnow())
    sub = [f"Generado el {ahora:%d/%m/%Y %H:%M} por {generado_por}", f"Filtros: {filtros or 'ninguno (todos los datos)'}"]
    filas = _filas(indicadores, mediciones, presupuestos, set(ejercicios), solo_cargadas, hoy)

    _hoja_resumen(wb.active, empresa, filas, indicadores, sub, por_aprobar, len(mediciones))
    wb.active.title = "Resumen"
    _hoja_detalle(wb.create_sheet("Real vs Presupuesto"), empresa, filas, sub)
    for anio in sorted(ejercicios):
        propias = [f for f in filas if f["ejercicio"] == anio]
        if propias:
            _hoja_matriz(wb.create_sheet(f"Matriz {calendario.etiqueta_ejercicio(anio)}"), empresa, anio, propias, sub)
    _hoja_plan(wb.create_sheet("Plan de mejora"), empresa, filas, sub)
    _hoja_indicadores(wb.create_sheet("Indicadores"), empresa, indicadores, sub)
    return wb
