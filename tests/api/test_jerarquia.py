"""Cruce rol × árbol × asignación: los ejemplos de aceptación de la sección 4 del diseño de la versión 2."""
import pytest
from conftest import (
    CLAVE_ADMIN,
    arbol,
    crear_indicador,
    crear_nodo,
    entrar,
    id_de_usuario,
    periodo_actual,
    persona,
    unico,
)


@pytest.fixture()
def empresa(client):
    """Dos gerencias con su árbol, las personas de los ejemplos y un indicador de cada tipo."""
    rrhh = arbol(client)                                     # Gerencia RRHH → Depto → Jefatura
    sst = crear_nodo(client, unico("SST "), "departamento", rrhh["gerencia"])
    prod = arbol(client)                                     # otra gerencia
    uid = lambda u: id_de_usuario(client, u)                 # noqa: E731
    gg = persona(client, "Gerente general", raiz=True, prefijo="gg")
    g_rrhh = persona(client, "Gerente", ambito=[rrhh["gerencia"]], prefijo="grh")
    g_prod = persona(client, "Gerente", ambito=[prod["gerencia"]], prefijo="gpr")
    par = persona(client, "Gerente", ambito=[rrhh["gerencia"]], prefijo="par")          # otro gerente con el mismo ámbito
    jefe2 = persona(client, "Jefe", ambito=[rrhh["jefatura"], prod["jefatura"]], prefijo="j2")   # dos jefaturas
    analista = persona(client, "Analista", prefijo="ana")                                # sin ámbito
    ind = {
        "gerente": crear_indicador(client, rrhh["gerencia"], responsable_id=uid(g_rrhh), nombre="del gerente RRHH"),
        "jefatura": crear_indicador(client, rrhh["jefatura"], responsable_id=uid(jefe2), suplente_id=uid(analista), nombre="de la jefatura RRHH"),
        "jefatura2": crear_indicador(client, prod["jefatura"], responsable_id=uid(jefe2), nombre="de la jefatura Prod"),
        "sst": crear_indicador(client, sst, responsable_id=uid(g_rrhh), nombre="de SST"),
        "prod": crear_indicador(client, prod["gerencia"], responsable_id=uid(g_prod), nombre="del gerente Prod"),
        "del_par": crear_indicador(client, rrhh["depto"], responsable_id=uid(par), nombre="del par"),
    }
    return {"gg": gg, "g_rrhh": g_rrhh, "g_prod": g_prod, "par": par, "jefe2": jefe2, "analista": analista, "ind": ind,
            "rrhh": rrhh, "prod": prod, "sst": sst}


def ids_visibles(client, usuario):
    entrar(client, usuario)
    return {i["id"] for i in client.get("/api/indicadores").json()}


def test_el_gerente_general_ve_absolutamente_todo(client, empresa):
    todos = {i["id"] for i in empresa["ind"].values()}
    assert todos <= ids_visibles(client, empresa["gg"])


def test_el_gerente_de_rrhh_ve_su_gerencia_y_sus_departamentos_y_no_la_otra(client, empresa):
    ind = empresa["ind"]
    ver = ids_visibles(client, empresa["g_rrhh"])
    assert {ind[k]["id"] for k in ("gerente", "jefatura", "sst", "del_par")} <= ver
    assert ind["prod"]["id"] not in ver
    assert ind["jefatura2"]["id"] not in ver        # la jefatura de la otra gerencia no cuelga de la suya


def test_un_jefe_con_dos_jefaturas_ve_ambas_completas(client, empresa):
    ind = empresa["ind"]
    ver = ids_visibles(client, empresa["jefe2"])
    assert {ind["jefatura"]["id"], ind["jefatura2"]["id"]} <= ver
    assert ind["gerente"]["id"] not in ver and ind["sst"]["id"] not in ver


def test_la_visibilidad_no_sube_un_jefe_no_ve_lo_propio_de_su_gerente(client, empresa):
    entrar(client, empresa["jefe2"])
    ind = empresa["ind"]["gerente"]
    assert client.get(f"/api/indicadores/{ind['id']}/ficha").status_code == 404
    assert client.get(f"/api/indicadores/{ind['id']}/periodos").status_code == 404
    assert ind["id"] not in ids_visibles(client, empresa["jefe2"])


