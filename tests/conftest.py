"""Configuración común de las pruebas: base temporal, cliente HTTP y fábricas de datos de la versión 2.

La base se crea una sola vez por sesión de pruebas (SQLite temporal, o PostgreSQL si se define SIGT_DATABASE_URL).
Cada prueba crea sus propios datos con nombres únicos, por lo que no dependen unas de otras ni del orden.

Personas de prueba (todas se crean con el Desarrollador `admin` y se asignan con `persona`):
  analista  — carga datos donde es cargador; sin ámbito (solo ve lo que le asignan)
  jefe      — Analista + aprueba, crea/edita sus indicadores, metas; ámbito en un nodo
  gerente   — igual que jefe (otro nombre de rol), normalmente con ámbito en una gerencia o en la raíz
  coordinador — rol de sistema «Coordinador SGC»
"""
import os
import tempfile
import uuid

os.environ["SIGT_DATA_DIR"] = tempfile.mkdtemp()
os.environ["SIGT_ADMIN_USER"] = "admin"
os.environ["SIGT_ADMIN_PASSWORD"] = "clave-admin-123"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import security  # noqa: E402
from app.main import app  # noqa: E402

security.ITERACIONES = 1_000   # solo en pruebas: con las 210 000 de producción crear cada persona tarda ~0,2 s y la suite se vuelve lenta

CLAVE_ADMIN = "clave-admin-123"   # el Desarrollador `admin`
CLAVE = "clave-segura-123"

# Roles definidos por el Coordinador que usan las pruebas (se crean al primer uso).
ROLES = {
    "Analista": {"cargas.cargar": "modificar", "reportes.general": "ver", "reportes.fichas": "ver"},
    "Jefe": {"cargas.cargar": "modificar", "cargas.aprobar": "modificar", "cargas.reabrir": "modificar", "cargas.notas": "modificar",
             "indicadores.crear": "modificar", "indicadores.editar": "modificar", "indicadores.archivar": "modificar",
             "indicadores.eliminar": "modificar", "indicadores.asignar": "modificar", "formulas.probar": "modificar",
             "metas.cargar": "modificar", "metas.copiar": "modificar", "panel.ver": "ver", "reportes.general": "ver",
             "reportes.fichas": "ver", "reportes.verificar": "ver", "recordatorios.enviar": "modificar", "catalogos.gestionar": "modificar"},
    "Gerente general": {"indicadores.ver": "ver", "cargas.ver": "ver", "metas.ver": "ver", "panel.ver": "ver", "reportes.general": "ver",
                        "reportes.fichas": "ver", "ejercicios.ver": "ver", "estructura.ver": "ver", "usuarios.ver": "ver",
                        "cargas.cargar": "modificar", "indicadores.editar": "modificar", "indicadores.archivar": "modificar"},
}
ROLES["Gerente"] = ROLES["Jefe"]
_ROLES_CREADOS: dict[str, int] = {}


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


def como_dev(c):
    return entrar(c, "admin", CLAVE_ADMIN)


# ---------------------------------------------------------------- estructura
def crear_nodo(c, nombre: str | None = None, nivel: str = "gerencia", padre_id: int | None = None) -> int:
    como_dev(c)
    r = c.post("/api/unidades", json={"nombre": nombre or unico("Nodo "), "nivel": nivel, "padre_id": padre_id})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def crear_area(c, nombre: str | None = None) -> int:
    """Un nodo donde colgar indicadores (una gerencia nueva)."""
    return crear_nodo(c, nombre, "gerencia")


def arbol(c) -> dict:
    """Gerencia → departamento → jefatura (ids), todo nuevo."""
    g = crear_nodo(c, unico("Gerencia "), "gerencia")
    d = crear_nodo(c, unico("Depto "), "departamento", g)
    j = crear_nodo(c, unico("Jefatura "), "jefatura", d)
    return {"gerencia": g, "depto": d, "jefatura": j}


# ---------------------------------------------------------------- roles y personas
def rol_id(c, nombre: str) -> int:
    """Id de un rol de prueba (lo crea el Desarrollador la primera vez)."""
    if nombre not in _ROLES_CREADOS:
        como_dev(c)
        r = c.post("/api/roles", json={"nombre": nombre, "descripcion": "de prueba", "permisos": ROLES[nombre]})
        if r.status_code == 422:   # ya existía (otra sesión de pruebas sobre la misma base)
            r = next(x for x in c.get("/api/roles").json() if x["nombre"] == nombre)
            _ROLES_CREADOS[nombre] = r["id"]
        else:
            assert r.status_code == 201, r.text
            _ROLES_CREADOS[nombre] = r.json()["id"]
    return _ROLES_CREADOS[nombre]


def rol_de_sistema(c, clave: str) -> int:
    como_dev(c)
    return next(r["id"] for r in c.get("/api/roles").json() if r["clave"] == clave)


def cuenta(c, prefijo: str = "usr") -> str:
    """Cuenta nueva SIN rol (la crea el Desarrollador)."""
    como_dev(c)
    username = unico(prefijo + ".")
    r = c.post("/api/usuarios", json={"username": username, "nombre": f"Usuario {username}", "password": CLAVE})
    assert r.status_code == 201, r.text
    return username


def persona(c, rol: str, ambito: list[int] | None = None, miembro: list[int] | None = None, raiz: bool = False,
            prefijo: str | None = None) -> str:
    """Cuenta nueva con su rol («Analista», «Jefe», «Gerente», «Gerente general» o «coordinador») y su posición."""
    username = cuenta(c, prefijo or rol[:3].lower())
    uid = id_de_usuario(c, username)
    como_dev(c)
    rid = rol_de_sistema(c, "coordinador") if rol == "coordinador" else rol_id(c, rol)
    como_dev(c)
    r = c.put(f"/api/usuarios/{uid}/asignacion", json={"rol_id": rid, "raiz": raiz, "ambito": ambito or [], "miembro": miembro or []})
    assert r.status_code == 200, r.text
    return username


