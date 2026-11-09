"""Observación opcional en verde, gerente que gestiona indicadores y listas paginadas en el servidor."""
from conftest import CLAVE_ADMIN, crear_area, crear_indicador, crear_usuario, entrar, ficha_base, periodo_actual


def _carga(escenario, periodo, dias, tickets, **extra):
    return {"indicador_id": escenario["indicador"]["id"], "periodo": periodo, "valores": {"dias": dias, "tickets": tickets}, **extra}


def test_en_verde_la_observacion_es_opcional_y_se_guarda_si_se_escribe(client, escenario):
    entrar(client, escenario["jefe"])
    periodo = periodo_actual(client, escenario["indicador"]["id"])
    r = client.post("/api/mediciones", json=_carga(escenario, periodo, 10, 10, analisis="Buen mes, sin novedades"))
    assert r.status_code == 201 and r.json()["semaforo"] == "verde" and r.json()["analisis"] == "Buen mes, sin novedades"
    otro = periodo_actual(client, escenario["indicador"]["id"], 1)
    sin = client.post("/api/mediciones", json=_carga(escenario, otro, 10, 10))
    assert sin.status_code == 201 and sin.json()["analisis"] == ""


def test_en_rojo_y_amarillo_siguen_siendo_obligatorios(client, escenario):
    entrar(client, escenario["jefe"])
    periodo = periodo_actual(client, escenario["indicador"]["id"])
    assert client.post("/api/mediciones", json=_carga(escenario, periodo, 300, 50, analisis="Solo análisis")).status_code == 422
    assert client.post("/api/mediciones", json=_carga(escenario, periodo, 30, 10)).status_code == 422   # amarillo (3 días: entre 2 y 4)


def test_el_gerente_crea_edita_archiva_y_elimina_indicadores(client, escenario):
    area = escenario["area"]
    entrar(client, escenario["gerente"])
    r = client.post("/api/indicadores", json=ficha_base(area, nombre="Creado por gerencia"))
    assert r.status_code == 201, r.text
    ind = r.json()
    assert client.get(f"/api/indicadores/codigo-sugerido?area_id={area}").status_code == 200
    assert client.post("/api/formula/validar", json={"formula": "dias / tickets", "claves": ["dias", "tickets"],
                                                      "variables": ["dias", "tickets"]}).status_code == 200
    editado = client.put(f"/api/indicadores/{ind['id']}", json={**ficha_base(area, nombre="Renombrado"), "codigo": ind["codigo"]})
    assert editado.status_code == 200 and editado.json()["nombre"] == "Renombrado"
    assert client.delete(f"/api/indicadores/{ind['id']}").json() == {"ok": True, "archivado": False}   # sin cargas: se elimina
    # y la gerencia ve los archivados en la lista de gestión
    archivado = crear_indicador(client, area, presupuesto=False)
    entrar(client, "admin", CLAVE_ADMIN)
    client.put(f"/api/indicadores/{archivado['id']}", json={**ficha_base(area), "codigo": archivado["codigo"], "activo": False})
    entrar(client, escenario["gerente"])
    assert archivado["id"] not in {i["id"] for i in client.get("/api/indicadores").json()}
    assert archivado["id"] in {i["id"] for i in client.get("/api/indicadores?gestion=true").json()}


def test_el_encargado_no_gestiona_indicadores(client, escenario):
    entrar(client, escenario["jefe"])
    assert client.post("/api/indicadores", json=ficha_base(escenario["area"])).status_code == 403
    assert client.delete(f"/api/indicadores/{escenario['indicador']['id']}").status_code == 403
    assert client.get("/api/indicadores?gestion=true").json()   # «gestion» no le da más que lo suyo
    assert [i["id"] for i in client.get("/api/indicadores?gestion=true").json()] == [escenario["indicador"]["id"]]