def test_el_analista_sin_ambito_solo_ve_lo_que_le_asignaron(client, empresa):
    assert ids_visibles(client, empresa["analista"]) == {empresa["ind"]["jefatura"]["id"]}


def _ficha(i):
    return {k: i[k] for k in ("nombre", "nodo_id", "unidad", "frecuencia", "sentido", "formula", "variables", "nivel_optimo", "limite")}


def test_quien_tiene_el_permiso_edita_lo_de_su_ambito_pero_no_carga_datos_ni_fija_metas_de_un_par(client, empresa):
    """La edición depende del permiso del rol y del ÁMBITO, no de ser el responsable. Cargar sigue siendo solo del responsable
    principal y del suplente; las metas, solo de quienes están debajo."""
    from app.dominio import calendario
    anio = calendario.ejercicio_de_fecha(calendario.hoy())
    ajeno = empresa["ind"]["del_par"]     # de otro gerente con su mismo ámbito (par suyo, no está debajo de él)
    entrar(client, empresa["g_rrhh"])
    assert client.get(f"/api/indicadores/{ajeno['id']}/ficha").status_code == 200
    assert client.put(f"/api/indicadores/{ajeno['id']}", json=_ficha(ajeno)).status_code == 200            # su ámbito: edita
    assert client.post(f"/api/indicadores/{ajeno['id']}/archivar").status_code == 200
    assert client.post(f"/api/indicadores/{ajeno['id']}/restaurar").status_code == 200
    assert client.post("/api/mediciones", json={"indicador_id": ajeno["id"], "periodo": periodo_actual(client, ajeno["id"]),
                                                "valores": {"dias": 1, "tickets": 1}}).status_code == 403   # no es su cargador
    assert client.put(f"/api/ejercicios/{anio}/metas/{ajeno['id']}", json={"anual": 3, "reparto": "repetir"}).status_code == 403   # par: no está debajo
    fuera = empresa["ind"]["prod"]        # otra gerencia: ni siquiera lo ve
    assert client.put(f"/api/indicadores/{fuera['id']}", json=_ficha(fuera)).status_code == 404
    assert client.delete(f"/api/indicadores/{ajeno['id']}").status_code == 200


def test_responsable_y_suplente_solo_cargan_no_editan_la_ficha(client, empresa):
    """El suplente carga pero no edita la ficha (su rol no lo permite); el responsable principal, cuyo rol sí lo permite, edita por su ámbito."""
    ind = empresa["ind"]["jefatura"]
    entrar(client, empresa["analista"])                                            # suplente, sin permiso de editar
    assert client.put(f"/api/indicadores/{ind['id']}", json=_ficha(ind)).status_code == 403
    assert client.post("/api/mediciones", json={"indicador_id": ind["id"], "periodo": periodo_actual(client, ind["id"]),
                                                "valores": {"dias": 1, "tickets": 1}}).status_code == 201
    entrar(client, empresa["jefe2"])                                               # responsable principal con rol que sí puede editar: su ámbito
    assert client.put(f"/api/indicadores/{ind['id']}", json=_ficha(ind)).status_code == 200


def test_un_gerente_fija_la_meta_de_quienes_estan_debajo_y_edita_su_ambito(client, empresa):
    from app.dominio import calendario
    anio = calendario.ejercicio_de_fecha(calendario.hoy())
    propio, de_abajo = empresa["ind"]["gerente"], empresa["ind"]["jefatura"]
    entrar(client, empresa["g_rrhh"])
    assert client.post(f"/api/indicadores/{propio['id']}/archivar").status_code == 200
    assert client.post(f"/api/indicadores/{propio['id']}/restaurar").status_code == 200
    assert client.put(f"/api/ejercicios/{anio}/metas/{de_abajo['id']}", json={"anual": 3, "reparto": "repetir"}).status_code == 200
    assert client.put(f"/api/indicadores/{de_abajo['id']}", json=_ficha(de_abajo)).status_code == 200      # en su ámbito


