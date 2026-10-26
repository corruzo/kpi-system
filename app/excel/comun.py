"""Piezas comunes de los reportes en Excel: paleta, estilos, encabezados, impresión, logo y guardado."""

import io
from datetime import UTC, timedelta

from openpyxl.drawing.image import Image as XLImagen
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

NAVY, BRAND, GRIS, ZEBRA = "0F172A", "0284C7", "64748B", "F8FAFC"
SEM = {
    "verde": ("DCFCE7", "166534", "Cumple"),
    "amarillo": ("FEF3C7", "92400E", "Alerta"),
    "rojo": ("FEE2E2", "991B1B", "Crítico"),
}
ESTADO = {"enviado": "En revisión", "aprobado": "Aprobado", "observado": "Devuelto"}
FUENTE = "Calibri"
_lado = Side(style="thin", color="E2E8F0")
BORDE = Border(left=_lado, right=_lado, top=_lado, bottom=_lado)


def hora_local(dt):
    """UTC → hora de Venezuela (UTC−4, sin horario de verano)."""
    return (dt.replace(tzinfo=UTC) + timedelta(hours=-4)).replace(tzinfo=None) if dt else None


def formato_numero(unidad: str, dec: int) -> str:
    base = "#,##0" + ("." + "0" * dec if dec else "")
    return {"%": base + '"%"', "USD": '"$"' + base, "días": base + '" d"', "TM": base + '" TM"'}.get(
        unidad, base + (f' "{unidad}"' if unidad and unidad != "cantidad" else "")
    )


def relleno(hex_):
    return PatternFill("solid", start_color=hex_, end_color=hex_)


def encabezado_tabla(ws, fila, textos, ancho=None):
    for j, t in enumerate(textos, 1):
        c = ws.cell(fila, j, t)
        c.font = Font(name=FUENTE, bold=True, color="FFFFFF", size=10)
        c.fill = relleno(NAVY)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = BORDE
    ws.row_dimensions[fila].height = 32
    for j, w in enumerate(ancho or [], 1):
        ws.column_dimensions[get_column_letter(j)].width = w


def franja_titulo(ws, titulo, subtitulo, ncols):
    ws.sheet_view.showGridLines = False
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ncols)
    c = ws.cell(1, 1, titulo)
    c.font = Font(name=FUENTE, bold=True, size=16, color="FFFFFF")
    c.fill = relleno(NAVY)
    c.alignment = Alignment(vertical="center", indent=1)
    ws.row_dimensions[1].height = 34
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=ncols)
    c = ws.cell(2, 1, subtitulo)
    c.font = Font(name=FUENTE, size=10, color="FFFFFF")
    c.fill = relleno(BRAND)
    c.alignment = Alignment(vertical="center", indent=1)
    ws.row_dimensions[2].height = 20


def configurar_impresion(ws, fila_encabezado, apaisado=True):
    ws.page_setup.orientation = "landscape" if apaisado else "portrait"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_title_rows = f"{fila_encabezado}:{fila_encabezado}"
    ws.oddFooter.center.text = "Tripoliven, C.A. · SIGT · Página &P de &N"
    ws.page_margins.left = ws.page_margins.right = 0.4


def celda_semaforo(c, semaforo):
    bg, fg, txt = SEM[semaforo]
    c.value = txt
    c.fill = relleno(bg)
    c.font = Font(name=FUENTE, bold=True, color=fg, size=10)
    c.alignment = Alignment(horizontal="center", vertical="center")


def poner_logo(ws, logo: bytes | None, celda: str = "A1", alto: int = 36):
    """Inserta el logo de la empresa (PNG) si existe; devuelve True si se insertó."""
    if not logo:
        return False
    try:
        img = XLImagen(io.BytesIO(logo))
        img.width, img.height = int(img.width * alto / img.height), alto
        ws.add_image(img, celda)
        return True
    except Exception:
        return False


def a_bytes(wb) -> bytes:
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ------------------------------------------------------------------ reporte general