def test_opciones_de_usuarios_para_gerente_y_admin_pero_no_para_el_encargado(client, escenario):
    entrar(client, escenario["gerente"])
    r = client.get("/api/usuarios/opciones")
    assert r.status_code == 200 and all(set(u) == {"id", "nombre", "rol", "area_id", "activo"} for u in r.json())
    assert client.get("/api/usuarios").status_code == 403   # la lista completa sigue siendo del administrador
    entrar(client, escenario["jefe"])
    assert client.get("/api/usuarios/opciones").status_code == 403


def test_bitacora_paginada_con_total(client):
    crear_area(client)
    crear_area(client)
    entrar(client, "admin", CLAVE_ADMIN)
    todo = client.get("/api/bitacora?limite=500")
    total = int(todo.headers["X-Total-Count"])
    assert total >= 3 and len(todo.json()) == min(total, 500)
    p1, p2 = client.get("/api/bitacora?limite=2&desde=0"), client.get("/api/bitacora?limite=2&desde=2")
    assert int(p1.headers["X-Total-Count"]) == total and len(p1.json()) == 2
    assert {b["id"] for b in p1.json()}.isdisjoint({b["id"] for b in p2.json()})
    filtrada = client.get("/api/bitacora?accion=AREA_CREADA&limite=1")
    assert int(filtrada.headers["X-Total-Count"]) >= 2 and len(filtrada.json()) == 1


def test_mediciones_paginadas_y_resumen_por_ejercicio(client, escenario):
    entrar(client, escenario["jefe"])
    for pos in (0, 1):
        assert client.post("/api/mediciones", json=_carga(escenario, periodo_actual(client, escenario["indicador"]["id"], pos), 10, 10)).status_code == 201
    entrar(client, escenario["gerente"])
    r = client.get("/api/mediciones?estado=enviado&limite=1")
    assert len(r.json()) == 1 and int(r.headers["X-Total-Count"]) >= 2
    resumen = client.get("/api/mediciones/resumen-ejercicios?estado=enviado").json()
    assert sum(e["n"] for e in resumen) == int(client.get("/api/mediciones?estado=enviado&limite=1").headers["X-Total-Count"])
    assert all({"ejercicio", "etiqueta", "n"} <= e.keys() for e in resumen)


def test_indicadores_y_usuarios_paginados_con_filtros_en_el_servidor(client):
    area = crear_area(client)
    nombres = [f"Paginado {k}" for k in range(3)]
    for n in nombres:
        crear_indicador(client, area, presupuesto=False, nombre=n)
    entrar(client, "admin", CLAVE_ADMIN)
    r = client.get(f"/api/indicadores?gestion=true&area_id={area}&limite=2&desde=0")
    assert int(r.headers["X-Total-Count"]) == 3 and len(r.json()) == 2
    assert len(client.get(f"/api/indicadores?gestion=true&area_id={area}&limite=2&desde=2").json()) == 1
    assert int(client.get("/api/indicadores?gestion=true&q=PAGINADO 1&limite=5").headers["X-Total-Count"]) >= 1
    assert int(client.get("/api/indicadores?gestion=true&frecuencia=anual&area_id=" + str(area) + "&limite=5").headers["X-Total-Count"]) == 0
    crear_usuario(client, "gerente")
    entrar(client, "admin", CLAVE_ADMIN)
    u = client.get("/api/usuarios?limite=1")
    assert len(u.json()) == 1 and int(u.headers["X-Total-Count"]) >= 2
    assert int(client.get("/api/usuarios?q=zzz-no-existe&limite=5").headers["X-Total-Count"]) == 0


def test_recordatorios_paginados(client, escenario):
    entrar(client, escenario["gerente"])
    todo = client.get("/api/recordatorios").json()
    pag = client.get("/api/recordatorios?limite=1&desde=0").json()
    assert pag["total"] == todo["total"] == len(todo["encargados"]) and len(pag["encargados"]) <= 1
    con = client.get("/api/recordatorios?solo_pendientes=true").json()
    assert all(e["total"] > 0 for e in con["encargados"]) and con["deben"] == todo["deben"]
