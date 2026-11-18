"""Entrega 4: notificaciones. Guardadas (carga aprobada, devuelta con su motivo, reabierta) y calculadas (el período está por
cerrar y faltan cargas)."""
from datetime import timedelta

from conftest import CLAVE_ADMIN, arbol, crear_indicador, entrar, id_de_usuario, periodo_actual, persona

from app.database import SessionLocal
from app.dominio import calendario
from app.models import Indicador, PeriodoJustificado, Usuario
from app.servicios import notificaciones

CARGA = {"dias": 1, "tickets": 1}


def _escenario(client):
    a = arbol(client)
    resp, supl, ajeno = (persona(client, "Analista", miembro=[a["jefatura"]]) for _ in range(3))
    coord = persona(client, "coordinador")
    entrar(client, "admin", CLAVE_ADMIN)
    ind = crear_indicador(client, a["jefatura"], responsable_id=id_de_usuario(client, resp), suplente_id=id_de_usuario(client, supl))
    return {"ind": ind, "resp": resp, "supl": supl, "ajeno": ajeno, "coord": coord, "periodo": periodo_actual(client, ind["id"])}


def _lista(client, usuario):
    entrar(client, usuario)
    return client.get("/api/notificaciones").json()


def test_aprobar_devolver_y_reabrir_avisan_a_quien_carga_con_el_motivo(client):
    e = _escenario(client)
    entrar(client, e["resp"])
    m = client.post("/api/mediciones", json={"indicador_id": e["ind"]["id"], "periodo": e["periodo"], "valores": CARGA}).json()["id"]
    entrar(client, e["coord"])
    assert client.post(f"/api/mediciones/{m}/revision", json={"accion": "observar", "nota": "Falta el soporte del dato"}).status_code == 200
    entrar(client, e["resp"])
    assert client.post("/api/mediciones", json={"indicador_id": e["ind"]["id"], "periodo": e["periodo"], "valores": CARGA}).status_code == 201
    entrar(client, e["coord"])
    assert client.post(f"/api/mediciones/{m}/revision", json={"accion": "aprobar", "nota": "Conforme"}).status_code == 200
    assert client.post(f"/api/mediciones/{m}/reabrir", json={"accion": "observar", "nota": "Se detectó un error"}).status_code == 200

    n = _lista(client, e["resp"])
    assert [x["tipo"] for x in n["items"]] == ["reabierta", "aprobada", "devuelta"] and n["no_leidas"] == 3     # lo más reciente primero
    devuelta = n["items"][2]
    assert devuelta["titulo"].startswith("Carga devuelta") and "Falta el soporte del dato" in devuelta["texto"]
    assert devuelta["indicador_id"] == e["ind"]["id"] and devuelta["periodo"] == e["periodo"] and devuelta["leida"] is False
    assert _lista(client, e["supl"])["no_leidas"] == 3                          # el suplente también carga: también se entera
    assert _lista(client, e["ajeno"])["items"] == [] and _lista(client, e["coord"])["items"] == []   # ni el ajeno ni quien revisó
    arranque = client.get("/api/arranque").json()["notificaciones"]
    assert arranque["no_leidas"] == 0 and arranque["items"] == []              # (el arranque trae lo de quien entró: el coordinador)


def test_marcar_como_leidas_solo_toca_lo_propio(client):
    e = _escenario(client)
    entrar(client, e["resp"])
    m = client.post("/api/mediciones", json={"indicador_id": e["ind"]["id"], "periodo": e["periodo"], "valores": CARGA}).json()["id"]
    entrar(client, e["coord"])
    client.post(f"/api/mediciones/{m}/revision", json={"accion": "observar", "nota": "Corrija el dato"})
    ids_resp = [x["id"] for x in _lista(client, e["resp"])["items"]]
    assert len(ids_resp) == 1
    entrar(client, e["supl"])                                                   # el suplente intenta marcar la de otra persona
    assert client.post("/api/notificaciones/leer", json={"ids": ids_resp}).json() == {"marcadas": 0, "no_leidas": 1}
    entrar(client, e["resp"])
    assert client.post("/api/notificaciones/leer", json={"ids": ids_resp}).json() == {"marcadas": 1, "no_leidas": 0}
    assert client.get("/api/notificaciones").json()["items"][0]["leida"] is True
    assert client.post("/api/notificaciones/leer", json={}).json() == {"marcadas": 0, "no_leidas": 0}
    entrar(client, e["supl"])
    assert client.post("/api/notificaciones/leer", json={}).json()["marcadas"] == 1                       # «todas»
    client.cookies.clear()
    assert client.get("/api/notificaciones").status_code == 401


def _con(username, funcion):
    """Ejecuta `funcion(db, usuario)` con la persona leída de la base (el servicio se prueba con fechas elegidas)."""
    with SessionLocal() as db:
        return funcion(db, db.query(Usuario).filter_by(username=username).one())


def test_el_aviso_de_cierre_aparece_5_dias_antes_si_faltan_cargas_y_se_va_al_cargar(client):
    e = _escenario(client)
    _, fin = calendario.rango("mensual", e["periodo"])
    avisos = lambda quien, hoy: _con(quien, lambda db, u: notificaciones.avisos_de_cierre(db, u, hoy))   # noqa: E731
    assert avisos(e["resp"], fin - timedelta(days=notificaciones.DIAS_AVISO_CIERRE + 1)) == []                # todavía falta mucho
    for hoy, dias in ((fin - timedelta(days=notificaciones.DIAS_AVISO_CIERRE), 5), (fin - timedelta(days=1), 1), (fin, 0)):
        for quien in (e["resp"], e["supl"]):                                                                   # responsable y suplente
            a = avisos(quien, hoy)
            assert len(a) == 1 and a[0]["indicador_id"] == e["ind"]["id"] and a[0]["dias"] == dias
            assert calendario.etiqueta("mensual", e["periodo"]) in a[0]["periodos"]
    assert avisos(e["ajeno"], fin) == [] and avisos(e["coord"], fin) == []                                    # quien no lo carga, no recibe aviso
    entrar(client, e["resp"])
    # al cargar el período en curso el aviso desaparece
    assert client.post("/api/mediciones", json={"indicador_id": e["ind"]["id"], "periodo": e["periodo"], "valores": CARGA}).status_code == 201
    assert avisos(e["resp"], fin) == []


def test_un_periodo_justificado_o_un_indicador_archivado_no_generan_aviso(client):
    e = _escenario(client)
    _, fin = calendario.rango("mensual", e["periodo"])
    avisos = lambda hoy: _con(e["resp"], lambda db, u: notificaciones.avisos_de_cierre(db, u, hoy))   # noqa: E731
    assert len(avisos(fin)) == 1
    with SessionLocal() as db:
        db.add(PeriodoJustificado(indicador_id=e["ind"]["id"], periodo=e["periodo"], ejercicio=calendario.ejercicio_de(
            "mensual", e["periodo"]), tipo="parada_planta", motivo="Parada programada", por_id=db.query(Usuario).filter_by(username="admin").one().id))
        db.commit()
    assert avisos(fin) == []                                                    # justificado: cubierto
    with SessionLocal() as db:
        db.query(PeriodoJustificado).delete()
        db.get(Indicador, e["ind"]["id"]).activo = False
        db.commit()
    assert avisos(fin) == []                                                    # archivado: nada que cargar
