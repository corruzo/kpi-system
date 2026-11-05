"""Ficha técnica de indicador en Excel (una hoja por indicador), con el formato del SGC y la comparación de lo real
contra lo presupuestado. Blanco y negro, sin logo y sin gráficos."""
import re
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter

from ..dominio import calendario
from ..dominio.ficha_texto import formula_documentada, franjas, meta_texto
from ..dominio.formula_excel import a_excel
from .comun import (
    BORDE,
    SEMAFORO,
    ajustar,
    formato_numero,
    fuente,
    hora_local,
    relleno_negro,
)
from .general import _formulas_comparacion
from .sello import formula_semaforo

NCOLS = 13


def _banda(ws, fila, texto, ncols=NCOLS):
    """Título de sección: franja negra a todo el ancho con letras blancas."""
    ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=ncols)
    c = ws.cell(fila, 1, texto)
    c.font = fuente(True, 10, blanca=True)
    c.fill = relleno_negro()
    c.alignment = Alignment(vertical="center", indent=1)
    ws.row_dimensions[fila].height = 20


def _par(ws, fila, c1, etiqueta, c2, c3, valor, alto=None, mono=False):
    """Etiqueta (c1) y valor combinado (c2..c3), con borde."""
    e = ws.cell(fila, c1, etiqueta)
    e.font = fuente(True)
    e.alignment = Alignment(vertical="center", wrap_text=True, indent=1)
    e.border = BORDE
    if c3 > c2:
        ws.merge_cells(start_row=fila, start_column=c2, end_row=fila, end_column=c3)
    v = ws.cell(fila, c2, valor or "—")                  # nunca una casilla vacía: «—» si el dato no se definió
    v.font = fuente(mono=mono)
    v.alignment = Alignment(vertical="top" if mono else "center", wrap_text=True, indent=1)
    for c in range(c2, c3 + 1):
        ws.cell(fila, c).border = BORDE
    if alto:
        ws.row_dimensions[fila].height = alto
    return v


def _titulos(ws, fila, textos, desde=1):
    for j, t in enumerate(textos, desde):
        c = ws.cell(fila, j, t)
        c.font = fuente(True, 9, blanca=True)
        c.fill = relleno_negro()
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = BORDE
    ws.row_dimensions[fila].height = 30


def _nombre_hoja(ind, usados: set[str]) -> str:
    base = re.sub(r"[\\/*?:\[\]]", "", ind.sigla or ind.codigo)[:28] or ind.codigo
    nombre, n = base, 2
    while nombre.lower() in usados:
        nombre, n = f"{base[:26]}_{n}", n + 1
    usados.add(nombre.lower())
    return nombre


