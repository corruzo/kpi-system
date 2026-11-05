"""Configuración común de las pruebas: base temporal, cliente HTTP y fábricas de datos.

La base se crea una sola vez por sesión de pruebas (SQLite temporal, o PostgreSQL si se define SIGT_DATABASE_URL).
Cada prueba crea sus propios datos con nombres únicos, por lo que no dependen unas de otras ni del orden.
"""
import os
import tempfile
import uuid

os.environ["SIGT_DATA_DIR"] = tempfile.mkdtemp()
os.environ["SIGT_ADMIN_USER"] = "admin"
os.environ["SIGT_ADMIN_PASSWORD"] = "clave-admin-123"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

CLAVE_ADMIN = "clave-admin-123"
CLAVE = "clave-segura-123"


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def entrar(c, usuario: str, clave: str = CLAVE):
    """Inicia sesión como `usuario` (descarta la sesión anterior)."""
    c.cookies.clear()
    r = c.post("/api/login", json={"username": usuario, "password": clave})
    assert r.status_code == 200, r.text
    return r.json()


def unico(prefijo: str) -> str:
    return f"{prefijo}{uuid.uuid4().hex[:6]}"


# ---------------------------------------------------------------- fábricas de datos (las usa el administrador)
def crear_area(c, nombre: str | None = None) -> int:
    entrar(c, "admin", CLAVE_ADMIN)
    r = c.post("/api/areas", json={"nombre": nombre or unico("Area ")})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def crear_usuario(c, rol: str, area_id: int | None = None) -> str:
    entrar(c, "admin", CLAVE_ADMIN)
    username = unico(rol[:3] + ".")
    r = c.post("/api/usuarios", json={"username": username, "nombre": f"Usuario {username}", "rol": rol,
                                       "area_id": area_id, "password": CLAVE})
    assert r.status_code == 201, r.text
    return username


def ficha_base(area_id: int, **cambios) -> dict:
    """Indicador de ejemplo: «días acumulados / tickets», menor es mejor, mensual."""
    base = {"codigo": unico("T-").upper(), "nombre": "Tiempo de resolución", "area_id": area_id, "unidad": "días",
            "frecuencia": "mensual", "sentido": "menor", "formula": "dias / tickets", "meta": 2, "limite": 4,
            "variables": [{"clave": "dias", "etiqueta": "Días acumulados"}, {"clave": "tickets", "etiqueta": "Tickets"}]}
    return {**base, **cambios}


def crear_periodo(c, anio: int) -> None:
    """Paso 1 del flujo: crea el período fiscal si aún no existe."""
    entrar(c, "admin", CLAVE_ADMIN)
    r = c.post("/api/ejercicios", json={"anio": anio})
    assert r.status_code in (201, 409), r.text


def presupuestar(c, indicador: dict, valor: float | None = None, anio: int | None = None) -> None:
    """Pasos 1 y 3: crea los períodos fiscales que toquen y presupuesta el indicador (por defecto, su meta, repetida)."""

    from app.dominio import calendario
    entrar(c, "admin", CLAVE_ADMIN)
    vigente = calendario.ejercicio_de_fecha(calendario.hoy())
    for a in ([anio] if anio else [vigente, vigente - 1]):
        crear_periodo(c, a)
        if indicador["frecuencia"] == "eventual":
            continue
        r = c.put(f"/api/ejercicios/{a}/presupuesto/{indicador['id']}",
                  json={"anual": indicador["meta"] if valor is None else valor, "reparto": "repetir"})
        assert r.status_code == 200, r.text


def crear_indicador(c, area_id: int, presupuesto: bool = True, **cambios) -> dict:
    """Crea un indicador y, salvo que se pida lo contrario, ya presupuestado (vigente y año anterior)."""
    entrar(c, "admin", CLAVE_ADMIN)
    r = c.post("/api/indicadores", json=ficha_base(area_id, **cambios))
    assert r.status_code == 201, r.text
    ind = r.json()
    if presupuesto:
        presupuestar(c, ind)
    return ind


@pytest.fixture()
def escenario(client):
    """Un área con su jefe, un gerente y un indicador mensual listo para cargar."""
    area = crear_area(client)
    return {"area": area, "jefe": crear_usuario(client, "jefe", area), "gerente": crear_usuario(client, "gerente"),
            "indicador": crear_indicador(client, area)}


def periodo_actual(c, indicador_id: int, posicion: int = 0) -> str:
    """Código de un período cargable del ejercicio vigente (0 = el actual, 1 = el anterior…) o, si no alcanza, de uno anterior."""

    from app.dominio import calendario
    frecuencia = c.get("/api/indicadores").json()
    frecuencia = next(i["frecuencia"] for i in frecuencia if i["id"] == indicador_id)
    return calendario.periodos_recientes(frecuencia, calendario.hoy(), posicion + 1)[posicion]
