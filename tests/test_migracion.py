import os
import sqlite3
import subprocess
import sys

VIEJO = """CREATE TABLE areas (id INTEGER PRIMARY KEY, nombre VARCHAR(80) UNIQUE);
INSERT INTO areas (nombre) VALUES ('Existente');
CREATE TABLE indicadores (id INTEGER PRIMARY KEY, codigo VARCHAR(20), nombre VARCHAR(150), objetivo TEXT,
  area_id INTEGER, unidad VARCHAR(20), frecuencia VARCHAR(20), sentido VARCHAR(10), formula VARCHAR(300),
  variables JSON, meta FLOAT, limite FLOAT, activo BOOLEAN, creado_en DATETIME);
INSERT INTO indicadores VALUES (1,'OLD-01','Viejo','',1,'%','mensual','mayor','a / b * 100',
  '[{"clave":"a","etiqueta":"A"},{"clave":"b","etiqueta":"B"}]',90,80,1,'2026-01-01 00:00:00');"""

PROGRAMA = ("from app.servicios.arranque import preparar_base; from app.database import SessionLocal; "
            "from app.models import Indicador; preparar_base(); "
            "db = SessionLocal(); i = db.get(Indicador, 1); print(i.codigo, i.decimales, i.constantes)")


def test_la_migracion_agrega_columnas_sin_perder_datos(tmp_path):
    base = tmp_path / "viejo.db"
    with sqlite3.connect(base) as cx:
        cx.executescript(VIEJO)
    env = {**os.environ, "SIGT_DATABASE_URL": f"sqlite:///{base}", "SIGT_DATA_DIR": str(tmp_path)}
    r = subprocess.run([sys.executable, "-c", PROGRAMA], env=env, capture_output=True, text=True, cwd=os.getcwd())
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "OLD-01 None None"
