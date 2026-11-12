"""Roles y permisos, anti-escalada, Desarrollador inmutable, cuentas sin rol y asignación de personas."""
from conftest import (
    CLAVE,
    CLAVE_ADMIN,
    arbol,
    crear_indicador,
    crear_nodo,
    cuenta,
    entrar,
    id_de_usuario,
    periodo_actual,
    persona,
    rol_de_sistema,
    unico,
)

from app import permisos as cat


def _rol(client, nombre=None, permisos=None, como="admin"):
    if como == "admin":
        entrar(client, "admin", CLAVE_ADMIN)
    r = client.post("/api/roles", json={"nombre": nombre or unico("Rol "), "permisos": permisos or {"indicadores.ver": "ver"}})
    return r


# ---------------------------------------------------------------- catálogo y matriz
def test_la_matriz_nunca_muestra_permisos_tecnicos_a_nadie(client):
    coord = persona(client, "coordinador")
    entrar(client, coord)
    c = client.get("/api/permisos").json()
    codigos = {p["codigo"] for p in c["permisos"]}
    assert codigos == {p.codigo for p in cat.FUNCIONALES}                       # TODAS las funcionales y solo ellas
    assert not any(p["tecnico"] for p in c["permisos"]) and "Técnico" not in c["grupos"]
    entrar(client, "admin", CLAVE_ADMIN)
    d = client.get("/api/permisos").json()   # ni siquiera el Desarrollador: lo técnico es suyo por definición, no una casilla
    assert {p["codigo"] for p in d["permisos"]} == {p.codigo for p in cat.FUNCIONALES} and "Técnico" not in d["grupos"]


def test_el_alcance_no_es_editable_y_los_niveles_se_validan(client):
    entrar(client, "admin", CLAVE_ADMIN)
    assert _rol(client, permisos={"metas.cargar": "ver"}).status_code == 422          # ese permiso solo admite «modificar»
    assert _rol(client, permisos={"indicadores.ver": "modificar"}).status_code == 422  # ese solo admite «ver»
    assert _rol(client, permisos={"no.existe": "ver"}).status_code == 422
    r = _rol(client, permisos={"metas.copiar": "modificar"}).json()
    assert {"metas.cargar", "metas.ver", "indicadores.ver", "ejercicios.ver"} <= set(r["permisos"])   # lo que necesita para servir
    assert r["resumen"] and any("Metas" in f for f in r["resumen"])


# ---------------------------------------------------------------- anti-escalada
def test_los_permisos_tecnicos_no_se_conceden_a_ningun_rol_ni_por_el_desarrollador(client):
    entrar(client, "admin", CLAVE_ADMIN)
    assert _rol(client, permisos={"bitacora.ver": "ver"}).status_code == 403
    assert _rol(client, permisos={"respaldo.restaurar": "modificar"}).status_code == 403
    coord = persona(client, "coordinador")
    entrar(client, coord)
    assert _rol(client, permisos={"usuarios.cuentas": "modificar"}, como=None).status_code == 403


def test_nadie_concede_un_permiso_que_no_posee(client):
    entrar(client, "admin", CLAVE_ADMIN)
    delegado = _rol(client, "Delegado " + unico(""), {"roles.gestionar": "modificar", "usuarios.asignar": "modificar"}).json()
    quien = persona_con_rol(client, delegado["id"])
    entrar(client, quien)
    assert _rol(client, permisos={"usuarios.ver": "ver"}, como=None).status_code == 201            # lo tiene (implicado)
    assert _rol(client, permisos={"metas.cargar": "modificar"}, como=None).status_code == 403      # no lo tiene
    assert _rol(client, permisos={"cargas.aprobar": "modificar"}, como=None).status_code == 403


def persona_con_rol(client, rol_id_):
    entrar(client, "admin", CLAVE_ADMIN)
    username = cuenta(client, "del")
    uid = id_de_usuario(client, username)
    entrar(client, "admin", CLAVE_ADMIN)
    assert client.put(f"/api/usuarios/{uid}/asignacion", json={"rol_id": rol_id_, "raiz": False, "ambito": [], "miembro": []}).status_code == 200
    return username


