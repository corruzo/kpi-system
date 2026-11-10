"""Barrido de permisos: TODA ruta de la API × cada rol de prueba, y coherencia del catálogo con las rutas.

Nota de ingeniería: en FastAPI reciente `app.routes` envuelve a los routers incluidos, de modo que un barrido sobre `app.routes`
no recorre ninguna ruta de la API. Aquí se recorren los routers declarados (`conftest.rutas_de_la_api`).
"""
import pytest
from conftest import CLAVE_ADMIN, arbol, cuenta, entrar, persona, rutas_de_la_api

from app import permisos as cat
from app import permisos_doc

PUBLICAS = {"/api/login", "/api/logout", "/api/publico", "/api/logo"}   # sin sesión (logout debe poder cerrar una sesión ya vencida)
CUENTA_PROPIA = {"/api/me", "/api/cambiar-clave", "/api/tour", "/api/arranque"}   # cualquier sesión válida, con o sin rol


_declaracion = permisos_doc.declaracion


def _url(path: str) -> str:
    for marcador in ("{indicador_id}", "{medicion_id}", "{usuario_id}", "{unidad_id}", "{rol_id}", "{elemento_id}"):
        path = path.replace(marcador, "987654")
    return path.replace("{anio}", "2001")   # año sin crear: ninguna ruta del barrido puede cerrar, reabrir ni cambiar nada real


RUTAS = list(rutas_de_la_api())


def test_hay_rutas_que_barrer():
    assert len(RUTAS) > 60                                                       # (la v1 recorría 0 rutas por el cambio de FastAPI)


def test_ninguna_ruta_queda_sin_permiso_declarado():
    sin = [f"{m} {r.path}" for m, _, r in RUTAS if _declaracion(r) is None]
    assert not sin, "rutas sin permiso declarado: " + ", ".join(sin)
    assert {r.path for _, _, r in RUTAS if _declaracion(r) == "publica"} <= PUBLICAS
    assert {r.path for _, _, r in RUTAS if _declaracion(r) == "cuenta"} == CUENTA_PROPIA


def test_el_catalogo_cubre_literalmente_todas_las_rutas_y_no_sobra_ningun_permiso():
    usados = set()
    for _, _, r in RUTAS:
        d = _declaracion(r)
        if isinstance(d, set):
            usados |= d
    assert usados == set(cat.POR_CODIGO), f"sin usar: {set(cat.POR_CODIGO) - usados}; fuera del catálogo: {usados - set(cat.POR_CODIGO)}"


@pytest.fixture(scope="module")
def roles_de_prueba(client):
    nodo = arbol(client)["jefatura"]
    entrar(client, "admin", CLAVE_ADMIN)
    return {"desarrollador": ("admin", CLAVE_ADMIN), "coordinador": (persona(client, "coordinador"), None),
            "jefe": (persona(client, "Jefe", ambito=[nodo]), None), "analista": (persona(client, "Analista", miembro=[nodo]), None),
            "gerente_general": (persona(client, "Gerente general", raiz=True), None), "sin_rol": (cuenta(client), None)}


def _permisos_de(client, usuario, clave):
    return entrar(client, usuario, clave) if clave else entrar(client, usuario)


@pytest.mark.parametrize("rol", ["desarrollador", "coordinador", "jefe", "analista", "gerente_general", "sin_rol"])
def test_barrido_ruta_por_rol_403_sin_permiso_y_otra_cosa_con_permiso(client, roles_de_prueba, rol):
    usuario, clave = roles_de_prueba[rol]
    yo = _permisos_de(client, usuario, clave)
    propios = yo["permisos"]
    errores = []
    for metodo, path, ruta in RUTAS:
        d = _declaracion(ruta)
        if d in ("publica", "cuenta"):
            continue
        permitido = any(cat.alcanza(propios.get(c), cat.POR_CODIGO[c].minimo) for c in d)
        if metodo == "POST" and path in ("/api/sistema/reiniciar", "/api/respaldo/restaurar") and permitido:
            continue                                                             # destructivas: se prueban en su propio caso
        r = client.request(metodo, _url(path), json={} if metodo in ("POST", "PUT") else None, headers={"Origin": "http://testserver"})
        if not permitido and r.status_code != 403:
            errores.append(f"{rol}: {metodo} {path} sin permiso respondió {r.status_code} (debía ser 403)")
        if permitido and r.status_code in (401, 403):
            errores.append(f"{rol}: {metodo} {path} con permiso respondió {r.status_code}")
    assert not errores, "\n".join(errores)


def test_sin_sesion_todo_responde_401_salvo_lo_publico(client):
    client.cookies.clear()
    for metodo, path, _ in RUTAS:
        if path in PUBLICAS:
            continue
        r = client.request(metodo, _url(path), headers={"Origin": "http://testserver"})
        assert r.status_code in (401, 403), f"{metodo} {path} → {r.status_code}"
        assert r.status_code == 401 or path == "/api/login", f"{metodo} {path} → {r.status_code}"


def test_lo_no_visible_responde_404_y_lo_visible_sin_permiso_403(client, roles_de_prueba):
    """Con permiso de ver pero sobre un recurso inexistente/ajeno: 404; sin el permiso de la acción: 403 (no se confunden)."""
    usuario, _ = roles_de_prueba["analista"]
    entrar(client, usuario)
    assert client.get("/api/indicadores/987654/ficha").status_code == 404
    assert client.post("/api/indicadores/987654/archivar").status_code == 403    # no tiene indicadores.archivar
    usuario, _ = roles_de_prueba["jefe"]
    entrar(client, usuario)
    assert client.post("/api/indicadores/987654/archivar").status_code == 404    # tiene el permiso, el indicador no es visible
