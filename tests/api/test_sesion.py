from conftest import CLAVE, CLAVE_ADMIN, crear_area, crear_usuario, entrar


def test_no_hay_endpoint_de_usuarios_de_demostracion(client):
    assert client.get("/api/demo-usuarios").status_code in (404, 405)


def test_clave_nueva_invalida_las_sesiones_anteriores(client):
    usuario = crear_usuario(client, "gerente")
    entrar(client, usuario)
    antes = client.cookies.get("sigt_sesion")
    assert client.post("/api/cambiar-clave", json={"actual": "incorrecta", "nueva": "otra-clave-123"}).status_code == 422
    assert client.post("/api/cambiar-clave", json={"actual": CLAVE, "nueva": "otra-clave-123"}).status_code == 200
    assert client.get("/api/me").status_code == 200            # la sesión actual se renueva
    client.cookies.clear()
    client.cookies.set("sigt_sesion", antes)
    assert client.get("/api/me").status_code == 401            # la anterior queda invalidada


def test_demasiados_intentos_fallidos_bloquean_temporalmente(client):
    from app.servicios.sesion import limite_intentos
    usuario = crear_usuario(client, "gerente")
    client.cookies.clear()
    try:
        for _ in range(5):
            client.post("/api/login", json={"username": usuario, "password": "mala"})
        assert client.post("/api/login", json={"username": usuario, "password": CLAVE}).status_code == 429
    finally:
        limite_intentos._fallos.clear()


def test_guia_de_bienvenida_se_marca_una_sola_vez(client):
    usuario = crear_usuario(client, "jefe", crear_area(client))
    entrar(client, usuario)
    assert client.get("/api/me").json()["tour_visto"] is False
    assert client.post("/api/tour", json={"visto": True}).json()["tour_visto"] is True
    assert client.get("/api/me").json()["tour_visto"] is True


def test_el_administrador_inicial_existe(client):
    assert entrar(client, "admin", CLAVE_ADMIN)["rol"] == "admin"
