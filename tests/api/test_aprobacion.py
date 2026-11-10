"""Aprobación jerárquica: el revisor es el superior más cercano; el Coordinador SGC es respaldo; nadie aprueba lo propio."""
import pytest
from conftest import CLAVE_ADMIN, arbol, crear_indicador, entrar, id_de_usuario, periodo_actual, persona


def _cargar(client, usuario, ind):
    entrar(client, usuario)
    r = client.post("/api/mediciones", json={"indicador_id": ind["id"], "periodo": periodo_actual(client, ind["id"]),
                                             "valores": {"dias": 1, "tickets": 1}})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _aprobar(client, usuario, medicion_id):
    entrar(client, usuario)
    return client.post(f"/api/mediciones/{medicion_id}/revision", json={"accion": "aprobar", "nota": ""})


def _en_bandeja(client, usuario, medicion_id):
    entrar(client, usuario)
    return medicion_id in {m["id"] for m in client.get("/api/bandeja?limite=500").json()}


@pytest.fixture()
def casa(client):
    """Gerencia → departamento → jefatura, con gerente (gerencia), jefe (jefatura), analista y Coordinador SGC."""
    a = arbol(client)
    p = {"gerente": persona(client, "Gerente", ambito=[a["gerencia"]]), "jefe": persona(client, "Jefe", ambito=[a["jefatura"]]),
         "analista": persona(client, "Analista", miembro=[a["jefatura"]]), "coord": persona(client, "coordinador")}
    entrar(client, "admin", CLAVE_ADMIN)
    uid = {k: id_de_usuario(client, v) for k, v in p.items()}
    ind = crear_indicador(client, a["jefatura"], responsable_id=uid["jefe"], cargadores=[uid["analista"], uid["jefe"]])
    return {"a": a, "p": p, "uid": uid, "ind": ind}


def test_aprueba_el_superior_directo_y_no_el_de_mas_arriba(client, casa):
    p = casa["p"]
    m = _cargar(client, p["analista"], casa["ind"])
    assert _en_bandeja(client, p["jefe"], m) and not _en_bandeja(client, p["gerente"], m) and _en_bandeja(client, p["coord"], m)
    assert _aprobar(client, p["gerente"], m).status_code == 403                 # el jefe es el superior directo
    assert _aprobar(client, p["analista"], m).status_code == 403                # ni siquiera tiene el permiso
    r = _aprobar(client, p["jefe"], m)
    assert r.status_code == 200 and r.json()["estado"] == "aprobado"
    assert not _en_bandeja(client, p["jefe"], m)


def test_el_coordinador_sgc_puede_aprobar_siempre_como_respaldo(client, casa):
    p = casa["p"]
    m = _cargar(client, p["analista"], casa["ind"])
    assert _aprobar(client, p["coord"], m).status_code == 200
    entrar(client, "admin", CLAVE_ADMIN)
    b = next(x for x in client.get("/api/bitacora?accion=APROBACION&limite=5").json() if x["entidad_id"] == m)
    assert b["rol"] == "Coordinador SGC"                                         # queda en bitácora quién y con qué rol


def test_escala_al_nivel_siguiente_si_no_hay_aprobador_en_el_nivel_cercano(client):
    a = arbol(client)                              # el jefe solo existe en el departamento; la jefatura no tiene aprobador
    jefe_depto = persona(client, "Jefe", ambito=[a["depto"]])
    gerente = persona(client, "Gerente", ambito=[a["gerencia"]])
    analista = persona(client, "Analista", miembro=[a["jefatura"]])
    entrar(client, "admin", CLAVE_ADMIN)
    ind = crear_indicador(client, a["jefatura"], responsable_id=id_de_usuario(client, jefe_depto), cargadores=[id_de_usuario(client, analista)])
    m = _cargar(client, analista, ind)
    assert _en_bandeja(client, jefe_depto, m) and not _en_bandeja(client, gerente, m)
    assert _aprobar(client, gerente, m).status_code == 403
    assert _aprobar(client, jefe_depto, m).status_code == 200


def test_si_hay_varios_aprobadores_en_el_mismo_nivel_cualquiera_aprueba(client):
    a = arbol(client)
    j1, j2 = persona(client, "Jefe", ambito=[a["jefatura"]]), persona(client, "Jefe", ambito=[a["jefatura"]])
    analista = persona(client, "Analista", miembro=[a["jefatura"]])
    entrar(client, "admin", CLAVE_ADMIN)
    ind = crear_indicador(client, a["jefatura"], responsable_id=id_de_usuario(client, j1), cargadores=[id_de_usuario(client, analista)])
    m = _cargar(client, analista, ind)
    assert _en_bandeja(client, j1, m) and _en_bandeja(client, j2, m)
    assert _aprobar(client, j2, m).status_code == 200


