"""Aislamiento estricto: un encargado de proceso NUNCA ve información de otro usuario, ni siquiera de su misma área."""
from io import BytesIO

import pytest
from conftest import (
    CLAVE_ADMIN,
    crear_area,
    crear_indicador,
    crear_usuario,
    entrar,
    id_de_usuario,
    periodo_actual,
)
from openpyxl import load_workbook


@pytest.fixture()
def dos_encargados(client):
    """Una sola área con dos encargados, cada uno con su indicador y una carga propia."""
    area = crear_area(client)
    a, b = crear_usuario(client, "jefe", area), crear_usuario(client, "jefe", area)
    ind_a = crear_indicador(client, area, encargado_id=id_de_usuario(client, a), nombre="Indicador SECRETO de A")
    ind_b = crear_indicador(client, area, encargado_id=id_de_usuario(client, b), nombre="Indicador SECRETO de B")
    for usuario, ind in ((a, ind_a), (b, ind_b)):
        entrar(client, usuario)
        r = client.post("/api/mediciones", json={"indicador_id": ind["id"], "periodo": periodo_actual(client, ind["id"]),
                                                 "valores": {"dias": 10, "tickets": 5}, "analisis": "x" * 300, "plan_mejora": "y " * 150})
        assert r.status_code == 201, r.text
    return {"a": a, "b": b, "ind_a": ind_a, "ind_b": ind_b, "area": area}


def test_cada_encargado_ve_solo_sus_indicadores_aunque_comparta_area(client, dos_encargados):
    d = dos_encargados
    entrar(client, d["a"])
    ids = {i["id"] for i in client.get("/api/indicadores").json()}
    assert d["ind_a"]["id"] in ids and d["ind_b"]["id"] not in ids
    entrar(client, d["b"])
    ids = {i["id"] for i in client.get("/api/indicadores").json()}
    assert d["ind_b"]["id"] in ids and d["ind_a"]["id"] not in ids


def test_el_indicador_ajeno_responde_404_en_todas_las_rutas(client, dos_encargados):
    d = dos_encargados
    ajeno = d["ind_b"]["id"]
    entrar(client, d["a"])
    ficha = {"indicador_id": ajeno, "valores": {"dias": 1, "tickets": 1}}
    for r in (client.get(f"/api/indicadores/{ajeno}/periodos"), client.get(f"/api/indicadores/{ajeno}/ficha"),
              client.post("/api/calcular", json=ficha),
              client.post("/api/mediciones", json={**ficha, "periodo": periodo_actual(client, d["ind_a"]["id"]), "analisis": "", "plan_mejora": ""}),
              client.get(f"/api/reportes/fichas.xlsx?indicador_id={ajeno}")):
        assert r.status_code == 404, (r.request.url, r.status_code)
        assert "SECRETO" not in r.text


def test_las_cargas_y_los_reportes_no_filtran_datos_de_otro_encargado(client, dos_encargados):
    d = dos_encargados
    entrar(client, d["a"])
    cargas = client.get("/api/mediciones").json()
    assert {m["indicador_id"] for m in cargas} == {d["ind_a"]["id"]}
    assert client.get(f"/api/mediciones?indicador_id={d['ind_b']['id']}").json() == []
    assert client.get(f"/api/mediciones?area_id={d['area']}").json() == cargas   # filtrar por área no amplía el acceso
    for url in (f"/api/reportes/general.xlsx?area_id={d['area']}", "/api/reportes/fichas.xlsx"):
        r = client.get(url)
        assert r.status_code == 200
        celdas = " ".join(str(c.value) for hoja in load_workbook(BytesIO(r.content)) for fila in hoja.iter_rows() for c in fila if c.value)
        assert "SECRETO de A" in celdas and d["ind_b"]["codigo"] not in celdas and "SECRETO de B" not in celdas


def test_un_encargado_no_accede_a_funciones_de_otros_roles(client, dos_encargados):
    entrar(client, dos_encargados["a"])
    for metodo, url in (("get", "/api/usuarios"), ("get", "/api/bitacora"), ("get", "/api/tablero"), ("get", "/api/dashboard"),
                        ("get", "/api/ejercicios?detalle=true"), ("get", "/api/ejercicios/2026/metas"),
                        ("get", "/api/indicadores/codigo-sugerido?area_id=1"), ("get", "/api/puesta-en-marcha")):
        assert getattr(client, metodo)(url).status_code == 403, url


def test_gerente_y_admin_ven_todo_y_el_archivado_solo_el_admin(client, dos_encargados):
    d = dos_encargados
    gerente = crear_usuario(client, "gerente")
    entrar(client, gerente)
    assert {d["ind_a"]["id"], d["ind_b"]["id"]} <= {i["id"] for i in client.get("/api/indicadores").json()}
    entrar(client, "admin", CLAVE_ADMIN)
    assert client.delete(f"/api/indicadores/{d['ind_a']['id']}").json()["archivado"] is True   # tiene carga: se archiva
    entrar(client, d["a"])
    assert client.get("/api/indicadores").json() == []
    assert client.get(f"/api/indicadores/{d['ind_a']['id']}/ficha").status_code == 404


