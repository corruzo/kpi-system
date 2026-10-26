"""Reportes en Excel (.xlsx) con formato corporativo."""
import io
import re
from datetime import datetime, timedelta, timezone

from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.formatting.rule import DataBarRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from . import calc

NAVY, BRAND, GRIS, ZEBRA = "0F172A", "0284C7", "64748B", "F8FAFC"
SEM = {"verde": ("DCFCE7", "166534", "Cumple"), "amarillo": ("FEF3C7", "92400E", "Alerta"),
       "rojo": ("FEE2E2", "991B1B", "Crítico")}
ESTADO = {"enviado": "En revisión", "aprobado": "Aprobado", "observado": "Devuelto"}
FUENTE = "Calibri"
_lado = Side(style="thin", color="E2E8F0")
BORDE = Border(left=_lado, right=_lado, top=_lado, bottom=_lado)


def _local(dt):
    """UTC → hora de Venezuela (UTC−4, sin horario de verano)."""
    return (dt.replace(tzinfo=timezone.utc) + timedelta(hours=-4)).replace(tzinfo=None) if dt else None


def _fmt_num(unidad: str, dec: int) -> str:
    base = "#,##0" + ("." + "0" * dec if dec else "")
    return {"%": base + '"%"', "USD": '"$"' + base, "días": base + '" d"', "TM": base + '" TM"'}.get(
        unidad, base + (f' "{unidad}"' if unidad and unidad != "cantidad" else ""))


def _fill(hex_):
    return PatternFill("solid", start_color=hex_, end_color=hex_)


def _encabezado(ws, fila, textos, ancho=None):
    for j, t in enumerate(textos, 1):
        c = ws.cell(fila, j, t)
        c.font = Font(name=FUENTE, bold=True, color="FFFFFF", size=10)
        c.fill = _fill(NAVY)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = BORDE
    ws.row_dimensions[fila].height = 32
    for j, w in enumerate(ancho or [], 1):
        ws.column_dimensions[get_column_letter(j)].width = w


def _titulo(ws, titulo, subtitulo, ncols):
    ws.sheet_view.showGridLines = False
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ncols)
    c = ws.cell(1, 1, titulo)
    c.font = Font(name=FUENTE, bold=True, size=16, color="FFFFFF")
    c.fill = _fill(NAVY)
    c.alignment = Alignment(vertical="center", indent=1)
    ws.row_dimensions[1].height = 34
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=ncols)
    c = ws.cell(2, 1, subtitulo)
    c.font = Font(name=FUENTE, size=10, color="FFFFFF")
    c.fill = _fill(BRAND)
    c.alignment = Alignment(vertical="center", indent=1)
    ws.row_dimensions[2].height = 20


def _impresion(ws, fila_encabezado, apaisado=True):
    ws.page_setup.orientation = "landscape" if apaisado else "portrait"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_title_rows = f"{fila_encabezado}:{fila_encabezado}"
    ws.oddFooter.center.text = "Tripoliven, C.A. · SIGT · Página &P de &N"
    ws.page_margins.left = ws.page_margins.right = 0.4


def _celda_sem(c, semaforo):
    bg, fg, txt = SEM[semaforo]
    c.value = txt
    c.fill = _fill(bg)
    c.font = Font(name=FUENTE, bold=True, color=fg, size=10)
    c.alignment = Alignment(horizontal="center", vertical="center")


def _legible(formula, variables):
    t = formula
    for v in sorted(variables, key=lambda v: -len(v["clave"])):
        t = re.sub(r"\b" + re.escape(v["clave"]) + r"\b", v["etiqueta"], t)
    return t


