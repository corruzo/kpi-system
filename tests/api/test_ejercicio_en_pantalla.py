"""Cada pantalla trabaja con UN ejercicio fiscal: los períodos y pendientes de otros ejercicios no se mezclan."""
from contextlib import contextmanager
from datetime import date, datetime

from conftest import entrar

from app.database import SessionLocal
from app.dominio import calendario
from app.models import Indicador


@contextmanager
def _antiguo(indicador_id: int):
    """El indicador existe desde antes (un indicador nuevo no debe períodos anteriores a su creación); se restablece
    al terminar para no alterar los faltantes que ven las demás pruebas."""
    with SessionLocal() as db:
        ind = db.get(Indicador, indicador_id)
        original, ind.creado_en = ind.creado_en, datetime(2020, 1, 1)
        db.commit()
    try:
        yield
    finally:
        with SessionLocal() as db:
            db.get(Indicador, indicador_id).creado_en = original
            db.commit()


def test_los_periodos_ofrecidos_son_solo_los_del_ejercicio_pedido(client, escenario):
    ind = escenario["indicador"]["id"]
    entrar(client, escenario["jefe"])
    vigente = calendario.ejercicio_de_fecha(date.today())
    for anio in (vigente, vigente - 1):
        r = client.get(f"/api/indicadores/{ind}/periodos?ejercicio={anio}").json()
        assert r["ejercicio"] == anio
        assert {p["ejercicio"] for p in r["periodos"]} == {calendario.etiqueta_ejercicio(anio)}
    assert len(client.get(f"/api/indicadores/{ind}/periodos?ejercicio={vigente - 1}").json()["periodos"]) == 12   # ya terminó
    sin_ejercicio = client.get(f"/api/indicadores/{ind}/periodos").json()
    assert sin_ejercicio["ejercicio"] == vigente                                                                      # por defecto, el vigente


def test_no_se_ofrecen_periodos_futuros_y_solo_uno_es_el_actual(client, escenario):
    ind = escenario["indicador"]["id"]
    entrar(client, escenario["jefe"])
    r = client.get(f"/api/indicadores/{ind}/periodos").json()
    codigos = [p["periodo"] for p in r["periodos"]]
    assert all(not calendario.es_futuro("mensual", c, date.today()) for c in codigos)
    assert [p["periodo"] for p in r["periodos"] if p["actual"]] == [calendario.periodo_actual("mensual", date.today())] or \
        calendario.ejercicio_de_fecha(date.today()) != r["ejercicio"]
    futuro = client.get(f"/api/indicadores/{ind}/periodos?ejercicio={calendario.ejercicio_de_fecha(date.today()) + 1}").json()
    assert futuro["periodos"] == []


def test_los_pendientes_se_separan_por_ejercicio(client, escenario):
    ind = escenario["indicador"]["id"]
    with _antiguo(ind):
        entrar(client, escenario["jefe"])
        hoy, vigente = date.today(), calendario.ejercicio_de_fecha(date.today())
        todos = calendario.periodos_pendientes("mensual", hoy, {})
        for anio in (vigente, vigente - 1):
            fila = next(i for i in client.get(f"/api/indicadores?ejercicio={anio}").json() if i["id"] == ind)
            aqui = [p for p in todos if calendario.ejercicio_de("mensual", p) == anio]
            assert [p["periodo"] for p in fila["pendientes"]] == aqui
            assert sum(o["n"] for o in fila["pendientes_otros"]) == len(todos) - len(aqui)
            assert all(o["ejercicio"] != anio for o in fila["pendientes_otros"])


def test_cada_carga_informa_su_ejercicio(client, escenario):
    ind = escenario["indicador"]["id"]
    entrar(client, escenario["jefe"])
    periodo = calendario.periodo_actual("mensual", date.today())
    client.post("/api/mediciones", json={"indicador_id": ind, "periodo": periodo, "valores": {"dias": 1, "tickets": 1}})
    m = next(m for m in client.get("/api/mediciones").json() if m["indicador_id"] == ind)
    assert m["ejercicio"] == calendario.ejercicio_de("mensual", periodo)
    assert m["ejercicio_etiqueta"] == calendario.etiqueta_ejercicio(m["ejercicio"])