JEFES_POR_AREA: dict[int, int] = {}   # último analista creado con `crear_usuario` en cada nodo: carga por defecto los indicadores nuevos


def crear_usuario(c, rol: str, area_id: int | None = None) -> str:
    """Compatibilidad con las pruebas de la versión 1: «jefe» = quien carga (Analista que trabaja en el nodo),
    «gerente» = rol con ámbito en toda la empresa, «admin» = Coordinador SGC."""
    if rol == "jefe":
        u = persona(c, "Analista", miembro=[area_id] if area_id else [], prefijo="jef")
        JEFES_POR_AREA[area_id] = id_de_usuario(c, u)
        return u
    if rol == "gerente":
        return persona(c, "Gerente", raiz=True, prefijo="ger")
    return persona(c, "coordinador", raiz=False, prefijo="adm")


def id_de_usuario(c, username: str) -> int:
    como_dev(c)
    r = c.get(f"/api/usuarios?q={username}&limite=50")
    assert r.status_code == 200, r.text
    return next(u["id"] for u in r.json() if u["username"] == username)


# ---------------------------------------------------------------- indicadores y metas
def ficha_base(nodo_id: int, **cambios) -> dict:
    """Indicador de ejemplo: «días acumulados / tickets», menor es mejor, mensual."""
    base = {"codigo": unico("T-").upper(), "nombre": "Tiempo de resolución", "nodo_id": nodo_id, "unidad": "días",
            "frecuencia": "mensual", "sentido": "menor", "formula": "dias / tickets", "nivel_optimo": 2, "limite": 4,
            "variables": [{"clave": "dias", "etiqueta": "Días acumulados"}, {"clave": "tickets", "etiqueta": "Tickets"}]}
    return {**base, **cambios}


def crear_periodo(c, anio: int) -> None:
    """Paso 1 del flujo: crea el período fiscal si aún no existe."""
    como_dev(c)
    r = c.post("/api/ejercicios", json={"anio": anio})
    assert r.status_code in (201, 409), r.text


def fijar_metas(c, indicador: dict, valor: float | None = None, anio: int | None = None) -> None:
    """Pasos 1 y 3: crea los períodos fiscales que toquen y fija la meta del indicador (por defecto, su nivel óptimo, repetido)."""
    from app.dominio import calendario
    como_dev(c)
    vigente = calendario.ejercicio_de_fecha(calendario.hoy())
    for a in ([anio] if anio else [vigente, vigente - 1]):
        crear_periodo(c, a)
        if indicador["frecuencia"] == "eventual":
            continue
        r = c.put(f"/api/ejercicios/{a}/metas/{indicador['id']}",
                  json={"anual": indicador["nivel_optimo"] if valor is None else valor, "reparto": "repetir"})
        assert r.status_code == 200, r.text


def crear_indicador(c, nodo_id: int, meta: bool = True, **cambios) -> dict:
    """Crea un indicador (lo hace el Desarrollador) y, salvo que se pida lo contrario, con meta (vigente y año anterior).
    `encargado_id` = responsable y cargador a la vez; por defecto, el analista creado en ese nodo con `crear_usuario`."""
    como_dev(c)
    if "encargado_id" not in cambios and "responsable_id" not in cambios and nodo_id in JEFES_POR_AREA:
        cambios["encargado_id"] = JEFES_POR_AREA[nodo_id]
    if "encargado_id" in cambios:
        e = cambios.pop("encargado_id")
        cambios.setdefault("responsable_id", e)
        cambios.setdefault("cargadores", [e])
    cuerpo = ficha_base(nodo_id, **cambios)
    r = c.post("/api/indicadores", json=cuerpo)
    assert r.status_code == 201, r.text
    ind = r.json()
    if meta:
        fijar_metas(c, ind)
    return ind


@pytest.fixture()
def escenario(client):
    """Un nodo con su analista (carga), un gerente (ámbito global) y un indicador mensual listo para cargar."""
    nodo = crear_area(client)
    analista = crear_usuario(client, "jefe", nodo)
    return {"area": nodo, "jefe": analista, "gerente": crear_usuario(client, "gerente"),
            "indicador": crear_indicador(client, nodo, responsable_id=id_de_usuario(client, analista),
                                         cargadores=[id_de_usuario(client, analista)])}


def periodo_actual(c, indicador_id: int, posicion: int = 0) -> str:
    """Código de un período cargable del ejercicio vigente (0 = el actual, 1 = el anterior…) o, si no alcanza, de uno anterior.
    Lee la frecuencia de la base directamente: NO toca la sesión de la prueba (quien llama sigue siendo el mismo usuario)."""
    from app.database import SessionLocal
    from app.dominio import calendario
    from app.models import Indicador
    with SessionLocal() as db:
        frecuencia = db.get(Indicador, indicador_id).frecuencia
    return calendario.periodos_recientes(frecuencia, calendario.hoy(), posicion + 1)[posicion]


def rutas_de_la_api():
    """(método, ruta, dependencias) de TODA ruta `/api/*` real. En FastAPI reciente `app.routes` envuelve a los routers
    (`_IncludedRouter`), por lo que se recorren los routers declarados."""
    from app.api.routers import ROUTERS
    for router in ROUTERS:
        for ruta in router.routes:
            if ruta.path.startswith("/api/"):
                for metodo in sorted(ruta.methods - {"HEAD", "OPTIONS"}):
                    yield metodo, ruta.path, ruta
