import os
import tempfile

os.environ["SIGT_DATA_DIR"] = tempfile.mkdtemp()

import pytest
from fastapi.testclient import TestClient

from app import calc
from app.main import app

CLAVE = "tripoliven2026"


def test_semaforo_directo_e_inverso():
    assert calc.semaforo(95, 90, 80, "mayor") == "verde"
    assert calc.semaforo(85, 90, 80, "mayor") == "amarillo"
    assert calc.semaforo(70, 90, 80, "mayor") == "rojo"
    assert calc.semaforo(2, 3, 5, "menor") == "verde"
    assert calc.semaforo(4, 3, 5, "menor") == "amarillo"
    assert calc.semaforo(6, 3, 5, "menor") == "rojo"


def test_formula_segura():
    assert calc.evaluar("a / b * 100", {"a": 1, "b": 4}) == 25
    with pytest.raises(calc.FormulaError):
        calc.evaluar("a / b", {"a": 1, "b": 0})
    with pytest.raises(calc.FormulaError):
        calc.validar_formula("__import__('os').system('ls')", ["a"])


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def entrar(c, user):
    assert c.post("/api/login", json={"username": user, "password": CLAVE}).status_code == 200


def test_flujo_completo(client):
    c = client
    entrar(c, "j.sistemas")
    ind = next(i for i in c.get("/api/indicadores").json() if i["codigo"] == "SIS-03")
    per = c.get(f"/api/indicadores/{ind['id']}/periodos").json()["periodos"][0]["periodo"]
    body = {"indicador_id": ind["id"], "periodo": per, "valores": {"dias_totales": 300, "tickets": 50}}
    assert c.post("/api/mediciones", json=body).status_code == 422  # fuera de meta sin análisis
    body.update(analisis="Caída del enlace principal", plan_mejora="Enlace de respaldo y turno extra")
    r = c.post("/api/mediciones", json=body)
    assert r.status_code == 201 and r.json()["semaforo"] == "rojo"
    assert c.post("/api/mediciones", json=body).status_code == 409
    entrar(c, "j.produccion")
    assert c.post("/api/calcular", json={"indicador_id": ind["id"], "valores": {}}).status_code == 403
    assert c.get("/api/dashboard").status_code == 403
    entrar(c, "gerente")
    mid = r.json()["id"]
    assert c.post(f"/api/mediciones/{mid}/revision", json={"accion": "observar"}).status_code == 422
    assert c.post(f"/api/mediciones/{mid}/revision", json={"accion": "observar", "nota": "Falta fecha"}).status_code == 200
    entrar(c, "j.sistemas")
    assert c.post("/api/mediciones", json=body).json()["version"] == 2
    entrar(c, "gerente")
    assert c.post(f"/api/mediciones/{mid}/revision", json={"accion": "aprobar"}).json()["estado"] == "aprobado"
    assert c.post(f"/api/mediciones/{mid}/notas", json={"texto": "Verificar eficacia"}).status_code == 201
    assert c.get("/api/bitacora/verificar").json()["ok"] is True


def test_admin_crud_y_bitacora_inalterable(client):
    c = client
    entrar(c, "admin")
    area = c.get("/api/areas").json()[0]["id"]
    ficha = {"codigo": "tst-01", "nombre": "Prueba", "area_id": area, "unidad": "días", "frecuencia": "trimestral",
             "sentido": "menor", "formula": "a / b", "variables": [{"clave": "a", "etiqueta": "Dato A"}, {"clave": "b", "etiqueta": "Dato B"}],
             "meta": 3, "limite": 2}
    assert c.post("/api/indicadores", json=ficha).status_code == 422
    ficha["limite"] = 5
    r = c.post("/api/indicadores", json=ficha)
    assert r.status_code == 201 and r.json()["codigo"] == "TST-01"
    assert c.delete(f"/api/indicadores/{r.json()['id']}").json()["archivado"] is False
    from app.database import SessionLocal
    from app.models import Bitacora
    with SessionLocal() as db:
        b = db.get(Bitacora, 1)
        b.accion = "X"
        with pytest.raises(RuntimeError):
            db.flush()