def test_la_asignacion_exige_un_encargado_valido_y_protege_su_cuenta(client):
    area, otra = crear_area(client), crear_area(client)
    enc, ajeno, gerente = crear_usuario(client, "jefe", area), crear_usuario(client, "jefe", otra), crear_usuario(client, "gerente")
    entrar(client, "admin", CLAVE_ADMIN)
    from conftest import ficha_base
    for malo in (id_de_usuario(client, ajeno), id_de_usuario(client, gerente), 99999):   # otra área, otro rol, inexistente
        assert client.post("/api/indicadores", json=ficha_base(area, encargado_id=malo)).status_code == 422 \
            or client.post("/api/indicadores", json=ficha_base(area, encargado_id=malo)).status_code == 400
    ind = client.post("/api/indicadores", json=ficha_base(area, encargado_id=id_de_usuario(client, enc))).json()
    uid = id_de_usuario(client, enc)
    cambio = client.put(f"/api/usuarios/{uid}", json={"nombre": "Nombre nuevo", "rol": "jefe", "area_id": area, "activo": False})
    assert cambio.status_code == 409 and "reasígnelos" in cambio.json()["detail"]
    assert client.delete(f"/api/usuarios/{uid}").status_code == 409
    assert ind["encargado_id"] == uid


def test_el_codigo_lo_genera_el_sistema_y_no_se_puede_cambiar(client):
    from conftest import ficha_base
    area = crear_area(client, "Calidad y Mejora")
    entrar(client, "admin", CLAVE_ADMIN)
    sugerido = client.get(f"/api/indicadores/codigo-sugerido?area_id={area}").json()["codigo"]
    ficha = ficha_base(area)
    ficha["codigo"] = ""
    r1 = client.post("/api/indicadores", json=ficha)
    assert r1.status_code == 201 and r1.json()["codigo"] == sugerido == "CAL-01"
    r2 = client.post("/api/indicadores", json=ficha)
    assert r2.json()["codigo"] == "CAL-02"
    editado = client.put(f"/api/indicadores/{r1.json()['id']}", json={**ficha, "codigo": "OTRO-99"})
    assert editado.json()["codigo"] == "CAL-01"
    assert client.post("/api/indicadores", json={**ficha, "codigo": "CAL-01"}).status_code in (400, 409, 422)


def test_las_respuestas_de_la_api_no_se_guardan_en_cache_y_varian_por_sesion(client, dos_encargados):
    entrar(client, dos_encargados["a"])
    r = client.get("/api/indicadores")
    assert r.headers["cache-control"] == "no-store" and "Cookie" in r.headers["vary"]


def test_toda_ruta_de_la_api_exige_sesion_salvo_las_publicas(client):
    from app.main import app
    publicas = {"/api/login", "/api/publico", "/api/logo"}
    client.cookies.clear()
    for ruta in app.routes:
        path = getattr(ruta, "path", "")
        if not path.startswith("/api/") or path in publicas or path.startswith("/api/docs"):
            continue
        for metodo in ruta.methods - {"HEAD", "OPTIONS"}:
            url = path.replace("{indicador_id}", "1").replace("{medicion_id}", "1").replace("{usuario_id}", "1") \
                .replace("{area_id}", "1").replace("{anio}", "2026").replace("{elemento_id}", "1")
            r = client.request(metodo, url, headers={"Origin": "http://testserver"})
            assert r.status_code in (401, 403), f"{metodo} {path} → {r.status_code}"


def test_el_arranque_entrega_a_cada_rol_solo_lo_suyo_en_una_peticion(client, dos_encargados):
    d = dos_encargados
    entrar(client, d["a"])
    r = client.get("/api/arranque").json()
    assert {i["id"] for i in r["indicadores"]} == {d["ind_a"]["id"]}
    assert "areas" not in r and "usuarios" not in r and "catalogos" not in r and "bandeja" not in r
    assert r["usuario"]["username"] == d["a"] and r["ejercicio"] in {e["anio"] for e in r["ejercicios"]["ejercicios"]}
    entrar(client, "admin", CLAVE_ADMIN)
    r = client.get("/api/arranque").json()
    assert {"usuario", "parametros", "ejercicios", "ejercicio", "indicadores", "areas", "bandeja_total", "bandeja_ejercicios",
            "catalogos"} <= r.keys()
    assert "usuarios" not in r and "bandeja" not in r   # las listas largas se piden paginadas, no en el arranque
    assert {d["ind_a"]["id"], d["ind_b"]["id"]} <= {i["id"] for i in r["indicadores"]}
    client.cookies.clear()
    assert client.get("/api/arranque").status_code == 401
