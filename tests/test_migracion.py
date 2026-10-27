"""Migraciones de Alembic: base antigua, base nueva, equivalencia con los modelos, ida y vuelta, y política de arranque.

Cada caso corre en un proceso aparte (el motor de la app se crea al importar) con su propia base SQLite temporal.
"""
import os
import sqlite3
import subprocess
import sys

SECRETO = "s" * 40

ANTIGUA = """CREATE TABLE areas (id INTEGER PRIMARY KEY, nombre VARCHAR(80) UNIQUE);
INSERT INTO areas (nombre) VALUES ('Existente');
CREATE TABLE indicadores (id INTEGER PRIMARY KEY, codigo VARCHAR(20), nombre VARCHAR(150), objetivo TEXT,
  area_id INTEGER, unidad VARCHAR(20), frecuencia VARCHAR(20), sentido VARCHAR(10), formula VARCHAR(300),
  variables JSON, meta FLOAT, limite FLOAT, activo BOOLEAN, creado_en DATETIME);
INSERT INTO indicadores VALUES (1,'OLD-01','Viejo','',1,'%','mensual','mayor','a / b * 100',
  '[{"clave":"a","etiqueta":"A"},{"clave":"b","etiqueta":"B"}]',90,80,1,'2026-01-01 00:00:00');"""


def correr(tmp_path, codigo: str, **entorno) -> subprocess.CompletedProcess:
    env = {**os.environ, "SIGT_DATABASE_URL": f"sqlite:///{tmp_path / 'base.db'}", "SIGT_DATA_DIR": str(tmp_path),
           "SIGT_SECRET": SECRETO, **entorno}
    return subprocess.run([sys.executable, "-c", codigo], env=env, capture_output=True, text=True, cwd=os.getcwd())


def correr_ok(tmp_path, codigo: str, **entorno) -> str:
    r = correr(tmp_path, codigo, **entorno)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def test_una_base_anterior_a_alembic_se_completa_sin_perder_datos(tmp_path):
    with sqlite3.connect(tmp_path / "base.db") as cx:
        cx.executescript(ANTIGUA)
    salida = correr_ok(tmp_path, (
        "from app.servicios.arranque import preparar_base; from app.servicios import migraciones; "
        "from app.database import SessionLocal; from app.models import Indicador; preparar_base(); "
        "db = SessionLocal(); i = db.get(Indicador, 1); "
        "print(i.codigo, i.decimales, i.constantes, migraciones.revision_actual() == migraciones.revision_cabeza())"))
    assert salida == "OLD-01 None None True"
    with sqlite3.connect(tmp_path / "base.db") as cx:
        tablas = {f[0] for f in cx.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"usuarios", "bitacora", "intentos_fallidos", "alembic_version"} <= tablas


def test_el_esquema_migrado_coincide_con_los_modelos(tmp_path):
    """Si alguien cambia un modelo sin escribir su migración, esta prueba falla."""
    salida = correr_ok(tmp_path, (
        "from alembic.autogenerate import compare_metadata; from alembic.runtime.migration import MigrationContext; "
        "from app import models; from app.database import Base, engine; from app.servicios import migraciones; "
        "migraciones.actualizar(); cx = engine.connect(); "
        "print(compare_metadata(MigrationContext.configure(cx, opts={'compare_type': True}), Base.metadata))"))
    assert salida == "[]"


def test_se_puede_bajar_a_cero_y_volver_a_subir(tmp_path):
    salida = correr_ok(tmp_path, (
        "from alembic import command; from app.servicios import migraciones as m; from sqlalchemy import inspect; "
        "from app.database import engine; cfg = m.configuracion(); command.upgrade(cfg, 'head'); "
        "command.downgrade(cfg, 'base'); print(sorted(inspect(engine).get_table_names())); "
        "command.upgrade(cfg, 'head'); print(m.esta_al_dia())"))
    assert salida.splitlines() == ["['alembic_version']", "True"]


def test_en_produccion_la_app_verifica_pero_no_migra(tmp_path):
    codigo = "from app.servicios.arranque import preparar_base; preparar_base(); print('listo')"
    r = correr(tmp_path, codigo, SIGT_ENV="production")
    assert r.returncode != 0 and "alembic upgrade head" in r.stderr
    with sqlite3.connect(tmp_path / "base.db") as cx:   # y no creó ni una tabla
        assert not cx.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuarios'").fetchall()


def test_en_produccion_con_la_base_migrada_arranca(tmp_path):
    correr_ok(tmp_path, "from app.servicios import migraciones; migraciones.actualizar()")
    assert correr_ok(tmp_path, "from app.servicios.arranque import preparar_base; preparar_base(); print('listo')",
                     SIGT_ENV="production") == "listo"


def test_en_produccion_se_puede_optar_por_migrar_al_arrancar(tmp_path):
    codigo = "from app.servicios.arranque import preparar_base; preparar_base(); print('listo')"
    assert correr_ok(tmp_path, codigo, SIGT_ENV="production", SIGT_AUTO_MIGRATE="1") == "listo"


def test_la_migracion_3_cifra_la_clave_de_reportes_existente_y_se_puede_revertir(tmp_path):
    correr_ok(tmp_path, ("from alembic import command; from app.servicios import migraciones as m; "
                         "command.upgrade(m.configuracion(), '0002')"))
    with sqlite3.connect(tmp_path / "base.db") as cx:
        cx.execute("INSERT INTO parametros (clave, valor) VALUES ('clave_reportes', 'texto-plano-123')")
    salida = correr_ok(tmp_path, (
        "from alembic import command; from app import cifrado; from app.database import engine; "
        "from app.servicios import migraciones as m; from sqlalchemy import text; cfg = m.configuracion(); "
        "leer = lambda: engine.connect().execute(text(\"SELECT valor FROM parametros WHERE clave='clave_reportes'\")).scalar(); "
        "command.upgrade(cfg, 'head'); v = leer(); print(v.startswith('fernet:'), 'texto-plano' in v, cifrado.descifrar(v)); "
        "command.downgrade(cfg, '0002'); print(leer())"))
    assert salida.splitlines() == ["True False texto-plano-123", "texto-plano-123"]