def fichas_xlsx(fichas, params: dict, generado_por: str) -> Workbook:
    """fichas: [(Indicador, ejercicio, periodos[{periodo, etiqueta, corta, presupuesto, medicion}])]. Una hoja por indicador."""
    wb = Workbook()
    wb.remove(wb.active)
    empresa = params.get("empresa", "")
    wb.properties.creator = empresa
    usados: set[str] = set()
    ahora = hora_local(datetime.utcnow())
    for ind, y, periodos in fichas:
        ws = wb.create_sheet(_nombre_hoja(ind, usados))
        ws.sheet_view.showGridLines = False
        ws.column_dimensions["A"].width = 30
        for j in range(2, NCOLS + 1):
            ws.column_dimensions[get_column_letter(j)].width = {2: 13.5, 5: 15, 9: 15}.get(j, 11.5)
        tipo = {"proceso": "Desempeño de proceso", "objetivo": "Objetivo organizacional",
                "proveedor": "Desempeño de proveedor externo"}.get(ind.seguimiento or "proceso", "")
        etq1, etq2 = {"objetivo": ("OBJETIVO ORGANIZACIONAL", "OBJETIVO ESPECÍFICO"),
                      "proveedor": ("PROCESO", "BIEN o SERVICIO")}.get(ind.seguimiento or "proceso", ("PROCESO", "OBJETIVO DEL PROCESO"))
        fmt = formato_numero(ind.unidad, ind.precision)

        # --- encabezado: solo el nombre de la empresa
        ws.cell(1, 1, empresa).font = fuente(True, 16)
        ws.cell(2, 1, "FICHA TÉCNICA DE INDICADOR DE GESTIÓN").font = fuente(True, 12)
        ws.cell(3, 1, " · ".join(t for t in (params.get("gerencia_emisora", ""), f"Seguimiento de: {tipo}") if t)).font = fuente(tam=9)

        # --- proceso / objetivo (solo si la ficha los tiene: no se dejan franjas vacías)
        fila = 5
        if ind.ref_nombre:
            _banda(ws, fila, etq1)
            ws.merge_cells(start_row=fila + 1, start_column=1, end_row=fila + 1, end_column=NCOLS)
            ws.cell(fila + 1, 1, ind.ref_nombre).font = fuente(True, 11)
            ws.cell(fila + 1, 1).alignment = Alignment(indent=1, vertical="center", wrap_text=True)
            fila += 2
        detalle = ind.ref_detalle or ind.objetivo
        if detalle:
            _banda(ws, fila, etq2)
            ws.merge_cells(start_row=fila + 1, start_column=1, end_row=fila + 1, end_column=NCOLS)
            ws.cell(fila + 1, 1, detalle).font = fuente()
            ws.cell(fila + 1, 1).alignment = Alignment(wrap_text=True, vertical="top", indent=1)
            fila += 2

        # --- definición y semáforo
        d = fila
        _banda(ws, d, "DEFINICIÓN DEL INDICADOR E INFORMACIÓN PARA LA MEDICIÓN")
        nombre_ind = ind.nombre + (f" ({ind.sigla})" if ind.sigla and f"({ind.sigla})" not in ind.nombre else "")
        _par(ws, d + 1, 1, "Nombre del indicador", 2, 7, nombre_ind, 30)
        _par(ws, d + 2, 1, "Unidad de medida", 2, 3, ind.unidad)
        _par(ws, d + 2, 4, "Meta", 5, 7, meta_texto(ind))
        _par(ws, d + 3, 1, "Frecuencia de medición", 2, 7, ind.frecuencia.capitalize())
        _par(ws, d + 4, 1, "Fórmula de cálculo", 2, 7, formula_documentada(ind), mono=True)
        ws.merge_cells(start_row=d + 4, start_column=2, end_row=d + 6, end_column=7)
        for r in (d + 5, d + 6):
            for cc in range(2, 8):
                ws.cell(r, cc).border = BORDE
        ws.merge_cells(start_row=d + 4, start_column=1, end_row=d + 6, end_column=1)
        _par(ws, d + 7, 1, "Fuente de la información", 2, 7, ind.fuente, 22)

        ws.merge_cells(start_row=d + 1, start_column=9, end_row=d + 1, end_column=13)
        c = ws.cell(d + 1, 9, "SEMÁFORO")
        c.font = fuente(True, 10, blanca=True)
        c.fill = relleno_negro()
        c.alignment = Alignment(horizontal="center", vertical="center")
        for col, t in ((10, "Mín."), (12, "Máx.")):
            ws.merge_cells(start_row=d + 2, start_column=col, end_row=d + 2, end_column=col + 1)
            h = ws.cell(d + 2, col, t)
            h.font = fuente(True, 9)
            h.alignment = Alignment(horizontal="center")
        verde, amar, rojo = franjas(ind)
        for r, (nom, (mn, mx)) in enumerate((("Verde", verde), ("Amarillo", amar), ("Rojo", rojo)), d + 3):
            e = ws.cell(r, 9, nom)
            e.font = fuente(True)
            e.alignment = Alignment(horizontal="center", vertical="center")
            e.border = BORDE
            for col, val in ((10, mn), (12, mx)):
                ws.merge_cells(start_row=r, start_column=col, end_row=r, end_column=col + 1)
                v = ws.cell(r, col, val if val not in (None, "") else "—")
                v.number_format = fmt
                v.alignment = Alignment(horizontal="center", vertical="center")
                v.font = fuente()
                for cc in (col, col + 1):
                    ws.cell(r, cc).border = BORDE
        _par(ws, d + 7, 9, "Ejercicio fiscal", 10, 13, calendario.etiqueta_ejercicio(y))

        # --- responsabilidades
        _banda(ws, d + 8, "RESPONSABILIDADES")
        _par(ws, d + 9, 1, "Gerencia", 2, 4, ind.gerencia, 22)
        _par(ws, d + 9, 5, "Departamento", 6, 8, ind.area.nombre)
        _par(ws, d + 9, 9, "Líder de proceso", 10, 13, ind.lider)
        _par(ws, d + 10, 1, "Responsable de medición", 2, 4, ind.resp_medicion, 22)
        _par(ws, d + 10, 5, "Responsable de registro", 6, 8, ind.resp_registro)
        _par(ws, d + 10, 9, "Responsable de análisis", 10, 13, ind.resp_analisis)

        # --- datos de cada período (las variables que digitó el jefe); solo las columnas de períodos que existen
        n = len(periodos)
        span = max(1, 12 // max(n, 1))                  # 12, 6, 4, 3, 2 o 1 períodos: cada uno ocupa 1, 2, 3, 4, 6 o 12 columnas
        col_per = [2 + j * span for j in range(n)]       # primera columna de cada período (la cuadrícula siempre llena el ancho)
        _banda(ws, d + 11, "RESULTADOS DE LAS DETERMINACIONES")
        fila = d + 12
        ws.cell(fila, 1, "PERÍODOS")
        for j, p in enumerate(periodos):
            if span > 1:
                ws.merge_cells(start_row=fila, start_column=col_per[j], end_row=fila, end_column=col_per[j] + span - 1)
            ws.cell(fila, col_per[j], p["corta"])
        for j in range(1, NCOLS + 1):
            c = ws.cell(fila, j)
            c.font = fuente(True, 9, blanca=True)
            c.fill = relleno_negro()
            c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            c.border = BORDE
        ws.row_dimensions[fila].height = 30
        fila = d + 13
        fila_variable = {v["clave"]: fila + k for k, v in enumerate(ind.variables)}
        for v in ind.variables:
            e = ws.cell(fila, 1, v["etiqueta"])
            e.font = fuente()
            e.alignment = Alignment(wrap_text=True, vertical="center", indent=1)
            e.border = BORDE
            for j in range(n):
                if span > 1:
                    ws.merge_cells(start_row=fila, start_column=col_per[j], end_row=fila, end_column=col_per[j] + span - 1)
                for cc in range(col_per[j], col_per[j] + span):
                    ws.cell(fila, cc).border = BORDE
                c = ws.cell(fila, col_per[j])
                c.font = fuente()
                c.alignment = Alignment(horizontal="center", vertical="center")
                if periodos[j]["medicion"] and periodos[j]["medicion"].estado != "observado":
                    c.value = periodos[j]["medicion"].valores.get(v["clave"])
                    if c.value is None and v.get("opcional"):
                        c.value = v.get("defecto", 0)          # el sistema usó el valor por defecto
                    c.number_format = "#,##0.##"
            fila += 1

        # --- real contra presupuesto, período por período; ocupa todo el ancho de la ficha (13 columnas)
        # columnas: A período · B-C presupuestado · D-E real · F-G diferencia · H-I real/presupuesto · J-K cumple · L semáforo · M estado
        fila += 1
        _banda(ws, fila, "REAL VS PRESUPUESTO")
        fila += 1
        grupos = [(1, 1, "Período"), (2, 3, "Presupuestado"), (4, 5, "Real"), (6, 7, "Diferencia"), (8, 9, "Real / presupuesto"),
                  (10, 11, "Cumple presupuesto"), (12, 12, "Semáforo"), (13, 13, "Estado")]
        for c1, c2, t in grupos:
            if c2 > c1:
                ws.merge_cells(start_row=fila, start_column=c1, end_row=fila, end_column=c2)
            ws.cell(fila, c1, t)
        for j in range(1, NCOLS + 1):
            c = ws.cell(fila, j)
            c.font = fuente(True, 9, blanca=True)
            c.fill = relleno_negro()
            c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            c.border = BORDE
        ws.row_dimensions[fila].height = 30
        mayor = ind.sentido == "mayor"
        for idx, per in enumerate(periodos):
            fila += 1
            m = per["medicion"] if per["medicion"] and per["medicion"].estado != "observado" else None
            ppto = m.presupuesto if m is not None and m.presupuesto is not None else per.get("presupuesto")
            dif, pct, cumple = _formulas_comparacion(fila, "B", "D", mayor)
            estado = {"enviado": "En revisión", "aprobado": "Aprobado"}.get(m.estado, "") if m else \
                ("Devuelto" if per["medicion"] else "Sin cargar")
            valores = {1: per["etiqueta"], 2: ppto, 4: m.resultado if m else None, 6: dif, 8: pct, 10: cumple, 12: "", 13: estado}
            for c1, c2, _ in grupos:
                if c2 > c1:
                    ws.merge_cells(start_row=fila, start_column=c1, end_row=fila, end_column=c2)
                c = ws.cell(fila, c1, valores[c1])
                for j in range(c1, c2 + 1):
                    ws.cell(fila, j).border = BORDE
                c.font = fuente(c1 == 4)
                c.alignment = Alignment(horizontal="left" if c1 == 1 else "center", vertical="center", indent=1 if c1 == 1 else 0)
                if c1 in (2, 4, 6):
                    c.number_format = fmt
                elif c1 == 8:
                    c.number_format = "0.0%"
            if m:
                # el resultado se recalcula desde los datos de la columna del período; si la fórmula no tiene
                # equivalente en Excel, queda el valor calculado por el sistema
                col = get_column_letter(col_per[idx])
                celdas = {v["clave"]: f"{col}{fila_variable[v['clave']]}" for v in ind.variables}
                celdas.update({k["clave"]: repr(k["valor"]) for k in m.constantes_aplicadas})
                formula = a_excel(m.formula_aplicada, celdas, m.precision)
                if formula:
                    ws.cell(fila, 4).value = formula
                if m.meta_tope is None and m.limite_tope is None:
                    ws.cell(fila, 12).value = formula_semaforo(f"D{fila}", m.meta, m.limite, m.sentido == "mayor")
                else:
                    ws.cell(fila, 12).value = SEMAFORO[m.semaforo]

        # --- análisis y evaluación
        fila += 2
        _banda(ws, fila, "ANÁLISIS Y EVALUACIÓN DE RESULTADOS")
        fila += 1
        ws.cell(fila, 1, "Período")
        ws.merge_cells(start_row=fila, start_column=2, end_row=fila, end_column=7)
        ws.cell(fila, 2, "Resultados del análisis")
        ws.merge_cells(start_row=fila, start_column=8, end_row=fila, end_column=13)
        ws.cell(fila, 8, "Correcciones, oportunidades o necesidades de mejora, propuestas de cambios y adecuación de recursos")
        for j in range(1, NCOLS + 1):
            c = ws.cell(fila, j)
            c.font = fuente(True, 9, blanca=True)
            c.fill = relleno_negro()
            c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            c.border = BORDE
        ws.row_dimensions[fila].height = 32
        con_texto = [(per, per["medicion"]) for per in periodos
                     if per["medicion"] and per["medicion"].estado != "observado" and (per["medicion"].analisis or per["medicion"].plan_mejora)]
        if not con_texto:
            fila += 1
            ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=NCOLS)
            ws.cell(fila, 1, "Sin análisis registrados: todos los períodos cargados están dentro de meta.").font = fuente(cursiva=True)
            ws.cell(fila, 1).alignment = Alignment(indent=1)
        for per, m in con_texto:                       # solo los períodos con análisis: sin filas en blanco
            fila += 1
            ws.cell(fila, 1, per["etiqueta"]).font = fuente(True)
            ws.cell(fila, 1).alignment = Alignment(vertical="top", indent=1, wrap_text=True)
            ws.merge_cells(start_row=fila, start_column=2, end_row=fila, end_column=7)
            ws.merge_cells(start_row=fila, start_column=8, end_row=fila, end_column=13)
            ws.cell(fila, 2, m.analisis)
            ws.cell(fila, 8, m.plan_mejora)
            for j in range(1, NCOLS + 1):
                c = ws.cell(fila, j)
                c.border = BORDE
                if j in (2, 8):
                    c.font = fuente()
                    c.alignment = Alignment(wrap_text=True, vertical="top", indent=1)
            ws.row_dimensions[fila].height = 20

        # --- notas y pie
        fila += 2
        if ind.notas:
            _banda(ws, fila, "NOTAS")
            fila += 1
            ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=NCOLS)
            ws.cell(fila, 1, ind.notas)
            ws.cell(fila, 1).alignment = Alignment(wrap_text=True, vertical="top", indent=1)
            ws.cell(fila, 1).font = fuente()
            fila += 2
        ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=NCOLS)
        pie = " · ".join(t for t in (params.get("codigo_formato", ""), f"Generado el {ahora:%d/%m/%Y %H:%M} por {generado_por}") if t)
        ws.cell(fila, 1, pie).font = fuente(tam=8)
        ws.cell(fila, 1).alignment = Alignment(horizontal="right")
        ws.print_area = f"A1:M{fila}"
        ws.page_setup.orientation = "portrait"
        ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_margins.left = ws.page_margins.right = 0.4
        ws.oddFooter.center.text = f"{empresa.replace('&', '&&')} · Página &P de &N"
        ajustar(ws, columnas=False)               # la cuadrícula de 13 columnas es fija: solo se ajustan las filas
    return wb
