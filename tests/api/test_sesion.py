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


# ---------------------------------------------------------------- endurecimiento del ingreso
def test_usuario_inexistente_tambien_verifica_una_clave(client, monkeypatch):
    """Sin esto, la respuesta rápida delataría qué usuarios existen (temporización)."""
    from app import security
    llamadas = []
    real = security.verificar_password
    monkeypatch.setattr(security, "verificar_password", lambda p, h: llamadas.append(h) or real(p, h))
    client.cookies.clear()
    assert client.post("/api/login", json={"username": "no.existe.nunca", "password": "lo-que-sea"}).status_code == 401
    assert llamadas == [security.HASH_FICTICIO]


def test_login_rechaza_campos_demasiado_largos(client):
    client.cookies.clear()
    assert client.post("/api/login", json={"username": "u" * 41, "password": "x"}).status_code == 422
    assert client.post("/api/login", json={"username": "admin", "password": "x" * 129}).status_code == 422


def test_password_spraying_desde_un_origen_se_bloquea(client):
    from app.servicios.sesion import MAX_POR_ORIGEN, limite_intentos
    client.cookies.clear()
    limite_intentos._fallos.clear()
    try:
        for i in range(MAX_POR_ORIGEN):   # un usuario distinto en cada intento: la pareja IP+usuario nunca llega a su tope
            assert client.post("/api/login", json={"username": f"rociado{i}", "password": "mala"}).status_code == 401
        r = client.post("/api/login", json={"username": "admin", "password": CLAVE_ADMIN})
        assert r.status_code == 429
    finally:
        limite_intentos._fallos.clear()


def test_muchas_ip_contra_un_mismo_usuario_se_bloquean():
    from app.database import SessionLocal
    from app.errores import DemasiadosIntentos, NoAutenticado
    from app.servicios.sesion import MAX_POR_USUARIO, autenticar, limite_intentos
    try:
        with SessionLocal() as db:
            for i in range(MAX_POR_USUARIO):
                try:
                    autenticar(db, "admin", "mala", f"10.0.0.{i}")
                except NoAutenticado:
                    pass
            try:
                autenticar(db, "admin", CLAVE_ADMIN, "10.0.1.1")   # clave correcta, pero la cuenta está siendo atacada
                raise AssertionError("debió bloquearse")
            except DemasiadosIntentos:
                pass
    finally:
        limite_intentos._fallos.clear()


def test_un_acceso_valido_no_borra_el_contador_del_origen(client):
    from app.servicios.sesion import limite_intentos
    usuario = crear_usuario(client, "gerente")
    client.cookies.clear()
    try:
        client.post("/api/login", json={"username": "otro.usuario", "password": "mala"})
        assert client.post("/api/login", json={"username": usuario, "password": CLAVE}).status_code == 200
        assert len(limite_intentos._fallos["origen|testclient"]) == 1
    finally:
        limite_intentos._fallos.clear()
