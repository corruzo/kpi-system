"""Robustez: entradas absurdas, errores inesperados y límites. Ninguna petición debe terminar en un 500 sin explicación."""
from datetime import UTC, datetime

import pytest
from conftest import crear_area, crear_usuario, entrar
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError, OperationalError

from app.dominio import calendario
from app.main import app

GIGANTE = 10**30


@pytest.fixture()
def admin(client):
    entrar(client, "admin", "clave-admin-123")
    return client


@pytest.mark.parametrize("metodo,ruta", [
    ("GET", f"/api/indicadores/{GIGANTE}/periodos"), ("GET", f"/api/indicadores/{GIGANTE}/ficha"), ("PUT", f"/api/unidades/{GIGANTE}"),
    ("DELETE", f"/api/unidades/{GIGANTE}"), ("POST", f"/api/mediciones/{GIGANTE}/revision"), ("GET", f"/api/ejercicios/{GIGANTE}/verificacion"),
    ("GET", "/api/ejercicios/0/metas"), ("GET", "/api/ejercicios/-4/metas"), ("GET", "/api/ejercicios/1/verificacion"),
    ("GET", f"/api/mediciones?indicador_id={GIGANTE}"), ("GET", f"/api/dashboard?ejercicio={GIGANTE}"),
    ("GET", "/api/reportes/general.xlsx?anio=1"), ("GET", f"/api/reportes/fichas.xlsx?ejercicio={GIGANTE}"),
    ("GET", "/api/indicadores?ejercicio=-1"), ("GET", "/api/mediciones?limite=0"), ("GET", "/api/bitacora?limite=-3"),
])
def test_ids_y_anios_imposibles_se_rechazan_con_422(admin, metodo, ruta):
    assert admin.request(metodo, ruta, json={} if metodo in ("POST", "PUT") else None).status_code == 422


def test_la_busqueda_por_usuario_trata_porcentaje_y_guion_bajo_como_texto(admin):
    admin.get("/api/bitacora?limite=5")
    assert admin.get("/api/bitacora?usuario=%25").json() == []          # «%» ya no es comodín
    assert admin.get("/api/bitacora?usuario=_").json() == []


def test_textos_y_diccionarios_desmedidos_se_rechazan(admin, escenario):
    ind = escenario["indicador"]["id"]
    base = {"indicador_id": ind, "periodo": "2026-01", "valores": {"dias": 1, "tickets": 1}}
    assert admin.post("/api/mediciones", json={**base, "analisis": "x" * 5000}).status_code == 422
    assert admin.post("/api/calcular", json={"indicador_id": ind, "valores": {f"v{i}": 1 for i in range(100)}}).status_code == 422
    assert admin.post("/api/mediciones/1/revision", json={"accion": "observar", "nota": "x" * 3000}).status_code == 422
    assert admin.put(f"/api/ejercicios/{calendario.ejercicio_de_fecha(calendario.hoy())}/metas/{ind}",
                     json={"valores": {f"2026-{i}": 1 for i in range(100)}}).status_code == 422


def test_un_error_inesperado_responde_json_con_codigo_y_sin_detalle_tecnico():
    app.add_api_route("/api/_prueba_error", lambda: 1 / 0, methods=["GET"])
    r = TestClient(app, raise_server_exceptions=False).get("/api/_prueba_error")
    assert r.status_code == 500 and r.headers["content-type"].startswith("application/json")
    assert "código" in r.json()["detail"] and "division" not in r.text.lower() and "Traceback" not in r.text


def test_un_choque_de_restriccion_unica_es_409_y_la_base_caida_es_503():
    def choque():
        raise IntegrityError("INSERT", {}, Exception("UNIQUE constraint failed"))

    def caida():
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))
    app.add_api_route("/api/_prueba_choque", choque, methods=["GET"])
    app.add_api_route("/api/_prueba_caida", caida, methods=["GET"])
    c = TestClient(app, raise_server_exceptions=False)
    assert c.get("/api/_prueba_choque").status_code == 409
    r = c.get("/api/_prueba_caida")
    assert r.status_code == 503 and "connection refused" not in r.text


