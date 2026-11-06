"""Soporte a usuarios desde el administrador, y comportamiento de rendimiento / cabeceras de la aplicación."""
import re

from conftest import CLAVE, CLAVE_ADMIN, crear_usuario, entrar

from app.servicios.sesion import limite_intentos


# ---------------------------------------------------------------- soporte (administrador)
def test_el_administrador_cierra_las_sesiones_de_otro_usuario(client):
    nombre = crear_usuario(client, "gerente")
    entrar(client, nombre)
    assert client.get("/api/me").status_code == 200
    token_del_usuario = dict(client.cookies)
    entrar(client, "admin", CLAVE_ADMIN)
    uid = next(u["id"] for u in client.get("/api/usuarios").json() if u["username"] == nombre)
    assert client.post(f"/api/usuarios/{uid}/cerrar-sesiones").status_code == 200
    client.cookies.clear()
    client.cookies.update(token_del_usuario)
    assert client.get("/api/me").status_code == 401                  # su sesión ya no vale
    entrar(client, nombre)                                           # pero puede volver a ingresar
    assert client.post(f"/api/usuarios/{uid}/cerrar-sesiones").status_code == 403     # y no es administrador


def test_el_administrador_no_cierra_su_propia_sesion_por_soporte(client):
    entrar(client, "admin", CLAVE_ADMIN)
    yo = client.get("/api/me").json()["id"]
    assert client.post(f"/api/usuarios/{yo}/cerrar-sesiones").status_code == 422
    assert client.post("/api/usuarios/999999/cerrar-sesiones").status_code == 404


def test_desbloquear_accesos_levanta_el_bloqueo_por_intentos(client):
    nombre = crear_usuario(client, "gerente")
    limite_intentos.reiniciar()
    try:
        client.cookies.clear()
        for _ in range(5):
            assert client.post("/api/login", json={"username": nombre, "password": "incorrecta-123"}).status_code == 401
        assert client.post("/api/login", json={"username": nombre, "password": CLAVE}).status_code == 429   # bloqueado
        limite_intentos.reiniciar()                                  # (el administrador también está bajo el mismo origen de prueba)
        entrar(client, "admin", CLAVE_ADMIN)
        for _ in range(5):
            client.post("/api/login", json={"username": nombre, "password": "incorrecta-123"})
        entrar(client, "admin", CLAVE_ADMIN)
        assert client.post("/api/sistema/desbloquear-accesos").status_code == 200
        client.cookies.clear()
        assert client.post("/api/login", json={"username": nombre, "password": CLAVE}).status_code == 200
        entrar(client, nombre)
        assert client.post("/api/sistema/desbloquear-accesos").status_code == 403
    finally:
        limite_intentos.reiniciar()


def test_la_lista_de_usuarios_informa_el_ultimo_ingreso(client):
    nombre = crear_usuario(client, "gerente")
    entrar(client, nombre)
    entrar(client, "admin", CLAVE_ADMIN)
    por_nombre = {u["username"]: u for u in client.get("/api/usuarios").json()}
    assert por_nombre[nombre]["ultimo_ingreso"] and por_nombre[nombre]["ultimo_ingreso"].endswith("Z")
    otro = crear_usuario(client, "gerente")
    entrar(client, "admin", CLAVE_ADMIN)
    assert {u["username"]: u for u in client.get("/api/usuarios").json()}[otro]["ultimo_ingreso"] is None


# ---------------------------------------------------------------- rendimiento y cabeceras
def test_la_pagina_viaja_comprimida_y_con_huellas_de_version(client):
    r = client.get("/", headers={"Accept-Encoding": "gzip"})
    assert r.headers.get("content-encoding") == "gzip"
    html = client.get("/", headers={"Accept-Encoding": "identity"}).text
    assert re.findall(r'src="/static/js/nucleo\.js\?v=[0-9a-f]{10}"', html) and re.search(r'href="/static/tailwind\.css\?v=[0-9a-f]{10}"', html)
    assert not re.search(r"<script[^>]+chart\.umd", html)            # los gráficos se piden solo cuando hacen falta
    assert 'name="sgc-chart"' in html and "chart.umd.js?v=" in html


def test_los_estaticos_con_huella_se_guardan_un_anio_y_la_api_nunca(client):
    html = client.get("/", headers={"Accept-Encoding": "identity"}).text
    ruta = re.search(r'src="(/static/js/nucleo\.js\?v=[0-9a-f]{10})"', html).group(1)
    assert "immutable" in client.get(ruta).headers["cache-control"]
    assert "immutable" in client.get("/static/fonts/manrope-latin-wght-normal.woff2").headers["cache-control"]
    assert "max-age=300" in client.get("/static/js/nucleo.js").headers["cache-control"]        # sin huella: poco tiempo
    assert client.get("/api/publico").headers["cache-control"] == "public, max-age=60"
    entrar(client, "admin", CLAVE_ADMIN)
    assert client.get("/api/me").headers["cache-control"] == "no-store"


def test_cabeceras_de_seguridad_y_cookie_estricta(client):
    r = client.get("/")
    for cab in ("content-security-policy", "x-frame-options", "x-content-type-options", "cross-origin-opener-policy",
                "cross-origin-resource-policy", "referrer-policy", "permissions-policy"):
        assert cab in r.headers, cab
    assert r.headers["x-frame-options"] == "DENY" and r.headers["cross-origin-opener-policy"] == "same-origin"
    login = client.post("/api/login", json={"username": "admin", "password": CLAVE_ADMIN})
    cookie = login.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie
