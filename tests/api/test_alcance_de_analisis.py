"""Panel, tablero, reportes Excel, metas y arranque solo incluyen lo visible para quien los pide."""
from io import BytesIO

from conftest import entrar, periodo_actual
from openpyxl import load_workbook
from test_jerarquia import empresa  # noqa: F401  (fixture compartida)


def _celdas(contenido: bytes) -> str:
    return " ".join(str(c.value) for hoja in load_workbook(BytesIO(contenido)) for fila in hoja.iter_rows() for c in fila if c.value)


def _cargar(client, usuario, ind):
    entrar(client, usuario)
    r = client.post("/api/mediciones", json={"indicador_id": ind["id"], "periodo": periodo_actual(client, ind["id"]),
                                             "valores": {"dias": 1, "tickets": 1}})
    assert r.status_code == 201, r.text


def test_el_panel_y_el_tablero_filtran_por_ambito(client, empresa):  # noqa: F811
    ind = empresa["ind"]
    _cargar(client, empresa["analista"], ind["jefatura"])
    _cargar(client, empresa["g_prod"], ind["prod"])
    entrar(client, empresa["g_rrhh"])
    visibles = {i["id"] for i in client.get("/api/indicadores").json()}
    tablero = client.get("/api/tablero").json()
    assert {i["id"] for i in tablero["indicadores"]} == visibles and ind["prod"]["id"] not in visibles
    assert ind["jefatura"]["id"] in {i["id"] for i in tablero["indicadores"]}
    panel = client.get("/api/dashboard").json()
    assert {i["id"] for i in panel["indicadores"]} == visibles
    assert sum(a["total"] for a in panel["por_area"]) == len(visibles)
    entrar(client, empresa["gg"])                                   # el gerente general ve todo
    assert {ind["prod"]["id"], ind["jefatura"]["id"]} <= {i["id"] for i in client.get("/api/tablero").json()["indicadores"]}


def test_los_excel_solo_incluyen_lo_visible(client, empresa):  # noqa: F811
    ind = empresa["ind"]
    entrar(client, empresa["g_rrhh"])
    for url in ("/api/reportes/general.xlsx", "/api/reportes/fichas.xlsx"):
        r = client.get(url)
        assert r.status_code == 200
        texto = _celdas(r.content)
        assert ind["gerente"]["codigo"] in texto and ind["prod"]["codigo"] not in texto, url
    entrar(client, empresa["jefe2"])                                # dos jefaturas: solo esas dos
    texto = _celdas(client.get("/api/reportes/general.xlsx").content)
    assert ind["jefatura"]["codigo"] in texto and ind["jefatura2"]["codigo"] in texto
    assert ind["gerente"]["codigo"] not in texto and ind["sst"]["codigo"] not in texto
    assert client.get(f"/api/reportes/fichas.xlsx?indicador_id={ind['gerente']['id']}").status_code == 404


def test_la_matriz_de_metas_solo_muestra_lo_visible_y_marca_lo_editable(client, empresa):  # noqa: F811
    from app.dominio import calendario
    ind, anio = empresa["ind"], calendario.ejercicio_de_fecha(calendario.hoy())
    entrar(client, empresa["g_rrhh"])
    filas = {f["indicador_id"]: f for f in client.get(f"/api/ejercicios/{anio}/metas").json()["indicadores"]}
    assert ind["prod"]["id"] not in filas and ind["jefatura"]["id"] in filas
    assert filas[ind["gerente"]["id"]]["editable"] and filas[ind["jefatura"]["id"]]["editable"]   # propio y de quien está debajo
    assert not filas[ind["del_par"]["id"]]["editable"]                                         # de un par: lo ve, no lo fija
    entrar(client, empresa["gg"])                                   # solo ve (sin metas.cargar): nada editable
    assert not any(f["editable"] for f in client.get(f"/api/ejercicios/{anio}/metas").json()["indicadores"])


def test_los_recordatorios_y_el_arranque_se_limitan_al_ambito(client, empresa):  # noqa: F811
    ind = empresa["ind"]
    entrar(client, empresa["g_rrhh"])
    r = client.get("/api/recordatorios").json()
    assert all(i["indicador_id"] != ind["prod"]["id"] for p in r["personas"] for i in p["indicadores"])
    arranque = client.get("/api/arranque").json()
    assert {u["id"] for u in arranque["unidades"]} >= {empresa["rrhh"]["gerencia"], empresa["rrhh"]["jefatura"]}
    assert empresa["prod"]["gerencia"] not in {u["id"] for u in arranque["unidades"]}
    assert {i["id"] for i in arranque["indicadores"]} == {i["id"] for i in client.get("/api/indicadores?cargables=true").json()}
    assert arranque["resumen"]["total"] == len(client.get("/api/indicadores").json())
