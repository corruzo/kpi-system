from conftest import crear_area, crear_indicador, entrar, ficha_base, periodo_actual


def test_formula_con_variables_inexistentes_o_nombres_reservados_se_rechaza(client, escenario):
    entrar(client, "admin", "clave-admin-123")
    area = escenario["area"]
    assert client.post("/api/indicadores", json=ficha_base(area, formula="dias / 0 + noexiste")).status_code == 422
    reservada = ficha_base(area, formula="si", variables=[{"clave": "si", "etiqueta": "Reservada"}])
    assert client.post("/api/indicadores", json=reservada).status_code == 422


def test_formula_con_constantes_y_variable_opcional(client):
    area = crear_area(client)
    ficha = ficha_base(
        area, unidad="índice", frecuencia="anual", decimales=3, meta=5, limite=10,
        formula="si(horas > 0, accidentes × factor ÷ horas, 0) + extra",
        variables=[{"clave": "accidentes", "etiqueta": "Accidentes"}, {"clave": "horas", "etiqueta": "Horas-hombre"},
                   {"clave": "extra", "etiqueta": "Ajuste", "opcional": True, "defecto": 1, "negativo": True}],
        constantes=[{"clave": "factor", "etiqueta": "Factor por millón", "valor": 1000000}])
    ind = crear_indicador(client, area, **{k: v for k, v in ficha.items() if k not in ("codigo", "area_id")})
    assert ind["frecuencia"] == "anual" and ind["decimales"] == 3
    sin_horas = client.post("/api/calcular", json={"indicador_id": ind["id"],
                                                    "valores": {"accidentes": 2, "horas": 0, "extra": None}}).json()
    assert sin_horas["ok"] and sin_horas["resultado"] == 1.0                    # rama protegida + valor por defecto
    normal = client.post("/api/calcular", json={"indicador_id": ind["id"],
                                                 "valores": {"accidentes": 2, "horas": 400000, "extra": -0.5}}).json()
    assert normal["resultado"] == 4.5 and normal["semaforo"] == "verde"
    periodo = periodo_actual(client, ind["id"], 1)
    r = client.post("/api/mediciones", json={"indicador_id": ind["id"], "periodo": periodo,
                                             "valores": {"accidentes": 2, "horas": 400000, "extra": -0.5}})
    assert r.status_code == 201
    assert r.json()["formula"].startswith("si(") and r.json()["constantes"][0]["valor"] == 1000000


def test_probar_y_validar_formulas_sin_guardar(client):
    entrar(client, "admin", "clave-admin-123")
    prueba = client.post("/api/formula/probar", json={"formula": "ok / total * 100", "valores": {"ok": 99, "total": 100},
                                                       "meta": 98, "limite": 95, "sentido": "mayor"}).json()
    assert prueba["ok"] and prueba["semaforo"] == "verde"
    r = client.post("/api/formula/validar", json={"formula": "ok * 2", "claves": ["ok", "total"]})
    assert r.json()["sin_usar"] == ["total"]


def test_con_cargas_la_ficha_no_cambia_frecuencia_ni_claves(client, escenario):
    ind = escenario["indicador"]
    entrar(client, escenario["jefe"])
    periodo = periodo_actual(client, ind["id"])
    assert client.post("/api/mediciones", json={"indicador_id": ind["id"], "periodo": periodo,
                                                "valores": {"dias": 2, "tickets": 1}}).status_code == 201
    entrar(client, "admin", "clave-admin-123")
    ficha = next(i for i in client.get("/api/indicadores").json() if i["id"] == ind["id"])
    assert ficha["n_mediciones"] == 1
    base = {k: ficha[k] for k in ("codigo", "nombre", "objetivo", "area_id", "unidad", "sentido", "formula",
                                  "variables", "meta", "limite", "activo")}
    assert client.put(f"/api/indicadores/{ind['id']}", json={**base, "frecuencia": "trimestral"}).status_code == 422
    nuevas = [{"clave": "dias", "etiqueta": "Días"}, {"clave": "tk", "etiqueta": "Tickets"}]
    assert client.put(f"/api/indicadores/{ind['id']}", json={**base, "frecuencia": "mensual", "variables": nuevas,
                                                             "formula": "dias / tk"}).status_code == 422
    assert client.put(f"/api/indicadores/{ind['id']}", json={**base, "frecuencia": "mensual", "meta": 3}).status_code == 200


def test_eliminar_un_indicador_con_cargas_lo_archiva(client, escenario):
    ind = escenario["indicador"]
    entrar(client, escenario["jefe"])
    client.post("/api/mediciones", json={"indicador_id": ind["id"], "periodo": periodo_actual(client, ind["id"]),
                                         "valores": {"dias": 2, "tickets": 1}})
    entrar(client, "admin", "clave-admin-123")
    assert client.delete(f"/api/indicadores/{ind['id']}").json()["archivado"] is True


def test_un_indicador_recien_creado_no_tiene_meses_pendientes(client, escenario):
    entrar(client, escenario["jefe"])
    ind = next(i for i in client.get("/api/indicadores").json() if i["id"] == escenario["indicador"]["id"])
    assert ind["pendientes"] == []
