"""Flujo anual: período fiscal → presupuesto → carga mensual comparada con lo presupuestado."""
from datetime import date

from conftest import CLAVE_ADMIN, crear_area, crear_indicador, crear_periodo, crear_usuario, entrar, periodo_actual

from app.dominio import calendario


def vigente() -> int:
    return calendario.ejercicio_de_fecha(date.today())


def preparar(client, **cambios):
    """Área, jefe, gerente e indicador SIN presupuestar."""
    area = crear_area(client)
    return {"area": area, "jefe": crear_usuario(client, "jefe", area), "gerente": crear_usuario(client, "gerente"),
            "indicador": crear_indicador(client, area, presupuesto=False, **cambios)}


def carga(esc, periodo, dias=10, tickets=10):
    return {"indicador_id": esc["indicador"]["id"], "periodo": periodo, "valores": {"dias": dias, "tickets": tickets}}


def test_sin_periodo_fiscal_no_se_presupuesta_ni_se_carga(client):
    esc = preparar(client)
    entrar(client, "admin", CLAVE_ADMIN)
    anio = 2099
    r = client.put(f"/api/ejercicios/{anio}/presupuesto/{esc['indicador']['id']}", json={"anual": 2, "reparto": "repetir"})
    assert r.status_code == 409 and "no ha sido creado" in r.json()["detail"]


def test_crear_un_periodo_es_solo_del_admin_y_no_se_repite(client):
    esc = preparar(client)
    entrar(client, esc["gerente"])
    assert client.post("/api/ejercicios", json={"anio": 2098}).status_code == 403
    entrar(client, "admin", CLAVE_ADMIN)
    assert client.post("/api/ejercicios", json={"anio": 2098}).status_code == 201
    assert client.post("/api/ejercicios", json={"anio": 2098}).status_code == 409
    assert client.post("/api/ejercicios", json={"anio": 1990}).status_code == 422


def test_no_se_carga_un_periodo_sin_presupuesto(client):
    esc = preparar(client)
    crear_periodo(client, vigente())
    entrar(client, esc["jefe"])
    periodo = periodo_actual(client, esc["indicador"]["id"])
    r = client.post("/api/mediciones", json=carga(esc, periodo))
    assert r.status_code == 409 and "presupuesto" in r.json()["detail"]


def test_presupuesto_por_periodo_y_comparacion_con_el_dato_real(client):
    esc = preparar(client)
    crear_periodo(client, vigente())
    ind = esc["indicador"]["id"]
    periodos = calendario.periodos_del_ejercicio("mensual", vigente())
    entrar(client, esc["gerente"])
    r = client.put(f"/api/ejercicios/{vigente()}/presupuesto/{ind}", json={"valores": dict.fromkeys(periodos, 1.5)})
    assert r.status_code == 200 and r.json()["guardados"] == 12
    entrar(client, esc["jefe"])
    periodo = periodo_actual(client, ind)
    calc = client.post("/api/calcular", json={"indicador_id": ind, "periodo": periodo, "valores": {"dias": 10, "tickets": 10}}).json()
    assert calc["vs_presupuesto"]["presupuesto"] == 1.5 and calc["vs_presupuesto"]["cumple"] is True   # 1 día ≤ 1,5 (menor es mejor)
    m = client.post("/api/mediciones", json={**carga(esc, periodo, dias=30, tickets=10), "analisis": "Retraso del proveedor", "plan_mejora": "Segundo proveedor"}).json()   # resultado 3 > 1,5
    assert m["presupuesto"] == 1.5 and m["vs_presupuesto"]["cumple"] is False and m["vs_presupuesto"]["desviacion"] == 1.5
    assert m["vs_presupuesto"]["porcentaje"] == 200.0


def test_valor_anual_se_reparte_igual_o_se_repite(client):
    esc = preparar(client, unidad="TM", sentido="mayor", meta=100, limite=50)
    crear_periodo(client, vigente())
    ind = esc["indicador"]["id"]
    entrar(client, esc["gerente"])
    assert client.put(f"/api/ejercicios/{vigente()}/presupuesto/{ind}", json={"anual": 1200, "reparto": "igual"}).status_code == 200
    fila = next(i for i in client.get(f"/api/ejercicios/{vigente()}/presupuesto").json()["indicadores"] if i["indicador_id"] == ind)
    assert [p["valor"] for p in fila["periodos"]] == [100.0] * 12 and fila["completo"]


