"""Estructura y cuentas: borrado de nodos, cuentas sin rol, soporte y reglas del Desarrollador."""
import pytest
from conftest import CLAVE, CLAVE_ADMIN, arbol, crear_area, crear_indicador, crear_usuario, cuenta, entrar, unico


def test_nodo_con_indicadores_no_se_elimina(client):
    area = crear_area(client)
    crear_indicador(client, area)
    entrar(client, "admin", CLAVE_ADMIN)
    r = client.delete(f"/api/unidades/{area}")
    assert r.status_code == 409 and "indicador" in r.json()["detail"]


def test_una_cuenta_nueva_no_tiene_rol_ni_acceso(client):
    entrar(client, "admin", CLAVE_ADMIN)
    r = client.post("/api/usuarios", json={"username": unico("x."), "nombre": "Sin rol", "password": CLAVE})
    assert r.status_code == 201 and r.json()["pendiente"] is True and r.json()["rol"] is None


def test_el_desarrollador_no_puede_inhabilitarse_a_si_mismo(client):
    entrar(client, "admin", CLAVE_ADMIN)
    yo = client.get("/api/me").json()
    r = client.put(f"/api/usuarios/{yo['id']}", json={"nombre": "Desarrollador", "activo": False})
    assert r.status_code == 422


@pytest.mark.parametrize("usuario_rol", ["jefe", "gerente"])
def test_solo_quien_tiene_el_permiso_ve_las_personas(client, usuario_rol):
    area = crear_area(client) if usuario_rol == "jefe" else None
    entrar(client, crear_usuario(client, usuario_rol, area))
    assert client.get("/api/usuarios").status_code == 403


def _usuario_nuevo(client, **extra):
    entrar(client, "admin", CLAVE_ADMIN)
    r = client.post("/api/usuarios", json={"username": unico("usr."), "nombre": "Usuario de prueba", "password": CLAVE, **extra})
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
    r = client.put(f"/api/usuarios/{nuevo['id']}", json={"nombre": nuevo["nombre"], "activo": False})
    assert r.status_code == 200 and r.json()["activo"] is False
    client.cookies.clear()
    assert client.post("/api/login", json={"username": nuevo["username"], "password": CLAVE}).status_code == 401   # ya no entra
    entrar(client, "admin", CLAVE_ADMIN)
    r = client.put(f"/api/usuarios/{nuevo['id']}", json={"nombre": nuevo["nombre"], "activo": True})
    assert r.status_code == 200
    entrar(client, nuevo["username"])                          # habilitado de nuevo


def test_no_se_elimina_a_si_mismo_y_solo_quien_tiene_cuentas_elimina(client):
    entrar(client, "admin", CLAVE_ADMIN)
    yo = client.get("/api/me").json()
    assert client.delete(f"/api/usuarios/{yo['id']}").status_code == 422
    otro = cuenta(client)
    entrar(client, otro)                                       # sin rol: ni siquiera el permiso
    assert client.delete(f"/api/usuarios/{yo['id']}").status_code == 403


def test_inhabilitar_a_un_responsable_exige_reasignar_sus_indicadores(client):
    area = crear_area(client)
    resp = crear_usuario(client, "jefe", area)
    crear_indicador(client, area)                              # lo carga el analista de la jefatura
    entrar(client, "admin", CLAVE_ADMIN)
    uid = next(u["id"] for u in client.get("/api/usuarios?q=" + resp).json())
    r = client.put(f"/api/usuarios/{uid}", json={"nombre": "Quien carga", "activo": False})
    assert r.status_code == 409 and "reasígnelos" in r.json()["detail"]


def test_la_estructura_valida_niveles_nombres_y_ciclos(client):
    a = arbol(client)
    entrar(client, "admin", CLAVE_ADMIN)
    assert client.post("/api/unidades", json={"nombre": "Mal", "nivel": "jefatura", "padre_id": a["gerencia"]}).status_code == 422
    assert client.post("/api/unidades", json={"nombre": "Mal", "nivel": "departamento"}).status_code == 422
    assert client.post("/api/unidades", json={"nombre": "Mal", "nivel": "gerencia", "padre_id": a["gerencia"]}).status_code == 422
    nombre = client.get("/api/unidades").json()
    dup = next(n["nombre"] for n in nombre if n["id"] == a["depto"])
    assert client.post("/api/unidades", json={"nombre": dup.upper(), "nivel": "departamento", "padre_id": a["gerencia"]}).status_code == 422
    assert client.post(f"/api/unidades/{a['gerencia']}/mover", json={"padre_id": a["depto"]}).status_code == 422   # gerencia: no se mueve
    assert client.post(f"/api/unidades/{a['depto']}/mover", json={"padre_id": a["jefatura"]}).status_code == 422   # nivel/ciclo
    r = client.delete(f"/api/unidades/{a['gerencia']}")
    assert r.status_code == 409 and "cuelgan" in r.json()["detail"]


def test_mover_un_nodo_reajusta_todo_su_subarbol(client):
    a, b = arbol(client), arbol(client)
    entrar(client, "admin", CLAVE_ADMIN)
    assert client.post(f"/api/unidades/{a['depto']}/mover", json={"padre_id": b["gerencia"]}).status_code == 200
    lista = {n["id"]: n for n in client.get("/api/unidades").json()}
    assert lista[a["depto"]]["padre_id"] == b["gerencia"] and lista[a["jefatura"]]["padre_id"] == a["depto"]
    assert lista[a["jefatura"]]["ruta"].split(" › ")[0] == lista[b["gerencia"]]["nombre"]   # la jefatura se mudó con su departamento
    assert client.delete(f"/api/unidades/{a['gerencia']}").status_code == 200               # la gerencia vieja quedó vacía
