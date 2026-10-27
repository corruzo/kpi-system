"""Protección CSRF: las peticiones que modifican datos desde otro origen se rechazan."""
from conftest import CLAVE_ADMIN

LOGIN = {"username": "admin", "password": CLAVE_ADMIN}


def _post(client, **cabeceras):
    client.cookies.clear()
    return client.post("/api/login", json=LOGIN, headers=cabeceras)


def test_origen_ajeno_se_rechaza(client):
    r = _post(client, Origin="https://sitio-malicioso.example")
    assert r.status_code == 403
    assert "sigt_sesion" not in r.cookies


def test_origen_null_se_rechaza(client):
    assert _post(client, Origin="null").status_code == 403


def test_sec_fetch_site_cruzado_se_rechaza(client):
    assert _post(client, **{"Sec-Fetch-Site": "cross-site"}).status_code == 403
    assert _post(client, **{"Sec-Fetch-Site": "same-site"}).status_code == 403


def test_mismo_origen_se_acepta(client):
    assert _post(client, Origin="http://testserver", **{"Sec-Fetch-Site": "same-origin"}).status_code == 200


def test_sin_cabeceras_de_navegador_se_acepta(client):
    assert _post(client).status_code == 200


def test_metodos_seguros_no_se_filtran(client):
    assert client.get("/api/publico", headers={"Origin": "https://otro.example"}).status_code == 200


def test_put_y_delete_tambien_se_filtran(client):
    _post(client)
    ajeno = {"Origin": "https://sitio-malicioso.example"}
    assert client.put("/api/areas/1", json={"nombre": "X"}, headers=ajeno).status_code == 403
    assert client.delete("/api/areas/1", headers=ajeno).status_code == 403
