"""Migraciones de Alembic: base nueva (esquema v2), equivalencia con los modelos, ida y vuelta, y política de arranque.

Cada caso corre en un proceso aparte (el motor de la app se crea al importar) con su propia base SQLite temporal.
"""
import os
import sqlite3
import subprocess
import sys

SECRETO = "s" * 40


def correr(tmp_path, codigo: str, **entorno) -> subprocess.CompletedProcess:
    env = {**os.environ, "SIGT_DATABASE_URL": f"sqlite:///{tmp_path / 'base.db'}", "SIGT_DATA_DIR": str(tmp_path),
           "SIGT_SECRET": SECRETO, **entorno}
    return subprocess.run([sys.executable, "-c", codigo], env=env, capture_output=True, text=True, cwd=os.getcwd())


def correr_ok(tmp_path, codigo: str, **entorno) -> str:
    r = correr(tmp_path, codigo, **entorno)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


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


def test_en_vercel_migra_solo_salvo_que_se_desactive(tmp_path):
    codigo = "from app.servicios.arranque import preparar_base; preparar_base(); print('listo')"
    assert correr_ok(tmp_path, codigo, SIGT_ENV="production", VERCEL="1") == "listo"
    r = correr(tmp_path / "otra", codigo, SIGT_ENV="production", VERCEL="1", SIGT_AUTO_MIGRATE="0") if (tmp_path / "otra").mkdir() is None else None
    assert r.returncode != 0 and "alembic upgrade head" in r.stderr


def test_la_base_desde_cero_queda_con_el_esquema_v2_y_la_migracion_de_endurecimiento_es_inocua(tmp_path):
    """Una sola migración base (v2_0001) más la de endurecimiento (v2_0002, que en SQLite no hace nada)."""
    salida = correr_ok(tmp_path, (
        "from app.servicios import migraciones as m; from sqlalchemy import inspect; from app.database import engine; "
        "m.actualizar(); t = set(inspect(engine).get_table_names()); print(m.revision_actual()); "
        "print(sorted(t & {'unidades','roles','rol_permisos','usuario_unidades','indicador_cargadores','metas'}))"))
    ahora, tablas = salida.splitlines()
    assert ahora == "v2_0002"
    assert tablas == str(sorted(["unidades", "roles", "rol_permisos", "usuario_unidades", "indicador_cargadores", "metas"]))
    todas = correr_ok(tmp_path, "from sqlalchemy import inspect; from app.database import engine; print(sorted(inspect(engine).get_table_names()))")
    assert todas == str(sorted(["alembic_version", "bitacora", "catalogos", "ejercicios", "indicador_cargadores", "indicadores", "intentos_fallidos",
                                "mediciones", "metas", "notas_auditoria", "parametros", "rol_permisos", "roles", "unidades", "usuario_unidades", "usuarios"]))