def _guardar(wb) -> bytes:
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ------------------------------------------------------------------ reporte general
def reporte_general(mediciones, indicadores, generado_por: str, filtros: str, por_aprobar: int) -> bytes:
    """mediciones: [Medicion]; indicadores: [Indicador] (los incluidos en el reporte)."""
    wb = Workbook()
    ahora = _local(datetime.utcnow())
    sub = f"Reporte de indicadores de gestión · Generado el {ahora:%d/%m/%Y %H:%M} por {generado_por}"

    # ---------- Resumen
    ws = wb.active
    ws.title = "Resumen"
    _titulo(ws, "Tripoliven, C.A. — Sistema de Indicadores de Gestión", sub, 7)
    ws["A4"], ws["B4"] = "Filtros aplicados", filtros or "Ninguno (todos los datos)"
    ws["A4"].font = Font(name=FUENTE, bold=True, color=GRIS)
    ultimo = {}
    for m in sorted(mediciones, key=lambda m: (m.indicador_id, m.periodo)):
        if m.estado in ("enviado", "aprobado"):
            ultimo[m.indicador_id] = m
    conteo = {"verde": 0, "amarillo": 0, "rojo": 0}
    por_area: dict[str, dict] = {}
    for i in indicadores:
        a = por_area.setdefault(i.area.nombre, {"total": 0, "verde": 0, "amarillo": 0, "rojo": 0, "sin": 0})
        a["total"] += 1
        m = ultimo.get(i.id)
        if m:
            conteo[m.semaforo] += 1
            a[m.semaforo] += 1
        else:
            a["sin"] += 1
    total = len(indicadores)
    kpis = [("Indicadores", total), ("Cumplimiento (verde)", conteo["verde"] / total if total else 0),
            ("En alerta", conteo["amarillo"]), ("Críticos", conteo["rojo"]),
            ("Cargas registradas", len(mediciones)), ("Por aprobar", por_aprobar)]
    colores = [NAVY, "16A34A", "F59E0B", "DC2626", BRAND, GRIS]
    for k, ((t, v), col) in enumerate(zip(kpis, colores)):
        r, c = 6 + (k // 3) * 3, 1 + (k % 3) * 2
        ws.merge_cells(start_row=r, start_column=c, end_row=r, end_column=c + 1)
        ws.merge_cells(start_row=r + 1, start_column=c, end_row=r + 1, end_column=c + 1)
        a = ws.cell(r, c, t.upper())
        a.font = Font(name=FUENTE, size=9, bold=True, color="FFFFFF")
        a.fill = _fill(col)
        a.alignment = Alignment(horizontal="center")
        ws.cell(r, c + 1).fill = _fill(col)
        b = ws.cell(r + 1, c, v)
        b.font = Font(name=FUENTE, size=20, bold=True, color=col)
        b.alignment = Alignment(horizontal="center", vertical="center")
        b.fill = _fill("FFFFFF")
        b.border = BORDE
        ws.cell(r + 1, c + 1).border = BORDE
        if t.startswith("Cumpl"):
            b.number_format = "0.0%"
        ws.row_dimensions[r + 1].height = 34
    f0 = 13
    ws.cell(f0 - 1, 1, "Cumplimiento por departamento (última medición de cada indicador)").font = \
        Font(name=FUENTE, bold=True, size=12, color=NAVY)
    _encabezado(ws, f0, ["Área", "Indicadores", "Cumple", "Alerta", "Crítico", "Sin datos", "% cumplimiento"],
                [30, 16, 14, 14, 14, 14, 20])
    for k, (nombre, a) in enumerate(sorted(por_area.items()), f0 + 1):
        fila = [nombre, a["total"], a["verde"], a["amarillo"], a["rojo"], a["sin"],
                a["verde"] / a["total"] if a["total"] else 0]
        for j, v in enumerate(fila, 1):
            c = ws.cell(k, j, v)
            c.font = Font(name=FUENTE, size=10, bold=(j == 1))
            c.border = BORDE
            c.alignment = Alignment(horizontal="left" if j == 1 else "center")
            if k % 2:
                c.fill = _fill(ZEBRA)
        ws.cell(k, 7).number_format = "0.0%"
    fin = f0 + len(por_area)
    if por_area:
        ws.conditional_formatting.add(f"G{f0 + 1}:G{fin}", DataBarRule(start_type="num", start_value=0,
                                                                      end_type="num", end_value=1, color="16A34A"))
        ch = BarChart()
        ch.type, ch.grouping, ch.overlap = "col", "stacked", 100
        ch.title = "Semáforos por departamento"
        ch.add_data(Reference(ws, min_col=3, max_col=5, min_row=f0, max_row=fin), titles_from_data=True)
        ch.set_categories(Reference(ws, min_col=1, min_row=f0 + 1, max_row=fin))
        for s, col in zip(ch.series, ("16A34A", "F59E0B", "DC2626")):
            s.graphicalProperties.solidFill = col
            s.graphicalProperties.line.solidFill = col
        ch.x_axis.delete = ch.y_axis.delete = False  # Excel oculta los ejes si no se indica
        ch.y_axis.numFmt, ch.y_axis.majorGridlines = "0", None
        ch.height, ch.width = 8.5, 20
        ws.add_chart(ch, f"A{fin + 3}")
    _impresion(ws, f0, apaisado=False)

    # ---------- Mediciones
    ws = wb.create_sheet("Mediciones")
    cols = ["Código", "Indicador", "Área", "Período", "Frecuencia", "Resultado", "Meta", "Límite crítico", "Sentido",
            "Semáforo", "Estado", "Cargado por", "Fecha de carga", "Revisado por", "Fecha de revisión",
            "Nota de revisión", "Análisis de resultados", "Correcciones / plan de mejora", "Versión"]
    anchos = [10, 38, 20, 16, 12, 14, 12, 14, 12, 12, 13, 24, 17, 24, 17, 34, 44, 44, 9]
    _titulo(ws, "Mediciones registradas", sub, len(cols))
    _encabezado(ws, 4, cols, anchos)
    ordenadas = sorted(mediciones, key=lambda m: (m.indicador.codigo, m.periodo))
    for k, m in enumerate(ordenadas, 5):
        i = m.indicador
        dec = m.decimales if m.decimales is not None else (i.decimales if i.decimales is not None else 2)
        fila = [i.codigo, i.nombre, i.area.nombre, calc.etiqueta(i.frecuencia, m.periodo), i.frecuencia.capitalize(),
                m.resultado, m.meta, m.limite, "Mayor es mejor" if m.sentido == "mayor" else "Menor es mejor", None,
                ESTADO[m.estado], m.cargado_por.nombre, _local(m.cargado_en),
                m.revisado_por.nombre if m.revisado_por else "", _local(m.revisado_en), m.nota_revision,
                m.analisis, m.plan_mejora, m.version]
        for j, v in enumerate(fila, 1):
            c = ws.cell(k, j, v)
            c.font = Font(name=FUENTE, size=10)
            c.border = BORDE
            c.alignment = Alignment(vertical="top", wrap_text=j in (2, 16, 17, 18))
            if k % 2:
                c.fill = _fill(ZEBRA)
        for j in (6, 7, 8):
            ws.cell(k, j).number_format = _fmt_num(i.unidad, dec)
        ws.cell(k, 6).font = Font(name=FUENTE, size=10, bold=True)
        for j in (13, 15):
            ws.cell(k, j).number_format = "dd/mm/yyyy hh:mm"
        _celda_sem(ws.cell(k, 10), m.semaforo)
        ws.cell(k, 10).border = BORDE
    ws.freeze_panes = "C5"
    ws.auto_filter.ref = f"A4:{get_column_letter(len(cols))}{max(5, 4 + len(ordenadas))}"
    _impresion(ws, 4)

    # ---------- Tendencias (matriz indicador × período, por frecuencia)
    ws = wb.create_sheet("Tendencias")
    _titulo(ws, "Tendencias por indicador", sub, 12)
    fila = 4
    ws.column_dimensions["A"].width = 10
    ws.column_dimensions["B"].width = 38
    for freq in ("mensual", "trimestral", "semestral", "anual"):
        inds = [i for i in indicadores if i.frecuencia == freq]
        if not inds:
            continue
        validas = [m for m in mediciones if m.indicador.frecuencia == freq and m.estado in ("enviado", "aprobado")]
        periodos = sorted({m.periodo for m in validas})
        ws.cell(fila, 1, f"Indicadores {freq}es" if freq != "anual" else "Indicadores anuales").font = \
            Font(name=FUENTE, bold=True, size=12, color=NAVY)
        fila += 1
        _encabezado(ws, fila, ["Código", "Indicador"] + [calc.etiqueta(freq, p) for p in periodos] + ["Meta"])
        for j in range(3, 3 + len(periodos) + 1):
            ws.column_dimensions[get_column_letter(j)].width = max(ws.column_dimensions[get_column_letter(j)].width or 0, 15)
        por = {(m.indicador_id, m.periodo): m for m in validas}
        for i in sorted(inds, key=lambda x: x.codigo):
            fila += 1
            dec = i.decimales if i.decimales is not None else 2
            ws.cell(fila, 1, i.codigo).font = Font(name=FUENTE, bold=True, size=10)
            ws.cell(fila, 2, i.nombre).alignment = Alignment(wrap_text=True, vertical="center")
            for j, p in enumerate(periodos, 3):
                m = por.get((i.id, p))
                c = ws.cell(fila, j, m.resultado if m else None)
                c.number_format = _fmt_num(i.unidad, dec)
                c.alignment = Alignment(horizontal="center", vertical="center")
                if m:
                    bg, fg, _ = SEM[m.semaforo]
                    c.fill = _fill(bg)
                    c.font = Font(name=FUENTE, bold=True, color=fg, size=10)
            c = ws.cell(fila, 3 + len(periodos), i.meta)
            c.number_format = _fmt_num(i.unidad, dec)
            c.font = Font(name=FUENTE, italic=True, color=GRIS, size=10)
            c.alignment = Alignment(horizontal="center", vertical="center")
            for j in range(1, 4 + len(periodos)):
                ws.cell(fila, j).border = BORDE
        fila += 3
    ws.freeze_panes = "C4"
    _impresion(ws, 4)

    # ---------- Plan de mejora (ISO 9001: 9.1.3 y 10.2)
    ws = wb.create_sheet("Plan de mejora")
    cols = ["Código", "Indicador", "Área", "Período", "Resultado", "Meta", "Semáforo", "Estado",
            "Análisis de resultados", "Correcciones / plan de mejora", "Responsable de la carga"]
    _titulo(ws, "Desviaciones y acciones correctivas (ISO 9001:2015, 9.1.3 y 10.2)", sub, len(cols))
    _encabezado(ws, 4, cols, [10, 36, 20, 16, 13, 12, 12, 13, 50, 50, 24])
    desv = [m for m in ordenadas if m.semaforo != "verde"]
    for k, m in enumerate(sorted(desv, key=lambda m: (m.semaforo != "rojo", m.indicador.codigo, m.periodo)), 5):
        i = m.indicador
        dec = m.decimales if m.decimales is not None else 2
        fila = [i.codigo, i.nombre, i.area.nombre, calc.etiqueta(i.frecuencia, m.periodo), m.resultado, m.meta, None,
                ESTADO[m.estado], m.analisis, m.plan_mejora, m.cargado_por.nombre]
        for j, v in enumerate(fila, 1):
            c = ws.cell(k, j, v)
            c.font = Font(name=FUENTE, size=10)
            c.border = BORDE
            c.alignment = Alignment(vertical="top", wrap_text=j in (2, 9, 10))
        for j in (5, 6):
            ws.cell(k, j).number_format = _fmt_num(i.unidad, dec)
        _celda_sem(ws.cell(k, 7), m.semaforo)
    ws.freeze_panes = "C5"
    ws.auto_filter.ref = f"A4:{get_column_letter(len(cols))}{max(5, 4 + len(desv))}"
    _impresion(ws, 4)

    # ---------- Fichas técnicas
    ws = wb.create_sheet("Fichas técnicas")
    cols = ["Código", "Indicador", "Área", "Objetivo", "Fuente de datos", "Unidad", "Frecuencia", "Sentido",
            "Meta (verde)", "Límite crítico", "Variables", "Constantes", "Fórmula", "Fórmula (en palabras)",
            "Método / notas", "Estado"]
    _titulo(ws, "Fichas técnicas de los indicadores", sub, len(cols))
    _encabezado(ws, 4, cols, [10, 36, 20, 40, 28, 10, 13, 15, 12, 13, 40, 28, 34, 46, 40, 11])
    for k, i in enumerate(sorted(indicadores, key=lambda x: x.codigo), 5):
        consts = i.constantes or []
        fila = [i.codigo, i.nombre, i.area.nombre, i.objetivo, i.fuente or "", i.unidad, i.frecuencia.capitalize(),
                "Mayor es mejor" if i.sentido == "mayor" else "Menor es mejor", i.meta, i.limite,
                "\n".join(f"• {v['etiqueta']} ({v['clave']})" for v in i.variables),
                "\n".join(f"• {c['etiqueta']} = {c['valor']}" for c in consts), i.formula,
                _legible(i.formula, [*i.variables, *consts]), i.notas or "", "Activo" if i.activo else "Archivado"]
        for j, v in enumerate(fila, 1):
            c = ws.cell(k, j, v)
            c.font = Font(name="Consolas" if j == 13 else FUENTE, size=10)
            c.border = BORDE
            c.alignment = Alignment(vertical="top", wrap_text=True)
            if k % 2:
                c.fill = _fill(ZEBRA)
    ws.freeze_panes = "C5"
    ws.auto_filter.ref = f"A4:{get_column_letter(len(cols))}{max(5, 4 + len(indicadores))}"
    _impresion(ws, 4)
    return _guardar(wb)


# ------------------------------------------------------------------ bitácora
def reporte_bitacora(registros, codigos: dict, generado_por: str, verificacion: dict) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Bitácora"
    ahora = _local(datetime.utcnow())
    estado = "ÍNTEGRA ✔" if verificacion["ok"] else f"ALTERADA ✖ (registro #{verificacion['primer_error_id']})"
    cols = ["#", "Fecha y hora", "Usuario", "Rol", "Acción", "Entidad", "Indicador", "Detalle", "Hash SHA-256"]
    _titulo(ws, "Bitácora de trazabilidad del sistema",
            f"Generado el {ahora:%d/%m/%Y %H:%M} por {generado_por} · Cadena de hashes: {estado} · "
            f"{verificacion['total']} registros", len(cols))
    _encabezado(ws, 4, cols, [8, 17, 28, 11, 22, 12, 11, 90, 24])
    for k, b in enumerate(registros, 5):
        det = "; ".join(f"{a}: {v}" for a, v in (b.detalle or {}).items())
        fila = [b.id, _local(b.fecha), b.usuario_nombre, b.rol, b.accion, b.entidad,
                codigos.get(b.indicador_id, ""), det, b.hash[:16] + "…"]
        for j, v in enumerate(fila, 1):
            c = ws.cell(k, j, v)
            c.font = Font(name="Consolas" if j == 9 else FUENTE, size=10, color=GRIS if j == 9 else "000000")
            c.border = BORDE
            c.alignment = Alignment(vertical="top", wrap_text=(j == 8))
            if k % 2:
                c.fill = _fill(ZEBRA)
        ws.cell(k, 2).number_format = "dd/mm/yyyy hh:mm:ss"
    ws.freeze_panes = "C5"
    ws.auto_filter.ref = f"A4:{get_column_letter(len(cols))}{max(5, 4 + len(registros))}"
    _impresion(ws, 4)
    return _guardar(wb)
