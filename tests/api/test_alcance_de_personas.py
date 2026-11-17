"""Personas y estructura con la misma regla que los indicadores: cada quien ve solo lo que está debajo de él."""
from conftest import CLAVE_ADMIN, crear_nodo, entrar, persona, unico


def _empresa(client):
    g = crear_nodo(client, unico("Producción "), "gerencia")
    d = crear_nodo(client, unico("Planta "), "departamento", g)
    l1, l2 = crear_nodo(client, unico("Línea "), "jefatura", d), crear_nodo(client, unico("Línea "), "jefatura", d)
    otra = crear_nodo(client, unico("Administración "), "gerencia")
    gente = {"gerente": persona(client, "Gerente general", ambito=[g]), "jefe1": persona(client, "Gerente general", ambito=[l1]),
             "ana1": persona(client, "Analista", miembro=[l1]), "ana2": persona(client, "Analista", miembro=[l2]),
             "admin_otra": persona(client, "Analista", miembro=[otra]), "par": persona(client, "Gerente general", ambito=[g]),
             "todo": persona(client, "Gerente general", raiz=True)}
    return {"g": g, "d": d, "l1": l1, "l2": l2, "otra": otra}, gente


def _ve(client, quien):
    entrar(client, quien)
    return {x["username"] for x in client.get("/api/usuarios?limite=500").json()}, {x["id"] for x in client.get("/api/unidades").json()}


def test_cada_quien_ve_solo_a_las_personas_y_la_rama_que_tiene_debajo(client):
    n, p = _empresa(client)
    personas, nodos = _ve(client, p["gerente"])
    assert {p["gerente"], p["jefe1"], p["ana1"], p["ana2"]} <= personas            # él y su gente
    assert not ({p["admin_otra"], p["par"], p["todo"]} & personas)                  # ni otra gerencia, ni pares, ni superiores
    assert {n["g"], n["d"], n["l1"], n["l2"]} <= nodos and n["otra"] not in nodos   # su rama, no la vecina
    personas, nodos = _ve(client, p["jefe1"])
    assert personas == {p["jefe1"], p["ana1"]}
    assert {n["g"], n["d"], n["l1"]} <= nodos and not ({n["l2"], n["otra"]} & nodos)   # el camino hasta la raíz, no las hermanas
    personas, nodos = _ve(client, p["todo"])                                          # alcance global: todo
    assert {p["gerente"], p["admin_otra"], p["par"]} <= personas and {n["otra"], n["l2"]} <= nodos


def test_no_se_puede_consultar_a_alguien_fuera_del_alcance(client):
    _, p = _empresa(client)
    entrar(client, "admin", CLAVE_ADMIN)
    ajeno = next(x["id"] for x in client.get(f"/api/usuarios?q={p['admin_otra']}&limite=5").json())
    entrar(client, p["gerente"])
    assert client.get(f"/api/usuarios/{ajeno}/alcance").status_code == 404
