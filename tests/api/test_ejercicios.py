from datetime import date

from conftest import crear_area, crear_indicador, crear_usuario, entrar

from app.dominio import calendario


def test_ejercicio_vigente_no_se_cierra_antes_de_terminar(client):
    entrar(client, "admin", "clave-admin-123")
    vigente = client.get("/api/ejercicios").json()["vigente"]
    assert vigente == calendario.ejercicio_de_fecha(date.today())
    assert client.post(f"/api/ejercicios/{vigente}/cerrar", json={}).status_code == 422


def test_cierre_bloquea_cargas_y_la_reapertura_las_permite(client):
    area = crear_area(client)
    ind = crear_indicador(client, area, formula="ok / total * 100", sentido="mayor", meta=98, limite=95, unidad="%",
                          variables=[{"clave": "ok", "etiqueta": "Conformes"}, {"clave": "total", "etiqueta": "Analizados"}])
    anio = calendario.ejercicio_de_fecha(date.today()) - 1
    periodo = calendario.codigo("mensual", calendario.limites(anio)[0])
    cuerpo = {"indicador_id": ind["id"], "periodo": periodo, "valores": {"ok": 99, "total": 100}}
    entrar(client, "admin", "clave-admin-123")
    assert client.get(f"/api/ejercicios/{anio}/verificacion").json()["puede_cerrar"]
    assert client.post(f"/api/ejercicios/{anio}/cerrar", json={"nota": "Cierre de prueba"}).json()["estado"] == "cerrado"
    assert client.post(f"/api/ejercicios/{anio}/cerrar", json={}).status_code == 409
    assert client.post("/api/mediciones", json=cuerpo).status_code == 409           # solo lectura
    assert client.put("/api/parametros", json={"empresa": "TT", "gerencia_emisora": "", "codigo_formato": "",
                                               "ejercicio_inicio": 1}).status_code == 409
    assert client.post(f"/api/ejercicios/{anio}/reabrir", json={"nota": "x"}).status_code == 422
    assert client.post(f"/api/ejercicios/{anio}/reabrir", json={"nota": "Corrección autorizada"}).json()["estado"] == "terminado"
    assert client.post("/api/mediciones", json=cuerpo).status_code == 201


def test_permisos_sobre_ejercicios(client):
    entrar(client, crear_usuario(client, "gerente"))
    assert client.get("/api/ejercicios?detalle=1").status_code == 200
    assert client.post("/api/ejercicios/2020/cerrar", json={}).status_code == 403
    entrar(client, crear_usuario(client, "jefe", crear_area(client)))
    assert client.get("/api/ejercicios?detalle=1").status_code == 403


def test_dashboard_por_ejercicio(client, escenario):
    entrar(client, escenario["gerente"])
    d = client.get("/api/dashboard").json()
    assert {"ejercicio", "resumen", "por_area", "indicadores", "atencion", "anterior"} <= d.keys()
    assert len(d["ejercicio"]["meses"]) == 12
    assert all(len(i["celdas"]) == 12 for i in d["indicadores"])
    anterior = client.get(f"/api/dashboard?ejercicio={d['ejercicio']['anio'] - 1}").json()
    assert anterior["ejercicio"]["anio"] == d["ejercicio"]["anio"] - 1
