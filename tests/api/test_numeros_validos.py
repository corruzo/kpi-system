"""NaN e Infinity no son datos válidos: se rechazan en la entrada, antes de llegar a la base."""
import json

import pytest
from conftest import crear_area, entrar, ficha_base

CABECERA = {"Content-Type": "application/json"}


def _crudo(client, ruta, cuerpo: dict):
    return client.post(ruta, content=json.dumps(cuerpo, allow_nan=True), headers=CABECERA)


@pytest.mark.parametrize("campo", ["meta", "limite", "meta_tope", "limite_tope"])
@pytest.mark.parametrize("malo", [float("nan"), float("inf"), float("-inf")])
def test_ficha_rechaza_numeros_no_finitos(client, campo, malo):
    area = crear_area(client)
    entrar(client, "admin", "clave-admin-123")
    assert _crudo(client, "/api/indicadores", ficha_base(area, **{campo: malo})).status_code == 422


def test_ficha_con_numeros_normales_sigue_funcionando(client):
    area = crear_area(client)
    entrar(client, "admin", "clave-admin-123")
    assert client.post("/api/indicadores", json=ficha_base(area)).status_code == 201


def test_variable_y_constante_rechazan_nan(client):
    area = crear_area(client)
    entrar(client, "admin", "clave-admin-123")
    ficha = ficha_base(area)
    ficha["variables"][0]["defecto"] = float("nan")
    assert _crudo(client, "/api/indicadores", ficha).status_code == 422


def test_calcular_rechaza_valores_no_finitos(client):
    entrar(client, "admin", "clave-admin-123")
    assert _crudo(client, "/api/calcular", {"indicador_id": 1, "valores": {"x": float("inf")}}).status_code == 422
    assert _crudo(client, "/api/formula/probar", {"formula": "a", "valores": {"a": float("nan")}, "meta": 1, "limite": 1,
                                                  "sentido": "mayor"}).status_code == 422
