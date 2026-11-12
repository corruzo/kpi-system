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


def test_la_proyeccion_de_espacio_no_se_inventa_con_poco_historial(client, monkeypatch):
    """Una base recién creada pesa ~10 MB por el motor mismo: eso no es «crecimiento» ni debe alarmar."""
    from app.database import SessionLocal
    MB = 1_048_576
    monkeypatch.setattr(salud, "_tamano_bd", lambda db: {"bytes": 12 * MB, "datos": 1 * MB, "tablas": [], "conexiones": 3})
    entrar(client, "admin", CLAVE_ADMIN)
    with SessionLocal() as db:
        bd = salud.base_de_datos(db)
        assert bd["crecimiento_mb_dia"] is None and bd["dias_restantes"] is None            # pocos días: no se proyecta
        assert not any("se llenaría" in x["titulo"] for x in salud.diagnostico(db, bd))
        assert bd["datos_mb"] == 1.0
    monkeypatch.setattr(salud, "DIAS_MINIMOS_PARA_ESTIMAR", 0)
    monkeypatch.setattr(salud, "_tamano_bd", lambda db: {"bytes": 420 * MB, "datos": 400 * MB, "tablas": [], "conexiones": 3})
    from datetime import timedelta
    futuro = salud.ahora() + timedelta(days=40)                                              # 40 días de historial
    monkeypatch.setattr(salud, "ahora", lambda: futuro)
    with SessionLocal() as db:                                                               # y 400 MB de datos propios: sí avisa
        bd = salud.base_de_datos(db)
        assert bd["crecimiento_mb_dia"] == round(400 / bd["historial_dias"], 3) and bd["dias_restantes"] >= 1   # (la base de pruebas puede traer historial previo)
        assert any("se llenaría" in x["titulo"] for x in salud.diagnostico(db, bd))
