"""El reinicio de fábrica se prueba en una base propia: borra todo, así que no puede compartir la de las demás pruebas."""
import os
import subprocess
import sys
import textwrap


def test_reinicio_de_fabrica(tmp_path):
    programa = textwrap.dedent("""
        import os
        from fastapi.testclient import TestClient
        from app.main import app
        from app.database import SessionLocal
        from app.models import Area, Bitacora, Indicador, Medicion, Usuario

        with TestClient(app) as c:
            c.post("/api/login", json={"username": "admin", "password": "clave-admin-123"})
            area = c.post("/api/areas", json={"nombre": "Sistemas"}).json()["id"]
            c.post("/api/usuarios", json={"username": "jefe", "nombre": "Jefe", "rol": "jefe", "area_id": area, "password": "clave-segura-123"})
            c.post("/api/indicadores", json={"codigo": "X-1", "nombre": "Indicador", "area_id": area, "unidad": "%", "frecuencia": "mensual",
                   "sentido": "mayor", "formula": "a / b * 100", "meta": 90, "limite": 80,
                   "variables": [{"clave": "a", "etiqueta": "A"}, {"clave": "b", "etiqueta": "B"}]})
            r = c.post("/api/sistema/reiniciar", json={"confirmacion": "borrar", "password": "clave-admin-123"})
            assert r.status_code == 422, r.text
            r = c.post("/api/sistema/reiniciar", json={"confirmacion": "BORRAR TODO", "password": "incorrecta"})
            assert r.status_code == 401, r.text
            c.cookies.clear()
            c.post("/api/login", json={"username": "jefe", "password": "clave-segura-123"})
            assert c.post("/api/sistema/reiniciar", json={"confirmacion": "BORRAR TODO", "password": "clave-segura-123"}).status_code == 403
            c.cookies.clear()
            c.post("/api/login", json={"username": "admin", "password": "clave-admin-123"})
            r = c.post("/api/sistema/reiniciar", json={"confirmacion": "BORRAR TODO", "password": "clave-admin-123"})
            assert r.status_code == 200, r.text
            with SessionLocal() as db:
                assert [u.username for u in db.query(Usuario)] == ["admin"]
                assert db.query(Area).count() == db.query(Indicador).count() == db.query(Medicion).count() == db.query(Bitacora).count() == 0
            assert c.get("/api/me").status_code == 200                      # la sesión del administrador sigue viva
            assert c.get("/api/indicadores").json() == [] and c.get("/api/areas").json() == []
            assert c.get("/api/bitacora/verificar").json()["total"] == 0
            assert c.get("/api/parametros").json()["empresa"]                # parámetros de fábrica
            assert c.post("/api/areas", json={"nombre": "Nueva"}).status_code == 201   # el sistema vuelve a funcionar
        print("OK")
    """)
    env = {**os.environ, "SIGT_DATA_DIR": str(tmp_path), "SIGT_ADMIN_USER": "admin", "SIGT_ADMIN_PASSWORD": "clave-admin-123"}
    env.pop("SIGT_DATABASE_URL", None)
    r = subprocess.run([sys.executable, "-c", programa], env=env, capture_output=True, text=True, cwd=os.getcwd())
    assert r.returncode == 0 and "OK" in r.stdout, r.stdout + r.stderr
