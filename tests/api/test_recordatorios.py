"""Recordatorios de carga: quién tiene períodos pendientes, solo para administrador y gerente."""
from datetime import datetime

from conftest import CLAVE_ADMIN, crear_area, crear_indicador, crear_usuario, entrar, id_de_usuario

from app.database import SessionLocal
from app.models import Indicador


def _escenario(client):
    area = crear_area(client)
    con, sin = crear_usuario(client, "jefe", area), crear_usuario(client, "jefe", area)
    ind = crear_indicador(client, area, encargado_id=id_de_usuario(client, con), nombre="Entregas a tiempo")
    huerfano = crear_indicador(client, area, encargado_id=None, nombre="Sin dueño")
    with SessionLocal() as db:   # indicadores «antiguos»: ya les corresponde haber cargado períodos pasados
        for i in (ind["id"], huerfano["id"]):
            db.get(Indicador, i).creado_en = datetime(2020, 1, 1)
        db.commit()
    return {"con": con, "sin": sin, "ind": ind, "huerfano": huerfano}


def test_lista_quien_debe_cargar_y_quien_esta_al_dia(client):
    e = _escenario(client)
    entrar(client, "admin", CLAVE_ADMIN)
    r = client.get("/api/recordatorios").json()
    por_usuario = {x["id"]: x for x in r["encargados"]}
    debe = por_usuario[id_de_usuario(client, e["con"])]
    assert debe["total"] > 0 and debe["indicadores"][0]["nombre"] == "Entregas a tiempo" and debe["indicadores"][0]["periodos"]
    assert por_usuario[id_de_usuario(client, e["sin"])]["total"] == 0
    assert any(i["nombre"] == "Sin dueño" for i in r["sin_encargado"])
    assert r["encargados"].index(debe) < r["encargados"].index(por_usuario[id_de_usuario(client, e["sin"])])   # primero quien más debe


def test_registrar_el_recordatorio_exige_correo_y_queda_en_la_bitacora(client):
    e = _escenario(client)
    entrar(client, "admin", CLAVE_ADMIN)
    uid = id_de_usuario(client, e["con"])
    assert client.post(f"/api/recordatorios/{uid}", json={"mensaje": "amable"}).status_code == 422   # sin correo
    editado = client.put(f"/api/usuarios/{uid}", json={"nombre": "Usuario con correo", "rol": "jefe", "area_id": e["ind"]["area_id"],
                                                        "email": " Ana.Perez@Tripoliven.COM ", "activo": True})
    assert editado.status_code == 200 and editado.json()["email"] == "ana.perez@tripoliven.com"
    assert client.post(f"/api/recordatorios/{uid}", json={"mensaje": "amable"}).status_code == 201
    mio = next(x for x in client.get("/api/recordatorios").json()["encargados"] if x["id"] == uid)
    assert mio["ultimo_recordatorio"] and mio["email"] == "ana.perez@tripoliven.com"
    assert any(b["accion"] == "RECORDATORIO" for b in client.get("/api/bitacora?accion=RECORDATORIO").json())
    for malo in ("sin-arroba", "a@b", "a b@c.com", "a@b.com, c@d.com"):
        r = client.put(f"/api/usuarios/{uid}", json={"nombre": "Usuario con correo", "rol": "jefe", "area_id": e["ind"]["area_id"], "email": malo})
        assert r.status_code == 422, malo


def test_el_encargado_no_accede_a_los_recordatorios(client):
    e = _escenario(client)
    otro = id_de_usuario(client, e["sin"])
    entrar(client, e["con"])
    assert client.get("/api/recordatorios").status_code == 403
    assert client.post(f"/api/recordatorios/{otro}", json={"mensaje": "x"}).status_code == 403


def test_el_gerente_puede_ver_los_pendientes(client):
    _escenario(client)
    gerente = crear_usuario(client, "gerente")
    entrar(client, gerente)
    assert client.get("/api/recordatorios").status_code == 200