def test_el_coordinador_no_toca_al_desarrollador_ni_su_propio_rol(client):
    coord = persona(client, "coordinador")
    entrar(client, "admin", CLAVE_ADMIN)
    id_dev, id_coord = id_de_usuario(client, "admin"), id_de_usuario(client, coord)
    rol_dev, rol_coord = rol_de_sistema(client, "desarrollador"), rol_de_sistema(client, "coordinador")
    entrar(client, coord)
    assert rol_dev not in {r["id"] for r in client.get("/api/roles").json()}                 # ni lo ve
    assert client.put(f"/api/roles/{rol_dev}", json={"nombre": "Desarrollador", "permisos": {}}).status_code == 404
    assert client.delete(f"/api/roles/{rol_dev}").status_code == 404
    assert id_dev not in {u["id"] for u in client.get("/api/usuarios?limite=500").json()}    # el Desarrollador es invisible para él
    for url, cuerpo in ((f"/api/usuarios/{id_dev}/asignacion", {"rol_id": rol_coord, "raiz": False, "ambito": [], "miembro": []}),
                        (f"/api/usuarios/{id_dev}/alcance", None), (f"/api/usuarios/{id_dev}/indicadores", None)):
        r = client.put(url, json=cuerpo) if cuerpo else client.get(url)
        assert r.status_code == 404, url
    assert client.put(f"/api/usuarios/{id_dev}", json={"nombre": "x" * 5, "activo": False}).status_code == 403   # sin usuarios.cuentas
    # ni cambia su propio rol, ámbito ni permisos
    assert client.put(f"/api/roles/{rol_coord}", json={"nombre": "Coordinador SGC", "permisos": {"roles.gestionar": "modificar"}}).status_code == 403
    r = client.put(f"/api/usuarios/{id_coord}/asignacion", json={"rol_id": None, "raiz": True, "ambito": [], "miembro": []})
    assert r.status_code == 403
    assert client.delete(f"/api/roles/{rol_coord}").status_code == 403
    # ni crea cuentas
    assert client.post("/api/usuarios", json={"username": unico("x."), "nombre": "No debe", "password": CLAVE}).status_code == 403


def test_solo_el_desarrollador_da_o_quita_el_rol_coordinador(client):
    coord = persona(client, "coordinador")
    otra = cuenta(client)
    uid = id_de_usuario(client, otra)
    entrar(client, coord)
    rol_coord = next(r["id"] for r in client.get("/api/roles").json() if r["clave"] == "coordinador")
    r = client.put(f"/api/usuarios/{uid}/asignacion", json={"rol_id": rol_coord, "raiz": False, "ambito": [], "miembro": []})
    assert r.status_code == 403 and "Desarrollador" in r.json()["detail"]
    entrar(client, "admin", CLAVE_ADMIN)
    assert client.put(f"/api/usuarios/{uid}/asignacion", json={"rol_id": rol_coord, "raiz": False, "ambito": [], "miembro": []}).status_code == 200


def test_el_rol_desarrollador_no_se_edita_ni_se_vacia_ni_se_da_por_la_asignacion(client):
    entrar(client, "admin", CLAVE_ADMIN)
    rol_dev = rol_de_sistema(client, "desarrollador")
    assert client.put(f"/api/roles/{rol_dev}", json={"nombre": "Desarrollador", "permisos": {}}).status_code == 403
    assert client.delete(f"/api/roles/{rol_dev}").status_code == 403
    dev = next(r for r in client.get("/api/roles").json() if r["id"] == rol_dev)
    assert dev["editable"] is False and set(dev["permisos"]) == {p.codigo for p in cat.CATALOGO}
    otra = id_de_usuario(client, cuenta(client))
    entrar(client, "admin", CLAVE_ADMIN)
    assert client.put(f"/api/usuarios/{otra}/asignacion", json={"rol_id": rol_dev, "raiz": False, "ambito": [], "miembro": []}).status_code == 422
    yo = id_de_usuario(client, "admin")
    entrar(client, "admin", CLAVE_ADMIN)
    assert client.put(f"/api/usuarios/{yo}", json={"nombre": "Desarrollador", "activo": False}).status_code == 422       # ni inhabilitarse
    assert client.post(f"/api/usuarios/{yo}/desarrollador", json={"activar": False, "password": CLAVE_ADMIN}).status_code == 422   # ni quitarse el rol
    assert client.delete(f"/api/usuarios/{yo}").status_code == 422


