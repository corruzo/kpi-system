"""Un .xlsx es un zip: se rechazan los que se expandirían a gigabytes o traen miles de partes."""
import io
import zipfile

import pytest
from conftest import entrar

from app.servicios import zip_seguro


def _zip(entradas: dict[str, bytes]) -> bytes:
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        for nombre, datos in entradas.items():
            z.writestr(nombre, datos)
    return b.getvalue()


@pytest.fixture(scope="module")
def bomba():
    """~60 MB de ceros: pesa apenas unos KB comprimido."""
    contenido = _zip({"xl/worksheets/sheet1.xml": bytes(zip_seguro.MAX_DESCOMPRIMIDO + 10_000_000)})
    assert len(contenido) < 1_000_000
    return contenido


def test_validar_acepta_un_zip_normal():
    zip_seguro.validar_xlsx(_zip({"a.xml": b"<x/>", "b.xml": b"<y/>"}))


def test_validar_rechaza_lo_que_no_es_zip():
    with pytest.raises(ValueError, match="Excel"):
        zip_seguro.validar_xlsx(b"esto no es un zip")


def test_validar_rechaza_exceso_de_tamano_descomprimido(bomba):
    with pytest.raises(ValueError, match="descomprimirse"):
        zip_seguro.validar_xlsx(bomba)


def test_validar_rechaza_exceso_de_entradas():
    with pytest.raises(ValueError, match="demasiadas"):
        zip_seguro.validar_xlsx(_zip({f"f{i}.xml": b"" for i in range(zip_seguro.MAX_ENTRADAS + 1)}))


def test_importar_excel_rechaza_zip_bomb(client, bomba):
    entrar(client, "admin", "clave-admin-123")
    r = client.post("/api/importar/excel", files={"archivo": ("bomba.xlsx", bomba)})
    assert r.status_code == 422
    assert "descomprimirse" in r.json()["detail"]


def test_verificar_reporte_rechaza_zip_bomb(client, bomba):
    entrar(client, "admin", "clave-admin-123")
    r = client.post("/api/reportes/verificar", files={"archivo": ("bomba.xlsx", bomba)})
    assert r.status_code == 422
    assert "descomprimirse" in r.json()["detail"]


def test_verificar_reporte_rechaza_archivo_de_mas_de_10_mb(client):
    entrar(client, "admin", "clave-admin-123")
    r = client.post("/api/reportes/verificar", files={"archivo": ("grande.xlsx", bytes(10_000_001))})
    assert r.status_code == 422
