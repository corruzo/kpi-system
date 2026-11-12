"""Salud del sistema: solo el Desarrollador; el diagnóstico detecta problemas reales de datos y de fórmulas."""
from conftest import CLAVE_ADMIN, crear_indicador, crear_nodo, entrar, persona

from app.servicios import salud


def test_la_salud_es_solo_del_desarrollador(client):
    entrar(client, "admin", CLAVE_ADMIN)
    d = client.get("/api/sistema/salud")
    assert d.status_code == 200
    j = d.json()
    assert {"estado", "conteo", "alertas", "base_de_datos", "despliegue", "cadena", "bitacora", "accesos"} <= set(j)
    assert j["cadena"]["ok"] and j["base_de_datos"]["migracion"]["al_dia"]
    assert 0 <= j["base_de_datos"]["porcentaje"] <= 100
    assert "password" not in str(j).lower()                     # nunca expone secretos
    entrar(client, persona(client, "coordinador"))
    assert client.get("/api/sistema/salud").status_code == 403
    assert client.get("/api/sistema/externos").status_code == 403


def test_el_diagnostico_detecta_umbrales_y_formulas_problematicas(client):
    from app.database import SessionLocal
    from app.models import Indicador
    entrar(client, "admin", CLAVE_ADMIN)
    ind = crear_indicador(client, crear_nodo(client))
    with SessionLocal() as db:
        i = db.get(Indicador, ind["id"])
        i.sentido, i.nivel_optimo, i.limite = "mayor", 80, 95        # el rojo queda del lado bueno del verde
        i.formula = "a / b"
        i.variables = [{"clave": "a", "etiqueta": "A"}, {"clave": "b", "etiqueta": "B"}]
        db.flush()
        titulos = " | ".join(x["titulo"] for x in salud.diagnostico(db))
        assert "semáforo incoherente" in titulos and "división entre cero" in titulos
        i.formula = "a +"
        db.flush()
        assert any(x["nivel"] == "critico" and "fórmula" in x["titulo"] for x in salud.diagnostico(db))
        db.rollback()