def test_designar_otro_desarrollador_es_un_procedimiento_explicito(client):
    nuevo = cuenta(client, "dev")
    uid = id_de_usuario(client, nuevo)
    entrar(client, "admin", CLAVE_ADMIN)
    assert client.post(f"/api/usuarios/{uid}/desarrollador", json={"activar": True, "password": "incorrecta-1"}).status_code == 401
    r = client.post(f"/api/usuarios/{uid}/desarrollador", json={"activar": True, "password": CLAVE_ADMIN})
    assert r.status_code == 200 and r.json()["rol"] == "Desarrollador"
    entrar(client, nuevo)
    assert client.get("/api/bitacora").status_code == 200                             # tiene lo técnico
    coord = persona(client, "coordinador")
    entrar(client, coord)
    assert uid not in {u["id"] for u in client.get("/api/usuarios?limite=500").json()}  # invisible para el Coordinador
    entrar(client, "admin", CLAVE_ADMIN)
    assert client.post(f"/api/usuarios/{uid}/desarrollador", json={"activar": False, "password": CLAVE_ADMIN}).status_code == 200
    assert client.get("/api/usuarios?q=" + nuevo).json()[0]["pendiente"] is True


# ---------------------------------------------------------------- ciclo de vida de los roles
def test_crear_duplicar_renombrar_y_borrar_roles(client):
    entrar(client, "admin", CLAVE_ADMIN)
    r = _rol(client, nombre="Rol " + unico(""), permisos={"cargas.cargar": "modificar"}).json()
    assert _rol(client, nombre=r["nombre"].upper()).status_code == 422                       # nombre repetido
    copia = client.post(f"/api/roles/{r['id']}/duplicar", json={"nombre": "Copia " + unico("")})
    assert copia.status_code == 201 and copia.json()["permisos"] == r["permisos"] and copia.json()["de_sistema"] is False
    nuevo = "Renombrado " + unico("")
    ed = client.put(f"/api/roles/{r['id']}", json={"nombre": nuevo, "descripcion": "otra", "permisos": {"cargas.cargar": "modificar", "panel.ver": "ver"}})
    assert ed.status_code == 200 and ed.json()["nombre"] == nuevo and "panel.ver" in ed.json()["permisos"]
    p = persona_con_rol(client, copia.json()["id"])
    entrar(client, "admin", CLAVE_ADMIN)
    assert client.delete(f"/api/roles/{copia.json()['id']}").status_code == 409              # alguien lo usa
    assert next(x for x in client.get("/api/roles").json() if x["id"] == copia.json()["id"])["usuarios"] == 1
    assert client.delete(f"/api/roles/{r['id']}").status_code == 200
    assert client.delete(f"/api/roles/{rol_de_sistema(client, 'coordinador')}").status_code == 403   # los de sistema no se borran
    assert p


def test_un_cambio_de_permisos_surte_efecto_en_la_siguiente_peticion_y_queda_en_bitacora(client):
    entrar(client, "admin", CLAVE_ADMIN)
    r = _rol(client, nombre="Efecto " + unico(""), permisos={"cargas.ver": "ver"}).json()
    quien = persona_con_rol(client, r["id"])
    entrar(client, quien)
    assert client.get("/api/mediciones").status_code == 200
    coord = persona(client, "coordinador")
    entrar(client, coord)
    assert client.put(f"/api/roles/{r['id']}", json={"nombre": r["nombre"], "permisos": {"estructura.ver": "ver"}}).status_code == 200
    entrar(client, quien)    # (la sesión ya abierta tampoco guardaba permisos: se leen por petición)
    assert client.get("/api/mediciones").status_code == 403 and client.get("/api/unidades").status_code == 200
    entrar(client, "admin", CLAVE_ADMIN)
    acciones = {b["accion"] for b in client.get("/api/bitacora?limite=60").json()}
    assert {"ROL_CREADO", "ROL_EDITADO", "USUARIO_ASIGNADO"} <= acciones
    cambio = next(b for b in client.get("/api/bitacora?accion=ROL_EDITADO&limite=5").json() if b["detalle"]["nombre"] == r["nombre"])
    assert "cargas.ver" in cambio["detalle"]["cambios"]["permisos"] and cambio["rol"] == "Coordinador SGC"