def test_un_periodo_ya_cargado_no_admite_cambiar_su_presupuesto(client):
    esc = preparar(client)
    crear_periodo(client, vigente())
    ind = esc["indicador"]["id"]
    entrar(client, "admin", CLAVE_ADMIN)
    client.put(f"/api/ejercicios/{vigente()}/presupuesto/{ind}", json={"anual": 2, "reparto": "repetir"})
    entrar(client, esc["jefe"])
    periodo = periodo_actual(client, ind)
    assert client.post("/api/mediciones", json=carga(esc, periodo)).status_code == 201
    entrar(client, "admin", CLAVE_ADMIN)
    r = client.put(f"/api/ejercicios/{vigente()}/presupuesto/{ind}", json={"valores": {periodo: 9}})
    assert r.status_code == 409 and "ya tiene dato real" in r.json()["detail"]


def test_periodos_ajenos_a_la_frecuencia_se_rechazan_y_el_jefe_no_presupuesta(client):
    esc = preparar(client, frecuencia="trimestral")
    crear_periodo(client, vigente())
    ind = esc["indicador"]["id"]
    entrar(client, esc["jefe"])
    assert client.put(f"/api/ejercicios/{vigente()}/presupuesto/{ind}", json={"anual": 1}).status_code == 403
    entrar(client, "admin", CLAVE_ADMIN)
    assert client.put(f"/api/ejercicios/{vigente()}/presupuesto/{ind}", json={"valores": {f"{vigente()}-03": 1}}).status_code == 422
    assert client.put(f"/api/ejercicios/{vigente()}/presupuesto/{ind}", json={"anual": 3, "reparto": "repetir"}).status_code == 200
    fila = next(i for i in client.get(f"/api/ejercicios/{vigente()}/presupuesto").json()["indicadores"] if i["indicador_id"] == ind)
    assert len(fila["periodos"]) == 4


def test_los_cambios_de_presupuesto_quedan_en_la_bitacora(client):
    esc = preparar(client)
    crear_periodo(client, vigente())
    entrar(client, "admin", CLAVE_ADMIN)
    client.put(f"/api/ejercicios/{vigente()}/presupuesto/{esc['indicador']['id']}", json={"anual": 2, "reparto": "repetir"})
    acciones = {b["accion"] for b in client.get("/api/bitacora?limite=50").json()}
    assert {"EJERCICIO_CREADO", "PRESUPUESTO_GUARDADO"} & acciones


def test_copiar_el_presupuesto_de_otro_ejercicio(client):
    esc = preparar(client)
    ind = esc["indicador"]["id"]
    crear_periodo(client, vigente() - 1)
    crear_periodo(client, vigente())
    entrar(client, "admin", CLAVE_ADMIN)
    client.put(f"/api/ejercicios/{vigente() - 1}/presupuesto/{ind}", json={"anual": 7, "reparto": "repetir"})
    r = client.post(f"/api/ejercicios/{vigente()}/presupuesto/copiar", json={"desde": vigente() - 1})
    assert r.status_code == 200 and r.json()["indicadores"] >= 1
    fila = next(i for i in client.get(f"/api/ejercicios/{vigente()}/presupuesto").json()["indicadores"] if i["indicador_id"] == ind)
    assert {p["valor"] for p in fila["periodos"]} == {7}


def test_puesta_en_marcha_informa_cada_paso(client):
    entrar(client, "admin", CLAVE_ADMIN)
    r = client.get("/api/puesta-en-marcha").json()
    assert [p["id"] for p in r["pasos"]] == ["org", "fichas", "periodo", "presupuesto", "carga"]
    entrar(client, crear_usuario(client, "gerente"))
    assert client.get("/api/puesta-en-marcha").status_code == 403
