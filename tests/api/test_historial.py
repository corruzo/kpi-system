"""Entrega 3: historial de revisiones de cada carga (qué se devolvió y por qué) e historial de cambios de cada indicador
(quién, qué cambió y cuándo), visible solo para quien tiene el permiso y ve el indicador."""
from conftest import (
    CLAVE_ADMIN,
    arbol,
    crear_indicador,
    crear_usuario,
    entrar,
    id_de_usuario,
    periodo_actual,
    persona,
    unico,
)

from app.dominio import calendario

CARGA = {"dias": 1, "tickets": 1}


def _cargar(client, usuario, ind, periodo):
    entrar(client, usuario)
    r = client.post("/api/mediciones", json={"indicador_id": ind["id"], "periodo": periodo, "valores": CARGA})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_cada_devolucion_aprobacion_y_reapertura_queda_en_el_historial_de_la_carga(client):
    a = arbol(client)
    analista = persona(client, "Analista", miembro=[a["jefatura"]])
    coord = persona(client, "coordinador")
    entrar(client, "admin", CLAVE_ADMIN)
    ind = crear_indicador(client, a["jefatura"], responsable_id=id_de_usuario(client, analista))
    periodo = periodo_actual(client, ind["id"])
    m = _cargar(client, analista, ind, periodo)
    for motivo in ("Falta el soporte del dato", "El total no coincide con el reporte de planta"):
        entrar(client, coord)
        assert client.post(f"/api/mediciones/{m}/revision", json={"accion": "observar", "nota": motivo}).status_code == 200
        _cargar(client, analista, ind, periodo)                                   # corrige y reenvía (misma carga, nueva versión)
    entrar(client, coord)
    assert client.post(f"/api/mediciones/{m}/revision", json={"accion": "aprobar", "nota": "Conforme"}).status_code == 200
    assert client.post(f"/api/mediciones/{m}/reabrir", json={"accion": "observar", "nota": "Se detectó un error en abril"}).status_code == 200

    # quien carga ve TODAS las devoluciones y sus motivos, no solo la última (la nota de la carga se pisa; el historial no)
    entrar(client, analista)
    carga = next(x for x in client.get(f"/api/mediciones?indicador_id={ind['id']}").json() if x["id"] == m)
    assert carga["nota_revision"] == "Se detectó un error en abril"
    historial = carga["revisiones"]                                               # la más reciente primero
    assert [r["accion"] for r in historial] == ["reabierta", "aprobada", "devuelta", "devuelta"]
    assert [r["nota"] for r in historial] == ["Se detectó un error en abril", "Conforme", "El total no coincide con el reporte de planta",
                                              "Falta el soporte del dato"]
    assert all(r["por"] and r["en"] for r in historial)
    # también llega con los períodos de la pantalla de carga
    p = next(x for x in client.get(f"/api/indicadores/{ind['id']}/periodos").json()["periodos"] if x["periodo"] == periodo)
    assert len(p["medicion"]["revisiones"]) == 4


def test_una_carga_sin_revisar_no_tiene_historial_de_revisiones(client, escenario):
    entrar(client, escenario["jefe"])
    ind = escenario["indicador"]
    m = _cargar(client, escenario["jefe"], ind, periodo_actual(client, ind["id"]))
    carga = next(x for x in client.get(f"/api/mediciones?indicador_id={ind['id']}").json() if x["id"] == m)
    assert carga["revisiones"] == [] and carga["estado"] == "enviado"