def test_el_coordinador_no_puede_dejar_su_rol_sin_los_permisos_minimos(client):
    entrar(client, "admin", CLAVE_ADMIN)
    rol_coord = rol_de_sistema(client, "coordinador")
    r = client.put(f"/api/roles/{rol_coord}", json={"nombre": "Coordinador SGC", "permisos": {"panel.ver": "ver"}})
    assert r.status_code == 422 and "no puede quedar sin" in r.json()["detail"]


# ---------------------------------------------------------------- cuenta pendiente de asignación
def test_una_cuenta_sin_rol_no_accede_a_nada_salvo_a_su_cuenta(client):
    sin = cuenta(client, "pend")
    entrar(client, sin)
    me = client.get("/api/me").json()
    assert me["pendiente"] is True and me["rol"] is None and me["permisos"] == {}
    arr = client.get("/api/arranque").json()
    assert set(arr) == {"usuario", "parametros"} and set(arr["parametros"]) == {"empresa", "logo_url"}
    for url in ("/api/indicadores", "/api/mediciones", "/api/unidades", "/api/usuarios", "/api/roles", "/api/ejercicios", "/api/tablero",
                "/api/reportes/general.xlsx", "/api/bandeja", "/api/parametros", "/api/catalogos", "/api/bitacora", "/api/recordatorios"):
        assert client.get(url).status_code == 403, url
    assert client.post("/api/tour", json={"visto": True}).status_code == 200                       # su cuenta sí
    assert client.post("/api/cambiar-clave", json={"actual": CLAVE, "nueva": "otra-clave-muy-larga-1"}).status_code == 200
    assert client.post("/api/logout").status_code == 200


# ---------------------------------------------------------------- asignación y casos de carga
def test_asignar_posicion_y_alcance_con_vista_previa(client):
    a = arbol(client)
    otra = cuenta(client)
    uid = id_de_usuario(client, otra)
    entrar(client, "admin", CLAVE_ADMIN)
    rol_jefe = next(r["id"] for r in client.get("/api/roles").json() if r["nombre"] == "Jefe") if any(r["nombre"] == "Jefe" for r in client.get("/api/roles").json()) else None
    if rol_jefe is None:
        persona(client, "Jefe")
        entrar(client, "admin", CLAVE_ADMIN)
        rol_jefe = next(r["id"] for r in client.get("/api/roles").json() if r["nombre"] == "Jefe")
    ind = crear_indicador(client, a["jefatura"], nombre="en la jefatura")
    crear_indicador(client, a["gerencia"], nombre="de la gerencia")
    antes = client.get(f"/api/usuarios/{uid}/alcance").json()
    assert antes["pendiente"] and antes["total"] == 0
    prev = client.post(f"/api/usuarios/{uid}/alcance", json={"rol_id": rol_jefe, "raiz": False, "ambito": [a["jefatura"]], "miembro": []}).json()
    assert prev["total"] == 1 and prev["indicadores"][0]["id"] == ind["id"] and prev["indicadores"][0]["motivo"] == "ámbito"
    assert [n["id"] for n in prev["nodos"]] == [a["jefatura"]]
    assert client.get(f"/api/usuarios/{uid}/alcance").json()["total"] == 0                       # la vista previa no guardó nada
    assert client.put(f"/api/usuarios/{uid}/asignacion", json={"rol_id": rol_jefe, "raiz": False, "ambito": [a["jefatura"]], "miembro": []}).status_code == 200
    assert client.get(f"/api/usuarios/{uid}/alcance").json()["total"] == 1
    assert client.put(f"/api/usuarios/{uid}/asignacion", json={"rol_id": rol_jefe, "raiz": False, "ambito": [987654], "miembro": []}).status_code == 422
    assert client.put(f"/api/usuarios/{uid}/asignacion", json={"rol_id": rol_jefe, "raiz": False, "ambito": [a["jefatura"]], "miembro": [a["jefatura"]]}).status_code == 422


