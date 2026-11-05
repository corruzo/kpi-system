import pytest
from conftest import CLAVE, CLAVE_ADMIN, crear_area, crear_indicador, crear_usuario, entrar


def test_area_con_indicadores_no_se_elimina(client):
    area = crear_area(client)
    crear_indicador(client, area)
    assert client.delete(f"/api/areas/{area}").status_code == 409


def test_jefe_exige_area(client):
    entrar(client, "admin", "clave-admin-123")
    r = client.post("/api/usuarios", json={"username": "x.jefe", "nombre": "Sin Area", "rol": "jefe", "password": CLAVE})
    assert r.status_code == 422


def test_el_administrador_no_puede_desactivarse_ni_quitarse_el_rol(client):
    entrar(client, "admin", "clave-admin-123")
    yo = client.get("/api/me").json()
    r = client.put(f"/api/usuarios/{yo['id']}", json={"nombre": "Admin SGC", "rol": "admin", "activo": False})
    assert r.status_code == 422


@pytest.mark.parametrize("usuario_rol", ["jefe", "gerente"])
def test_solo_el_administrador_gestiona_usuarios(client, usuario_rol):
    area = crear_area(client) if usuario_rol == "jefe" else None
    entrar(client, crear_usuario(client, usuario_rol, area))
    assert client.get("/api/usuarios").status_code == 403


def _usuario_nuevo(client, rol="gerente", **extra):
    from conftest import unico
    entrar(client, "admin", CLAVE_ADMIN)
    r = client.post("/api/usuarios", json={"username": unico("usr."), "nombre": "Usuario de prueba", "rol": rol, "password": CLAVE, **extra})
    assert r.status_code == 201, r.text
    return r.json()


def test_un_usuario_sin_actividad_se_puede_eliminar_y_queda_en_la_bitacora(client):
    nuevo = _usuario_nuevo(client)
    lista = {x["id"]: x for x in client.get("/api/usuarios").json()}
    assert lista[nuevo["id"]]["puede_eliminarse"] is True
    assert client.delete(f"/api/usuarios/{nuevo['id']}").status_code == 200
    assert nuevo["id"] not in {x["id"] for x in client.get("/api/usuarios").json()}
    assert client.delete(f"/api/usuarios/{nuevo['id']}").status_code == 404
    assert any(b["accion"] == "USUARIO_ELIMINADO" and b["detalle"]["username"] == nuevo["username"]
               for b in client.get("/api/bitacora?limite=20").json())


def test_un_usuario_con_actividad_no_se_elimina_pero_si_se_inhabilita(client):
    nuevo = _usuario_nuevo(client)
    entrar(client, nuevo["username"])                          # el ingreso queda en la bitácora: ya tiene historial
    entrar(client, "admin", CLAVE_ADMIN)
    assert {x["id"]: x for x in client.get("/api/usuarios").json()}[nuevo["id"]]["puede_eliminarse"] is False
    r = client.delete(f"/api/usuarios/{nuevo['id']}")
    assert r.status_code == 409 and "Inhabilítelo" in r.json()["detail"]
    r = client.put(f"/api/usuarios/{nuevo['id']}", json={"nombre": nuevo["nombre"], "rol": "gerente", "activo": False})
    assert r.status_code == 200 and r.json()["activo"] is False
    client.cookies.clear()
    assert client.post("/api/login", json={"username": nuevo["username"], "password": CLAVE}).status_code == 401   # ya no entra
    entrar(client, "admin", CLAVE_ADMIN)
    r = client.put(f"/api/usuarios/{nuevo['id']}", json={"nombre": nuevo["nombre"], "rol": "gerente", "activo": True})
    assert r.status_code == 200
    entrar(client, nuevo["username"])                          # habilitado de nuevo


def test_no_se_elimina_a_si_mismo_y_solo_el_admin_elimina(client):
    entrar(client, "admin", CLAVE_ADMIN)
    yo = client.get("/api/me").json()
    assert client.delete(f"/api/usuarios/{yo['id']}").status_code == 422
    otro = _usuario_nuevo(client, "gerente")
    entrar(client, otro["username"])
    assert client.delete(f"/api/usuarios/{yo['id']}").status_code == 403