def test_el_historial_de_cambios_dice_quien_que_y_cuando(client):
    a = arbol(client)
    ana, luis = persona(client, "Analista", miembro=[a["jefatura"]]), persona(client, "Analista", miembro=[a["jefatura"]])
    entrar(client, "admin", CLAVE_ADMIN)
    ind = crear_indicador(client, a["jefatura"], responsable_id=id_de_usuario(client, ana), nombre="Tiempo de respuesta")
    anio = calendario.ejercicio_de_fecha(calendario.hoy())
    cuerpo = {k: ind[k] for k in ("nombre", "nodo_id", "unidad", "frecuencia", "sentido", "formula", "variables", "nivel_optimo", "limite")}
    assert client.put(f"/api/indicadores/{ind['id']}", json={**cuerpo, "nombre": "Tiempo de respuesta al cliente", "nivel_optimo": 3}).status_code == 200
    assert client.put(f"/api/ejercicios/{anio}/metas/{ind['id']}", json={"anual": 5, "reparto": "repetir"}).status_code == 200
    assert client.put(f"/api/usuarios/{id_de_usuario(client, luis)}/indicadores", json={"responsable": [], "suplente": [ind["id"]]}).status_code == 200
    assert client.post(f"/api/indicadores/{ind['id']}/archivar").status_code == 200

    r = client.get(f"/api/indicadores/{ind['id']}/historial")
    assert r.status_code == 200 and int(r.headers["X-Total-Count"]) == len(r.json())
    por_titulo = {}
    for e in r.json():
        por_titulo.setdefault(e["titulo"], e)                                                # la entrada más reciente de cada tipo
    assert [e["titulo"] for e in r.json()][0] == "Indicador archivado"                       # lo más reciente primero
    assert {"Indicador creado", "Ficha editada", "Meta modificada", "Asignación cambiada", "Indicador archivado"} <= set(por_titulo)
    editada = por_titulo["Ficha editada"]
    assert {"campo": "Nombre", "antes": "Tiempo de respuesta", "despues": "Tiempo de respuesta al cliente"} in editada["cambios"]
    assert any(c["campo"] == "Nivel óptimo" and c["despues"] == "3" for c in editada["cambios"])
    assert editada["usuario"] and editada["rol"] and editada["fecha"]
    assert any(c["campo"].startswith("Meta de") and c["antes"] == "2" and c["despues"] == "5" for c in por_titulo["Meta modificada"]["cambios"])
    # el cambio hecho desde «Personas» también aparece en el historial del PROPIO indicador
    asignacion = por_titulo["Asignación cambiada"]
    assert any(c["campo"] == "Suplente" and c["antes"] == "—" and c["despues"] != "—" for c in asignacion["cambios"])
    assert client.get(f"/api/indicadores/{ind['id']}/historial?limite=2&desde=1").json()[0]["id"] == r.json()[1]["id"]    # paginación


def test_el_historial_de_cambios_exige_permiso_y_ver_el_indicador(client):
    a, otra = arbol(client), arbol(client)
    analista = persona(client, "Analista", miembro=[a["jefatura"]])
    entrar(client, "admin", CLAVE_ADMIN)
    ind = crear_indicador(client, a["jefatura"], responsable_id=id_de_usuario(client, analista))
    rol = client.post("/api/roles", json={"nombre": unico("Auditor "), "permisos": {"indicadores.historial": "ver"}}).json()["id"]

    def con_historial(ambito):
        usuario = crear_usuario(client, "jefe")      # cuenta nueva; se le da el rol de solo consultar historial
        entrar(client, "admin", CLAVE_ADMIN)
        uid = id_de_usuario(client, usuario)
        assert client.put(f"/api/usuarios/{uid}/asignacion", json={"rol_id": rol, "raiz": False, "ambito": [ambito], "miembro": []}).status_code == 200
        return usuario

    dentro, fuera = con_historial(a["jefatura"]), con_historial(otra["jefatura"])
    entrar(client, dentro)
    assert client.get(f"/api/indicadores/{ind['id']}/historial").status_code == 200
    entrar(client, fuera)
    assert client.get(f"/api/indicadores/{ind['id']}/historial").status_code == 404           # tiene el permiso, pero no lo ve
    entrar(client, analista)
    assert client.get(f"/api/indicadores/{ind['id']}/historial").status_code == 403           # lo ve, pero su rol no tiene el permiso
