"""Bitácora del sistema en Excel (solo administrador). Blanco y negro, sin logo."""

from openpyxl import Workbook
from openpyxl.utils import get_column_letter

from .comun import ahora_local, ajustar, celda, configurar_impresion, encabezado_hoja, encabezado_tabla, hora_local


def reporte_bitacora(empresa: str, registros, codigos: dict, generado_por: str, verificacion: dict) -> Workbook:
    wb = Workbook()
    wb.properties.creator = empresa
    ws = wb.active
    ws.title = "Bitácora"
    ahora = ahora_local()
    estado = "íntegra" if verificacion["ok"] else f"ALTERADA (registro #{verificacion['primer_error_id']})"
    fila0 = encabezado_hoja(ws, empresa, "Bitácora de trazabilidad del sistema", [
        f"Generado el {ahora:%d/%m/%Y %H:%M} por {generado_por}",
        f"Cadena de huellas: {estado} · {verificacion['total']} registros"])
    cols = ["#", "Fecha y hora", "Usuario", "Rol", "Acción", "Entidad", "Indicador", "Detalle", "Huella SHA-256"]
    encabezado_tabla(ws, fila0, cols, [8, 19, 28, 11, 22, 12, 11, 90, 24])
    for k, b in enumerate(registros, fila0 + 1):
        det = "; ".join(f"{a}: {v}" for a, v in (b.detalle or {}).items())
        valores = [b.id, hora_local(b.fecha), b.usuario_nombre, b.rol, b.accion, b.entidad, codigos.get(b.indicador_id, ""),
                   det, b.hash[:16] + "…"]
        for j, v in enumerate(valores, 1):
            celda(ws, k, j, v, "dd/mm/yyyy hh:mm:ss" if j == 2 else None, alinear="center" if j in (1, 2, 4, 7) else "left",
                  ajustar_texto=(j == 8), mono=(j == 9))
    ws.freeze_panes = ws.cell(fila0 + 1, 3)
    ws.auto_filter.ref = f"A{fila0}:{get_column_letter(len(cols))}{max(fila0 + 1, fila0 + len(registros))}"
    configurar_impresion(ws, fila0, empresa=empresa)
    ajustar(ws)
    return wb
