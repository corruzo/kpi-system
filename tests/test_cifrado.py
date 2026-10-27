"""Cifrado de la contraseña de los reportes con una clave derivada de SIGT_SECRET."""
import pytest
from conftest import entrar
from sqlalchemy import select

from app import cifrado, security
from app.database import SessionLocal
from app.dominio import calendario
from app.models import Parametro


def test_cifrar_y_descifrar():
    c = cifrado.cifrar("secreta-123")
    assert cifrado.esta_cifrado(c) and "secreta" not in c
    assert cifrado.descifrar(c) == "secreta-123"
    assert cifrado.cifrar("secreta-123") != c      # cada cifrado usa un IV distinto


def test_un_valor_manipulado_o_en_claro_no_se_descifra():
    c = cifrado.cifrar("x")
    with pytest.raises(cifrado.ErrorDeCifrado):
        cifrado.descifrar(c[:-4] + "AAAA")
    with pytest.raises(cifrado.ErrorDeCifrado):
        cifrado.descifrar("texto-plano")


def test_otra_secret_no_puede_descifrar(monkeypatch):
    c = cifrado.cifrar("secreta-123")
    monkeypatch.setattr(security, "_SECRET", b"otra-secret-distinta-de-32-caracteres!")
    cifrado._fernet.cache_clear()
    try:
        with pytest.raises(cifrado.ErrorDeCifrado):
            cifrado.descifrar(c)
    finally:
        monkeypatch.undo()
        cifrado._fernet.cache_clear()


def _parametros(client, activa, clave=""):
    entrar(client, "admin", "clave-admin-123")
    return client.put("/api/parametros", json={"empresa": "TRIPOLIVEN, C.A.", "gerencia_emisora": "", "codigo_formato": "",
                                               "ejercicio_inicio": calendario.inicio_mes(), "proteger_reportes": activa,
                                               "clave_reportes": clave})


def test_la_clave_se_guarda_cifrada_y_los_reportes_siguen_bloqueados(client):
    assert _parametros(client, True, "secreta-123").status_code == 200
    try:
        with SessionLocal() as db:
            valor = db.scalar(select(Parametro.valor).where(Parametro.clave == "clave_reportes"))
        assert valor.startswith("fernet:") and "secreta-123" not in valor
        r = client.get("/api/reportes/bitacora.xlsx")
        assert r.status_code == 200
        from io import BytesIO

        from openpyxl import load_workbook
        wb = load_workbook(BytesIO(r.content))
        assert all(ws.protection.sheet for ws in wb.worksheets)
        assert _parametros(client, True).status_code == 200      # en blanco = conserva la cifrada
    finally:
        _parametros(client, False)


def test_si_cambia_la_secret_no_se_exporta_sin_proteccion(client, monkeypatch):
    assert _parametros(client, True, "secreta-123").status_code == 200
    try:
        monkeypatch.setattr(security, "_SECRET", b"otra-secret-distinta-de-32-caracteres!")
        cifrado._fernet.cache_clear()
        entrar(client, "admin", "clave-admin-123")      # la cookie anterior estaba firmada con la secret vieja
        r = client.get("/api/reportes/bitacora.xlsx")
        assert r.status_code == 409 and "SIGT_SECRET" in r.json()["detail"]
    finally:
        monkeypatch.undo()
        cifrado._fernet.cache_clear()
        _parametros(client, False)
