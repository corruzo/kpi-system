import pytest
from conftest import CLAVE, crear_area, crear_indicador, crear_usuario, entrar


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