def test_hoy_usa_la_hora_de_venezuela(monkeypatch):
    class Reloj(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 11, 6, 2, 30, tzinfo=UTC)       # 02:30 UTC = 22:30 del día 5 en Venezuela
    monkeypatch.setattr(calendario, "datetime", Reloj)
    assert calendario.hoy().isoformat() == "2026-11-05"


def test_login_con_datos_absurdos_no_falla(client):
    for cuerpo in ({}, {"username": "a" * 500, "password": "x"}, {"username": "admin", "password": "x" * 500},
                   {"username": "' OR 1=1 --", "password": "x"}, {"username": "ñandú\u0000", "password": "x"}):
        assert client.post("/api/login", json=cuerpo).status_code in (401, 422)


def test_las_cargas_se_listan_con_pocas_consultas(client, escenario):
    """Antes cada fila hacía consultas adicionales (indicador, área, usuarios, notas): ahora el total no crece con las filas."""
    from sqlalchemy import event

    from app.database import engine
    entrar(client, "admin", "clave-admin-123")
    consultas = []

    def contar(*_):
        consultas.append(1)
    event.listen(engine, "before_cursor_execute", contar)
    try:
        assert client.get("/api/mediciones?limite=500").status_code == 200
        assert client.get("/api/usuarios").status_code == 200
    finally:
        event.remove(engine, "before_cursor_execute", contar)
    assert len(consultas) <= 16, f"{len(consultas)} consultas"


def test_un_usuario_nuevo_y_su_posicion_se_listan_sin_error(client):
    area = crear_area(client)
    crear_usuario(client, "jefe", area)
    assert all({"rol", "ambito", "miembro", "pendiente"} <= u.keys() for u in client.get("/api/usuarios").json())


def _consultas(client, url):
    from sqlalchemy import event

    from app.database import engine
    n = []

    def contar(*_):
        n.append(1)
    event.listen(engine, "before_cursor_execute", contar)
    try:
        assert client.get(url).status_code == 200, url
    finally:
        event.remove(engine, "before_cursor_execute", contar)
    return len(n)


def test_el_arranque_y_los_listados_no_tienen_consultas_por_fila(client):
    """Sin N+1: agregar indicadores, cargadores y personas no aumenta el número de consultas de las rutas calientes."""
    from conftest import crear_indicador, persona
    nodo = crear_area(client)
    jefe = persona(client, "Jefe", ambito=[nodo])
    crear_indicador(client, nodo)
    persona(client, "Analista", miembro=[nodo])        # línea base con al menos una fila de cada cosa (con 0 filas se omiten consultas)
    como_jefe = ["/api/arranque", "/api/indicadores", "/api/indicadores?gestion=true&limite=50", "/api/mediciones?limite=50",
                 "/api/bandeja", "/api/recordatorios"]
    como_dev = ["/api/arranque", "/api/unidades", "/api/usuarios?limite=50", "/api/roles", "/api/indicadores?limite=50"]
    entrar(client, jefe)
    antes_j = {u: _consultas(client, u) for u in como_jefe}
    entrar(client, "admin", "clave-admin-123")
    antes_d = {u: _consultas(client, u) for u in como_dev}
    for _ in range(4):
        crear_indicador(client, nodo)
    for _ in range(3):
        persona(client, "Analista", miembro=[nodo])
    entrar(client, "admin", "clave-admin-123")
    for u, base in antes_d.items():
        assert (ahora := _consultas(client, u)) <= base + 1, f"Desarrollador {u}: de {base} a {ahora} consultas al agregar filas"
    entrar(client, jefe)
    for u, base in antes_j.items():
        assert (ahora := _consultas(client, u)) <= base + 1, f"Jefe {u}: de {base} a {ahora} consultas al agregar filas"
    assert _consultas(client, "/api/arranque") <= 25
