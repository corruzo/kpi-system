import base64
from io import BytesIO

from conftest import entrar
from openpyxl import load_workbook
from PIL import Image


def png_en_data_url(ancho=900, alto=300) -> str:
    buf = BytesIO()
    Image.new("RGB", (ancho, alto), (2, 132, 199)).save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def test_logo_se_valida_redimensiona_y_aparece_en_reportes(client):
    entrar(client, "admin", "clave-admin-123")
    assert client.put("/api/logo", json={"imagen": "data:text/html;base64,PGI+"}).status_code == 422
    assert client.put("/api/logo", json={"imagen": "data:image/png;base64,AAAA"}).status_code == 422
    r = client.put("/api/logo", json={"imagen": png_en_data_url()})
    assert r.status_code == 200 and r.json()["logo_url"].startswith("/api/logo?v=")
    try:
        imagen = client.get("/api/logo")
        assert imagen.headers["content-type"] == "image/png" and Image.open(BytesIO(imagen.content)).width == 600
        resumen = load_workbook(BytesIO(client.get("/api/reportes/general.xlsx").content))["Resumen"]
        assert len(resumen._images) == 1
        client.cookies.clear()                                       # el logo es público (pantalla de ingreso)
        assert client.get("/api/publico").json()["logo_url"]
    finally:
        entrar(client, "admin", "clave-admin-123")
        assert client.delete("/api/logo").json()["logo_url"] is None
