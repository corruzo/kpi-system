from conftest import crear_area, crear_indicador, entrar, periodo_actual


def cuerpo(escenario, periodo, dias=300, tickets=50, **extra):
    return {"indicador_id": escenario["indicador"]["id"], "periodo": periodo, "valores": {"dias": dias, "tickets": tickets}, **extra}


def test_fuera_de_meta_exige_analisis_y_plan(client, escenario):
    entrar(client, escenario["jefe"])
    periodo = periodo_actual(client, escenario["indicador"]["id"])
    assert client.post("/api/mediciones", json=cuerpo(escenario, periodo)).status_code == 422
    r = client.post("/api/mediciones", json=cuerpo(escenario, periodo, analisis="Caída del enlace", plan_mejora="Enlace de respaldo"))
    assert r.status_code == 201 and r.json()["semaforo"] == "rojo"


def test_dentro_de_meta_no_exige_analisis_y_no_se_duplica(client, escenario):
    entrar(client, escenario["jefe"])
    periodo = periodo_actual(client, escenario["indicador"]["id"])
    assert client.post("/api/mediciones", json=cuerpo(escenario, periodo, dias=10, tickets=10)).json()["semaforo"] == "verde"
    assert client.post("/api/mediciones", json=cuerpo(escenario, periodo, dias=10, tickets=10)).status_code == 409


def test_revision_observar_corregir_y_aprobar(client, escenario):
    entrar(client, escenario["jefe"])
    periodo = periodo_actual(client, escenario["indicador"]["id"])
    mid = client.post("/api/mediciones", json=cuerpo(escenario, periodo, dias=10, tickets=10)).json()["id"]
    entrar(client, escenario["gerente"])
    assert client.post(f"/api/mediciones/{mid}/revision", json={"accion": "observar"}).status_code == 422   # exige nota
    assert client.post(f"/api/mediciones/{mid}/revision", json={"accion": "observar", "nota": "Falta fecha"}).status_code == 200
    entrar(client, escenario["jefe"])
    assert client.post("/api/mediciones", json=cuerpo(escenario, periodo, dias=10, tickets=10)).json()["version"] == 2
    entrar(client, escenario["gerente"])
    assert client.post(f"/api/mediciones/{mid}/revision", json={"accion": "aprobar"}).json()["estado"] == "aprobado"
    assert client.post(f"/api/mediciones/{mid}/notas", json={"texto": "Verificar eficacia"}).status_code == 201


def test_reabrir_una_carga_aprobada_solo_lo_hace_la_gerencia(client, escenario):
    entrar(client, escenario["jefe"])
    mid = client.post("/api/mediciones", json=cuerpo(escenario, periodo_actual(client, escenario["indicador"]["id"]),
                                                      dias=10, tickets=10)).json()["id"]
    entrar(client, escenario["gerente"])
    client.post(f"/api/mediciones/{mid}/revision", json={"accion": "aprobar"})
    assert client.post(f"/api/mediciones/{mid}/reabrir", json={"accion": "observar"}).status_code == 422
    r = client.post(f"/api/mediciones/{mid}/reabrir", json={"accion": "observar", "nota": "Dato digitado mal"})
    assert r.status_code == 200 and r.json()["estado"] == "observado"
    entrar(client, escenario["jefe"])
    assert client.post(f"/api/mediciones/{mid}/reabrir", json={"accion": "observar", "nota": "no puedo"}).status_code == 403


def test_un_jefe_no_ve_ni_carga_indicadores_de_otra_area(client, escenario):
    otra = crear_area(client)
    ajeno = crear_indicador(client, otra)
    entrar(client, escenario["jefe"])
    assert client.post("/api/calcular", json={"indicador_id": ajeno["id"], "valores": {}}).status_code in (403, 404)
    assert client.get("/api/dashboard").status_code == 403


def test_el_administrador_carga_pero_no_aprueba_lo_propio(client, escenario):
    entrar(client, "admin", "clave-admin-123")
    periodo = periodo_actual(client, escenario["indicador"]["id"], 1)
    r = client.post("/api/mediciones", json=cuerpo(escenario, periodo, dias=10, tickets=10))
    assert r.status_code == 201
    assert client.post(f"/api/mediciones/{r.json()['id']}/revision", json={"accion": "aprobar"}).status_code == 403
    entrar(client, escenario["gerente"])
    assert client.post(f"/api/mediciones/{r.json()['id']}/revision", json={"accion": "aprobar"}).status_code == 200
