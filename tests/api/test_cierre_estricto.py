"""Cierre fiscal estricto: un ejercicio solo se cierra con todos sus períodos cargados y aprobados, o justificados
(parada de planta, empezó a medirse después, no aplica). Los indicadores archivados antes de un período no lo deben."""
from datetime import datetime

from conftest import crear_area, crear_indicador, crear_usuario, entrar, fijar_metas, id_de_usuario, persona

from app.database import SessionLocal
from app.dominio import calendario
from app.models import Indicador


def _escenario(client, anios_atras: int):
    """Un indicador mensual con UNA carga aprobada en el primer mes de un ejercicio terminado; los otros 11 meses faltan."""
    area = crear_area(client)
    cargador = crear_usuario(client, "jefe", area)
    ind = crear_indicador(client, area, responsable_id=id_de_usuario(client, cargador), cargadores=[id_de_usuario(client, cargador)])
    anio = calendario.ejercicio_de_fecha(calendario.hoy()) - anios_atras
    fijar_metas(client, ind, anio=anio)
    meses = calendario.periodos_del_ejercicio("mensual", anio)
    entrar(client, cargador)
    r = client.post("/api/mediciones", json={"indicador_id": ind["id"], "periodo": meses[0], "valores": {"dias": 1, "tickets": 1}})
    assert r.status_code == 201, r.text
    coord = persona(client, "coordinador")
    entrar(client, coord)
    assert client.post(f"/api/mediciones/{r.json()['id']}/revision", json={"accion": "aprobar", "nota": ""}).status_code == 200
    return {"ind": ind, "anio": anio, "meses": meses, "cargador": cargador, "coord": coord}


def test_no_se_cierra_con_periodos_sin_cargar_ni_se_puede_forzar(client):
    e = _escenario(client, 3)
    entrar(client, e["coord"])
    v = client.get(f"/api/ejercicios/{e['anio']}/verificacion").json()
    assert v["total_faltantes"] == 11 and v["puede_cerrar"] is False
    mio = next(f for f in v["faltantes"] if f["indicador_id"] == e["ind"]["id"])
    assert [i["periodo"] for i in mio["items"]] == e["meses"][1:]
    for cuerpo in ({}, {"nota": "x"}, {"aceptar_faltantes": True}):          # ya no existe «cerrar de todos modos»
        r = client.post(f"/api/ejercicios/{e['anio']}/cerrar", json=cuerpo)
        assert r.status_code == 422 and "justif" in r.json()["detail"].lower(), r.text


def test_justificar_un_periodo_lo_da_por_cubierto_y_permite_cerrar(client):
    e = _escenario(client, 4)
    base = f"/api/indicadores/{e['ind']['id']}/justificaciones"
    entrar(client, e["cargador"])
    assert client.post(base, json={"periodo": e["meses"][1], "tipo": "parada_planta", "motivo": "Parada programada"}).status_code == 403
    entrar(client, e["coord"])
    assert client.post(base, json={"periodo": e["meses"][1], "tipo": "parada_planta", "motivo": "ab"}).status_code == 422   # motivo obligatorio
    assert client.post(base, json={"periodo": e["meses"][1], "tipo": "otro", "motivo": "Parada programada"}).status_code == 422
    assert client.post(base, json={"periodo": e["meses"][0], "tipo": "no_aplica", "motivo": "Ya tiene carga"}).status_code == 409
    futuro = calendario.periodo_actual("mensual", calendario.limites(calendario.ejercicio_de_fecha(calendario.hoy()) + 1)[0])
    assert client.post(base, json={"periodo": futuro, "tipo": "no_aplica", "motivo": "Todavía no ocurre"}).status_code == 422

    for k, mes in enumerate(e["meses"][1:], 1):
        tipo = "inicio_medicion" if k < 3 else "parada_planta"
        r = client.post(base, json={"periodo": mes, "tipo": tipo, "motivo": "Justificación de prueba"})
        assert r.status_code == 201, r.text
    assert client.post(base, json={"periodo": e["meses"][1], "tipo": "no_aplica", "motivo": "Otra vez"}).status_code == 409

    v = client.get(f"/api/ejercicios/{e['anio']}/verificacion").json()
    assert v["total_faltantes"] == 0 and v["puede_cerrar"] is True and len(v["justificados"]) == 11
    assert {j["por"] for j in v["justificados"]} == {v["justificados"][0]["por"]}

    # un período justificado no se carga, no está pendiente y la bitácora lo recuerda
    entrar(client, e["cargador"])
    r = client.post("/api/mediciones", json={"indicador_id": e["ind"]["id"], "periodo": e["meses"][1], "valores": {"dias": 1, "tickets": 1}})
    assert r.status_code == 409
    d = client.get(f"/api/indicadores/{e['ind']['id']}/periodos?ejercicio={e['anio']}").json()
    fila = next(x for x in d["periodos"] if x["periodo"] == e["meses"][1])
    assert fila["justificado"]["tipo"] == "inicio_medicion" and not fila["pendiente"]

    entrar(client, e["coord"])
    assert client.delete(f"{base}/{e['meses'][5]}").status_code == 200                   # se revoca: vuelve a exigirse
    assert client.delete(f"{base}/{e['meses'][5]}").status_code == 404
    assert client.get(f"/api/ejercicios/{e['anio']}/verificacion").json()["total_faltantes"] == 1
    assert client.post(f"/api/ejercicios/{e['anio']}/cerrar", json={}).status_code == 422
    assert client.post(base, json={"periodo": e["meses"][5], "tipo": "no_aplica", "motivo": "Se vuelve a justificar"}).status_code == 201

    assert client.post(f"/api/ejercicios/{e['anio']}/cerrar", json={"nota": "Cierre con justificaciones"}).json()["estado"] == "cerrado"
    assert client.delete(f"{base}/{e['meses'][5]}").status_code == 409                   # con el ejercicio cerrado nada cambia
    assert client.post(base, json={"periodo": e["meses"][5], "tipo": "no_aplica", "motivo": "Fuera de plazo"}).status_code in (404, 409, 422)


def test_un_indicador_archivado_no_debe_los_periodos_posteriores_a_su_archivado(client):
    e = _escenario(client, 5)
    corte = calendario.rango("mensual", e["meses"][2])[0]            # archivado el primer día del tercer mes
    with SessionLocal() as db:
        ind = db.get(Indicador, e["ind"]["id"])
        ind.activo, ind.archivado_en = False, datetime(corte.year, corte.month, corte.day, 8)
        db.commit()
    entrar(client, e["coord"])
    v = client.get(f"/api/ejercicios/{e['anio']}/verificacion").json()
    mio = next(f for f in v["faltantes"] if f["indicador_id"] == e["ind"]["id"])
    assert [i["periodo"] for i in mio["items"]] == e["meses"][1:3]    # mes 2 y mes 3; del 4 en adelante ya no se le exigen
    assert v["total_faltantes"] == 2


def test_archivar_y_restaurar_guardan_la_fecha(client):
    area = crear_area(client)
    ind = crear_indicador(client, area)
    entrar(client, "admin", "clave-admin-123")
    assert client.post(f"/api/indicadores/{ind['id']}/archivar").status_code == 200
    with SessionLocal() as db:
        assert db.get(Indicador, ind["id"]).archivado_en is not None
    assert client.post(f"/api/indicadores/{ind['id']}/restaurar").status_code == 200
    with SessionLocal() as db:
        assert db.get(Indicador, ind["id"]).archivado_en is None