def test_el_gerente_general_solo_consulta_y_carga_lo_que_tiene_asignado(client, empresa):
    """Rol «Gerente general»: ve todo; no edita fichas (su rol no lo permite) y solo carga lo que tiene asignado."""
    gg = empresa["gg"]
    entrar(client, "admin", CLAVE_ADMIN)
    mio = crear_indicador(client, empresa["rrhh"]["gerencia"], responsable_id=id_de_usuario(client, gg),
                          nombre="del gerente general")
    ajeno = empresa["ind"]["gerente"]
    entrar(client, gg)
    assert client.get(f"/api/indicadores/{ajeno['id']}/ficha").status_code == 200
    assert client.put(f"/api/indicadores/{ajeno['id']}", json=_ficha(ajeno)).status_code == 403
    assert client.put(f"/api/indicadores/{mio['id']}", json=_ficha(mio)).status_code == 403
    assert client.post("/api/mediciones", json={"indicador_id": ajeno["id"], "periodo": periodo_actual(client, ajeno["id"]),
                                                "valores": {"dias": 1, "tickets": 1}}).status_code == 403
    assert client.post("/api/mediciones", json={"indicador_id": mio["id"], "periodo": periodo_actual(client, mio["id"]),
                                                "valores": {"dias": 1, "tickets": 1}}).status_code == 201
    for url in ("/api/bitacora", "/api/respaldo", "/api/usuarios/1/cerrar-sesiones", "/api/sistema/desbloquear-accesos"):
        assert client.request("POST" if "respaldo" in url or "cerrar" in url or "desbloq" in url else "GET", url, json={"frase": "x" * 12}).status_code == 403, url


def test_el_gerente_general_se_construye_solo_con_la_pantalla_de_roles(client):
    """Sin código especial: un rol de solo ver + ámbito en la raíz."""
    entrar(client, "admin", CLAVE_ADMIN)
    permisos = {"indicadores.ver": "ver", "cargas.ver": "ver", "metas.ver": "ver", "panel.ver": "ver", "reportes.general": "ver",
                "reportes.fichas": "ver", "ejercicios.ver": "ver"}
    r = client.post("/api/roles", json={"nombre": unico("Gerente general "), "permisos": permisos})
    assert r.status_code == 201
    assert set(r.json()["permisos"]) == set(permisos)           # nada más (no se cuela ningún permiso técnico ni de escritura)


def test_crear_y_asignar_solo_a_si_mismo_o_a_personas_debajo(client, empresa):
    """Un jefe de RRHH no puede crear un indicador fuera de su rama ni asignarlo a un par o a un superior."""
    nodo_prod = empresa["prod"]["gerencia"]
    entrar(client, empresa["g_rrhh"])
    from conftest import ficha_base
    uid = lambda u: id_de_usuario(client, u)       # noqa: E731
    entrar(client, "admin", CLAVE_ADMIN)
    ids = {u: uid(u) for u in (empresa["g_rrhh"], empresa["par"], empresa["jefe2"], empresa["analista"], empresa["gg"])}
    entrar(client, empresa["g_rrhh"])
    fuera = client.post("/api/indicadores", json=ficha_base(nodo_prod, nombre="fuera de mi rama"))
    assert fuera.status_code == 403                                                 # nodo ajeno
    aqui = empresa["rrhh"]["depto"]
    assert client.post("/api/indicadores", json=ficha_base(aqui, responsable_id=ids[empresa["par"]])).status_code == 403   # par
    assert client.post("/api/indicadores", json=ficha_base(aqui, responsable_id=ids[empresa["gg"]])).status_code == 403    # superior
    ok = client.post("/api/indicadores", json=ficha_base(aqui, responsable_id=ids[empresa["g_rrhh"]], suplente_id=ids[empresa["analista"]]))
    assert ok.status_code == 403                                                   # el analista aún no tiene posición: no está «debajo»
    # el analista no está «debajo» (no trabaja en ningún nodo de su ámbito): se rechaza hasta que se le dé posición
    entrar(client, "admin", CLAVE_ADMIN)
    r = client.put(f"/api/usuarios/{ids[empresa['analista']]}/asignacion",
                   json={"rol_id": next(x["id"] for x in client.get("/api/roles").json() if x["nombre"] == "Analista"),
                         "raiz": False, "ambito": [], "miembro": [empresa["rrhh"]["jefatura"]]})
    assert r.status_code == 200
    entrar(client, empresa["g_rrhh"])
    abajo = client.post("/api/indicadores", json=ficha_base(aqui, responsable_id=ids[empresa["jefe2"]], suplente_id=ids[empresa["analista"]]))
    assert abajo.status_code == 201, abajo.text                                    # jefe2 (ámbito inferior) y analista (miembro) están debajo