def test_casos_de_carga_solo_el_jefe_solo_el_gerente_analista_y_varios_analistas(client):
    nodo = arbol(client)["jefatura"]
    jefe = persona(client, "Jefe", ambito=[nodo])
    gerente = persona(client, "Gerente", ambito=[nodo])
    a1, a2 = persona(client, "Analista", miembro=[nodo]), persona(client, "Analista", miembro=[nodo])
    entrar(client, "admin", CLAVE_ADMIN)
    uid = lambda u: id_de_usuario(client, u)       # noqa: E731
    casos = {"solo_jefe": (uid(jefe), [uid(jefe)]), "solo_gerente": (uid(gerente), [uid(gerente)]),
             "analista_y_jefe_responsable": (uid(jefe), [uid(a1)]), "varios_analistas": (uid(jefe), [uid(a1), uid(a2)])}
    inds = {k: crear_indicador(client, nodo, responsable_id=r, cargadores=c, nombre=k) for k, (r, c) in casos.items()}
    quien_carga = {"solo_jefe": [jefe], "solo_gerente": [gerente], "analista_y_jefe_responsable": [a1], "varios_analistas": [a1, a2]}
    for caso, ind in inds.items():
        for u in (jefe, gerente, a1, a2):
            entrar(client, u)
            periodo = periodo_actual(client, ind["id"])
            r = client.post("/api/mediciones", json={"indicador_id": ind["id"], "periodo": periodo, "valores": {"dias": 1, "tickets": 1}})
            if u in quien_carga[caso]:
                assert r.status_code in (201, 409), (caso, u, r.text)     # 409 si otro cargador ya cargó este período
                if r.status_code == 409:
                    assert "ya fue cargado" in r.json()["detail"]
            else:   # quien lo ve por su ámbito pero no lo carga recibe 403; quien ni siquiera lo ve (analista ajeno), 404
                assert r.status_code == (403 if u in (jefe, gerente) else 404), (caso, u, r.status_code)
    entrar(client, a2)
    assert client.get("/api/arranque").json()["indicadores"] and {i["id"] for i in client.get("/api/arranque").json()["indicadores"]} == {inds["varios_analistas"]["id"]}


def test_traspasar_responsabilidad_y_no_dejar_un_indicador_sin_cargador(client):
    nodo = crear_nodo(client)
    a, b = persona(client, "Jefe", miembro=[nodo]), persona(client, "Jefe", miembro=[nodo])
    entrar(client, "admin", CLAVE_ADMIN)
    ia, ib = id_de_usuario(client, a), id_de_usuario(client, b)
    ind = crear_indicador(client, nodo, responsable_id=ia, cargadores=[ia])
    entrar(client, "admin", CLAVE_ADMIN)
    r = client.put(f"/api/usuarios/{ia}/indicadores", json={"responsable": [], "cargador": [ind["id"]]})
    assert r.status_code == 409 and "traspasa" in r.json()["detail"]                    # la responsabilidad no se «quita»
    r = client.put(f"/api/usuarios/{ia}/indicadores", json={"responsable": [ind["id"]], "cargador": []})
    assert r.status_code == 409 and "sin nadie que lo cargue" in r.json()["detail"]
    assert client.put(f"/api/usuarios/{ib}/indicadores", json={"responsable": [ind["id"]], "cargador": [ind["id"]]}).status_code == 200
    assert client.put(f"/api/usuarios/{ia}/indicadores", json={"responsable": [], "cargador": []}).status_code == 200   # ya traspasado y con otro cargador
    visto = client.put(f"/api/indicadores/{ind['id']}/asignacion", json={"nodo_id": nodo, "responsable_id": ib, "cargadores": [ib]}).json()
    assert visto["responsable_id"] == ib and visto["cargadores"] == [ib]
    assert client.put(f"/api/indicadores/{ind['id']}/asignacion", json={"nodo_id": nodo, "responsable_id": ib, "cargadores": []}).status_code == 422


def test_inhabilitar_a_un_responsable_sigue_bloqueado_hasta_reasignar(client):
    nodo = crear_nodo(client)
    p = persona(client, "Jefe", miembro=[nodo])
    entrar(client, "admin", CLAVE_ADMIN)
    uid = id_de_usuario(client, p)
    crear_indicador(client, nodo, responsable_id=uid, cargadores=[uid])
    entrar(client, "admin", CLAVE_ADMIN)
    r = client.put(f"/api/usuarios/{uid}", json={"nombre": "Nombre Nuevo", "activo": False})
    assert r.status_code == 409 and "reasígnelos" in r.json()["detail"]
    assert client.delete(f"/api/usuarios/{uid}").status_code == 409
    r = client.put(f"/api/usuarios/{uid}/asignacion", json={"rol_id": None, "raiz": False, "ambito": [], "miembro": []})
    assert r.status_code == 409                                                           # tampoco se le quita el rol con indicadores