def test_nadie_aprueba_una_carga_propia_y_el_aprobador_se_busca_hacia_arriba(client, casa):
    p = casa["p"]
    m = _cargar(client, p["jefe"], casa["ind"])                                   # carga el propio jefe
    assert _aprobar(client, p["jefe"], m).status_code == 403                       # segregación de funciones
    assert not _en_bandeja(client, p["jefe"], m)
    assert _en_bandeja(client, p["gerente"], m)                                    # sube un nivel: el gerente
    assert _aprobar(client, p["gerente"], m).status_code == 200


def test_ni_siquiera_un_rol_de_sistema_aprueba_lo_que_el_mismo_cargo(client, casa):
    entrar(client, "admin", CLAVE_ADMIN)
    propio = crear_indicador(client, casa["a"]["jefatura"], nombre="cargado por el Desarrollador")   # el Desarrollador es su cargador
    r = client.post("/api/mediciones", json={"indicador_id": propio["id"], "periodo": periodo_actual(client, propio["id"]),
                                             "valores": {"dias": 1, "tickets": 1}})
    assert r.status_code == 201
    assert client.post(f"/api/mediciones/{r.json()['id']}/revision", json={"accion": "aprobar", "nota": ""}).status_code == 403


def test_autor_gerente_general_aprueba_el_coordinador(client):
    """Quien carga es el gerente general (ámbito raíz, sin permiso de aprobar) y ningún otro aprobador cubre su indicador."""
    nodo = arbol(client)["gerencia"]
    gg = persona(client, "Gerente general", raiz=True)
    coord = persona(client, "coordinador")
    entrar(client, "admin", CLAVE_ADMIN)
    ind = crear_indicador(client, nodo, responsable_id=id_de_usuario(client, gg), cargadores=[id_de_usuario(client, gg)])
    m = _cargar(client, gg, ind)
    assert _en_bandeja(client, coord, m)
    assert _aprobar(client, gg, m).status_code == 403
    assert _aprobar(client, coord, m).status_code == 200


def test_devolver_exige_motivo_y_reabrir_sigue_la_misma_regla(client, casa):
    p = casa["p"]
    m = _cargar(client, p["analista"], casa["ind"])
    entrar(client, p["jefe"])
    assert client.post(f"/api/mediciones/{m}/revision", json={"accion": "observar", "nota": ""}).status_code == 422
    r = client.post(f"/api/mediciones/{m}/revision", json={"accion": "observar", "nota": "Falta soporte del dato"})
    assert r.status_code == 200 and r.json()["estado"] == "observado"
    entrar(client, p["analista"])                                             # corrige y reenvía
    assert client.post("/api/mediciones", json={"indicador_id": casa["ind"]["id"], "periodo": periodo_actual(client, casa["ind"]["id"]),
                                                "valores": {"dias": 1, "tickets": 1}}).status_code == 201
    assert _aprobar(client, p["jefe"], m).status_code == 200
    entrar(client, p["gerente"])
    assert client.post(f"/api/mediciones/{m}/reabrir", json={"accion": "observar", "nota": "Se detectó un error"}).status_code == 403
    entrar(client, p["jefe"])
    r = client.post(f"/api/mediciones/{m}/reabrir", json={"accion": "observar", "nota": "Se detectó un error"})
    assert r.status_code == 200 and r.json()["estado"] == "observado"
    entrar(client, "admin", CLAVE_ADMIN)
    acciones = [b["accion"] for b in client.get("/api/bitacora?limite=40").json() if b["entidad_id"] == m]
    assert {"OBSERVACION", "APROBACION", "REAPERTURA", "REENVIO", "CARGA"} <= set(acciones)


def test_la_bandeja_y_su_resumen_cuentan_solo_lo_que_le_toca_a_cada_quien(client, casa):
    p = casa["p"]
    m = _cargar(client, p["analista"], casa["ind"])
    entrar(client, p["jefe"])
    assert client.get("/api/bandeja/resumen").json()["total"] >= 1
    assert client.get("/api/arranque").json()["bandeja_total"] == client.get("/api/bandeja/resumen").json()["total"]
    entrar(client, p["gerente"])
    assert m not in {x["id"] for x in client.get("/api/bandeja?limite=500").json()}
    assert client.get("/api/bandeja/resumen").json()["total"] == 0
    assert client.get("/api/mediciones?estado=enviado").status_code == 200       # (ve la carga en el historial de su ámbito, pero no es suya de aprobar)
