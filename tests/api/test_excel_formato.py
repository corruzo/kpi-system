"""Orden de los Excel exportados: nada superpuesto, nada recortado y filas/columnas del tamaño de su contenido."""
import math
from io import BytesIO

import pytest
from conftest import entrar, periodo_actual
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

from app.excel.comun import altura_necesaria


@pytest.fixture(scope="module")
def libros(client):
    from conftest import crear_area, crear_indicador, crear_usuario
    area = crear_area(client)
    jefe = crear_usuario(client, "jefe", area)
    ind = crear_indicador(client, area, nombre="Indicador con un nombre bastante largo para obligar a que el texto se ajuste en varias líneas",
                          formula="(dias * 100) / tickets", variables=[{"clave": "dias", "etiqueta": "Días acumulados de atención al usuario"},
                                                                       {"clave": "tickets", "etiqueta": "Tickets"}])
    entrar(client, jefe)
    client.post("/api/mediciones", json={"indicador_id": ind["id"], "periodo": periodo_actual(client, ind["id"]),
                                         "valores": {"dias": 10, "tickets": 5}, "analisis": "A" * 300, "plan_mejora": "B " * 150})
    entrar(client, "admin", "clave-admin-123")
    rutas = {"general": "/api/reportes/general.xlsx", "fichas": f"/api/reportes/fichas.xlsx?indicador_id={ind['id']}",
             "bitacora": "/api/reportes/bitacora.xlsx"}
    return {k: load_workbook(BytesIO(client.get(r).content)) for k, r in rutas.items()}


def _hojas(libros):
    return [(f"{k}/{ws.title}", ws) for k, wb in libros.items() for ws in wb.worksheets]


def _alto_filas(ws, r1, r2):
    return sum(ws.row_dimensions[r].height or 15 for r in range(r1, r2 + 1))


def test_las_filas_con_texto_ajustado_tienen_la_altura_necesaria(libros):
    for nombre, ws in _hojas(libros):
        combinadas = {(rg.min_row, rg.min_col): rg for rg in ws.merged_cells.ranges}
        for fila in ws.iter_rows():
            for c in fila:
                if c.value in (None, "") or not (c.alignment and c.alignment.wrap_text):
                    continue
                rg = combinadas.get((c.row, c.column))
                ancho = sum(ws.column_dimensions[get_column_letter(k)].width or 8.43
                            for k in range(rg.min_col, rg.max_col + 1)) if rg else ws.column_dimensions[c.column_letter].width or 8.43
                alto = _alto_filas(ws, c.row, rg.max_row if rg else c.row)
                assert alto >= altura_necesaria(c, ancho) - 1, f"{nombre}!{c.coordinate} ({alto} < {altura_necesaria(c, ancho):.0f})"


def test_el_texto_sin_ajuste_cabe_en_su_columna(libros):
    for nombre, ws in _hojas(libros):
        combinadas = {(r, c) for rg in ws.merged_cells.ranges for r in range(rg.min_row, rg.max_row + 1)
                      for c in range(rg.min_col, rg.max_col + 1)}
        for fila in ws.iter_rows():
            if sum(1 for c in fila if c.value not in (None, "")) < 2:
                continue                                      # títulos de sección: se extienden sobre celdas vacías
            for c in fila:
                if not isinstance(c.value, str) or c.value.startswith("=") or (c.row, c.column) in combinadas:
                    continue
                if c.alignment and c.alignment.wrap_text:
                    continue
                ancho = ws.column_dimensions[c.column_letter].width or 8.43
                assert max(len(t) for t in c.value.split("\n")) <= math.ceil(ancho * 1.25), f"{nombre}!{c.coordinate}: «{c.value[:40]}»"


def test_los_reportes_son_en_blanco_y_negro_sin_logo_ni_graficos(libros):
    colores_permitidos = {"00000000", "FF000000", "FFFFFFFF", "00FFFFFF", None, ""}
    for nombre, ws in _hojas(libros):
        assert not ws._charts and not ws._images, f"{nombre}: lleva gráfico o imagen"
        for fila in ws.iter_rows():
            for c in fila:
                if c.value in (None, "") and not c.fill.fill_type:
                    continue
                relleno = c.fill.start_color.rgb if c.fill.fill_type else None
                letra = c.font.color.rgb if c.font and c.font.color is not None and isinstance(c.font.color.rgb, str) else None
                assert relleno in colores_permitidos and letra in colores_permitidos, f"{nombre}!{c.coordinate}: {relleno}/{letra}"


def test_cada_hoja_empieza_con_el_nombre_de_la_empresa(libros, client):
    empresa = client.get("/api/parametros").json()["empresa"]
    for nombre, ws in _hojas(libros):
        assert ws["A1"].value == empresa, nombre


def test_la_ficha_compara_real_y_presupuesto(libros):
    ws = libros["fichas"].worksheets[0]
    textos = [c.value for fila in ws.iter_rows() for c in fila if isinstance(c.value, str)]
    assert "REAL VS PRESUPUESTO" in textos and "Presupuestado" in textos and "Cumple presupuesto" in textos
