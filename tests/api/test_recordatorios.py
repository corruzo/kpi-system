"""Recordatorios de carga: quién tiene períodos pendientes, solo dentro del ámbito de quien consulta."""
from datetime import datetime

from conftest import CLAVE_ADMIN, crear_area, crear_indicador, crear_usuario, entrar, id_de_usuario, persona

from app.database import SessionLocal
from app.models import Indicador


def _escenario(client):
    area = crear_area(client)
    con, sin = crear_usuario(client, "jefe", area), crear_usuario(client, "jefe", area)
    ind = crear_indicador(client, area, encargado_id=id_de_usuario(client, con), nombre="Entregas a tiempo")
    otro = crear_indicador(client, area, encargado_id=id_de_usuario(client, sin), nombre="Al día")
    with SessionLocal() as db:   # indicadores «antiguos»: al primero ya le corresponde haber cargado períodos pasados
        db.get(Indicador, ind["id"]).creado_en = datetime(2020, 1, 1)
        db.commit()
    return {"con": con, "sin": sin, "ind": ind, "otro": otro, "area": area}


def test_lista_quien_debe_cargar_y_quien_esta_al_dia(client):
    e = _escenario(client)
    entrar(client, "admin", CLAVE_ADMIN)
    r = client.get("/api/recordatorios").json()
    por_usuario = {x["id"]: x for x in r["personas"]}
    debe = por_usuario[id_de_usuario(client, e["con"])]
    assert debe["total"] > 0 and debe["indicadores"][0]["nombre"] == "Entregas a tiempo" and debe["indicadores"][0]["periodos"]
    assert r["personas"].index(debe) < r["personas"].index(por_usuario[id_de_usuario(client, e["sin"])]) or \
        por_usuario[id_de_usuario(client, e["sin"])]["total"] == 0   # primero quien más debe


def test_registrar_el_recordatorio_exige_correo_y_queda_en_la_bitacora(client):
    e = _escenario(client)
    entrar(client, "admin", CLAVE_ADMIN)
    uid = id_de_usuario(client, e["con"])
    assert client.post(f"/api/recordatorios/{uid}", json={"mensaje": "amable"}).status_code == 422   # sin correo
    editado = client.put(f"/api/usuarios/{uid}", json={"nombre": "Usuario con correo", "email": " Ana.Perez@Tripoliven.COM ", "activo": True})
    assert editado.status_code == 200 and editado.json()["email"] == "ana.perez@tripoliven.com"
    assert client.post(f"/api/recordatorios/{uid}", json={"mensaje": "amable"}).status_code == 201
    mio = next(x for x in client.get("/api/recordatorios").json()["personas"] if x["id"] == uid)
    assert mio["ultimo_recordatorio"] and mio["email"] == "ana.perez@tripoliven.com"
    assert any(b["accion"] == "RECORDATORIO" for b in client.get("/api/bitacora?accion=RECORDATORIO").json())
    for malo in ("sin-arroba", "a@b", "a b@c.com", "a@b.com, c@d.com"):
        r = client.put(f"/api/usuarios/{uid}", json={"nombre": "Usuario con correo", "email": malo})
        assert r.status_code == 422, malo


def test_quien_no_tiene_el_permiso_no_accede(client):
    e = _escenario(client)
    otro = id_de_usuario(client, e["sin"])
    entrar(client, e["con"])   # analista: sin recordatorios.enviar
    assert client.get("/api/recordatorios").status_code == 403
    assert client.post(f"/api/recordatorios/{otro}", json={"mensaje": "x"}).status_code == 403


def test_solo_alcanza_a_personas_del_ambito_de_quien_envia(client):
    """Un jefe con ámbito en otra jefatura no ve ni recuerda a quienes cargan en un nodo ajeno."""
    e = _escenario(client)
    uid = id_de_usuario(client, e["con"])
    entrar(client, "admin", CLAVE_ADMIN)
    client.put(f"/api/usuarios/{uid}", json={"nombre": "Con correo", "email": "con@tripoliven.com", "activo": True})
    propio = persona(client, "Jefe", ambito=[e["area"]])
    ajeno = persona(client, "Jefe", ambito=[crear_area(client)])
    entrar(client, propio)
    assert uid in {x["id"] for x in client.get("/api/recordatorios").json()["personas"]}
    assert client.post(f"/api/recordatorios/{uid}", json={"mensaje": "amable"}).status_code == 201
    entrar(client, ajeno)
    assert uid not in {x["id"] for x in client.get("/api/recordatorios").json()["personas"]}
    assert client.post(f"/api/recordatorios/{uid}", json={"mensaje": "amable"}).status_code == 404
