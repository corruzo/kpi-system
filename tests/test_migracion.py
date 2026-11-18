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
    """Esquema base (v2_0001) más las migraciones v2_0002 (endurecimiento), v2_0003 (sin listas de apoyo), v2_0004 (períodos
    justificados), v2_0005 (responsable + suplente), v2_0006 (historial de revisiones) y v2_0007 (notificaciones): la revisión actual es la última."""
    salida = correr_ok(tmp_path, (
        "from app.servicios import migraciones as m; from sqlalchemy import inspect; from app.database import engine; "
        "m.actualizar(); t = set(inspect(engine).get_table_names()); print(m.revision_actual()); "
        "print(sorted(t & {'unidades','roles','rol_permisos','usuario_unidades','metas'}))"))
    ahora, tablas = salida.splitlines()
    assert ahora == "v2_0007"
    assert tablas == str(sorted(["unidades", "roles", "rol_permisos", "usuario_unidades", "metas"]))
    todas = correr_ok(tmp_path, "from sqlalchemy import inspect; from app.database import engine; print(sorted(inspect(engine).get_table_names()))")
    assert todas == str(sorted(["alembic_version", "bitacora", "ejercicios", "indicadores", "intentos_fallidos",
                                "mediciones", "metas", "notas_auditoria", "notificaciones", "parametros", "periodos_justificados", "revisiones", "rol_permisos", "roles", "unidades", "usuario_unidades", "usuarios"]))


def test_la_migracion_a_responsable_y_suplente_conserva_a_los_cargadores_y_registra_a_quien_queda_fuera(tmp_path):
    """v2_0005: el primer cargador distinto del responsable pasa a suplente; si no había responsable, el primer cargador lo es;
    los que sobran (más de dos personas) se descartan y cada caso queda en la bitácora."""
    preparar = (
        "import sqlite3; from alembic import command; from app.servicios import migraciones as m; cfg = m.configuracion(); "
        "command.upgrade(cfg, 'v2_0004'); c = sqlite3.connect(r'%s'); "
        "[c.execute('INSERT INTO usuarios (id, username, nombre, ambito_raiz, password_hash, activo, sesion_v, tour_visto) VALUES (?, ?, ?, 0, ?, 1, 0, 0)', (i, f'u{i}', f'Persona {i}', 'x')) for i in range(1, 6)]; "
        "c.execute(\"INSERT INTO unidades (id, nombre, nivel, ruta) VALUES (1, 'G', 'gerencia', '/1/')\"); "
        "[c.execute(\"INSERT INTO indicadores (id, codigo, nombre, objetivo, nodo_id, responsable_id, unidad, frecuencia, sentido, formula, variables, nivel_optimo, limite, activo, creado_en, constantes, decimales, fuente, notas, seguimiento, ref_nombre, ref_detalle, sigla, gerencia, lider, resp_medicion, resp_registro, resp_analisis) VALUES (?, ?, 'N', '', 1, ?, '%%', 'mensual', 'mayor', 'a', '[]', 1, 0, 1, '2026-01-01', '[]', 2, '', '', 'proceso', '', '', '', '', '', '', '', '')\", (i, k, r)) for i, k, r in ((1, 'A1', 1), (2, 'A2', None), (3, 'A3', 1))]; "
        "[c.execute('INSERT INTO indicador_cargadores (indicador_id, usuario_id) VALUES (?, ?)', par) for par in ((1, 1), (1, 2), (2, 4), (2, 5), (3, 1), (3, 2), (3, 3), (3, 4))]; "
        "c.commit(); c.close(); command.upgrade(cfg, 'v2_0005'); print(m.revision_actual())" % (tmp_path / "base.db"))
    assert correr_ok(tmp_path, preparar) == "v2_0005"
    c = sqlite3.connect(tmp_path / "base.db")
    filas = {i: (r, s) for i, r, s in c.execute("SELECT id, responsable_id, suplente_id FROM indicadores")}
    assert filas == {1: (1, 2),          # responsable 1 + su cargador 2
                     2: (4, 5),          # sin responsable: el primer cargador lo es y el segundo, suplente
                     3: (1, 2)}          # responsable 1, suplente el primer otro cargador; 3 y 4 quedan fuera
    assert "indicador_cargadores" not in {n for (n,) in c.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    descartes = [(i, d) for i, d in c.execute("SELECT entidad_id, detalle FROM bitacora WHERE accion = 'INDICADOR_ASIGNADO'")]
    assert [i for i, _ in descartes] == [3] and "Persona 3" in descartes[0][1] and "Persona 4" in descartes[0][1]
    c.close()


def test_la_migracion_del_historial_de_revisiones_reconstruye_las_devoluciones_desde_la_bitacora(tmp_path):
    """v2_0006: cada APROBACION, OBSERVACION y REAPERTURA de la bitácora pasa a `revisiones` con su nota, quien la hizo y cuándo;
    una carga revisada sin rastro en la bitácora (p. ej. importada) recibe una revisión con sus datos actuales."""
    preparar = (
        "import json, sqlite3; from alembic import command; from app.servicios import migraciones as m; cfg = m.configuracion(); "
        "command.upgrade(cfg, 'v2_0005'); c = sqlite3.connect(r'%s'); "
        "[c.execute('INSERT INTO usuarios (id, username, nombre, ambito_raiz, password_hash, activo, sesion_v, tour_visto) VALUES (?, ?, ?, 0, ?, 1, 0, 0)', (i, f'u{i}', f'Persona {i}', 'x')) for i in (1, 2)]; "
        "c.execute(\"INSERT INTO unidades (id, nombre, nivel, ruta) VALUES (1, 'G', 'gerencia', '/1/')\"); "
        "c.execute(\"INSERT INTO indicadores (id, codigo, nombre, objetivo, nodo_id, responsable_id, unidad, frecuencia, sentido, formula, variables, nivel_optimo, limite, activo, creado_en, constantes, decimales, fuente, notas, seguimiento, ref_nombre, ref_detalle, sigla, gerencia, lider, resp_medicion, resp_registro, resp_analisis) VALUES (1, 'A1', 'N', '', 1, 1, '%%', 'mensual', 'mayor', 'a', '[]', 1, 0, 1, '2026-01-01', '[]', 2, '', '', 'proceso', '', '', '', '', '', '', '', '')\"); "
        "[c.execute(\"INSERT INTO mediciones (id, indicador_id, periodo, valores, resultado, semaforo, nivel_optimo, limite, sentido, estado, analisis, plan_mejora, version, cargado_por_id, cargado_en, revisado_por_id, revisado_en, nota_revision, formula, constantes, decimales, ejercicio) VALUES (?, 1, ?, '{}', 1, 'verde', 1, 0, 'mayor', ?, '', '', 1, 1, '2026-02-01 08:00:00', ?, ?, ?, 'a', '[]', 2, 2026)\", d) for d in ("
        "(1, '2026-01', 'aprobado', 2, '2026-02-03 10:00:00', ''), (2, '2026-02', 'aprobado', 2, '2026-03-05 10:00:00', 'Importado desde Excel'))]; "
        "[c.execute(\"INSERT INTO bitacora (fecha, usuario_id, usuario_nombre, rol, accion, entidad, entidad_id, indicador_id, nodo_id, detalle, prev_hash, hash) VALUES (?, 2, 'Persona 2', 'R', ?, 'medicion', 1, 1, 1, ?, 'p', 'h')\", (f, a, json.dumps({'periodo': '2026-01', 'nota': n}))) for f, a, n in ("
        "('2026-02-02 09:00:00', 'OBSERVACION', 'Falta soporte del dato'), ('2026-02-03 10:00:00', 'APROBACION', ''), ('2026-02-10 11:00:00', 'REAPERTURA', 'Se detectó un error'))]; "
        "c.commit(); c.close(); command.upgrade(cfg, 'v2_0006'); print(m.revision_actual())" % (tmp_path / "base.db"))
    assert correr_ok(tmp_path, preparar) == "v2_0006"
    c = sqlite3.connect(tmp_path / "base.db")
    filas = c.execute("SELECT medicion_id, accion, nota, por_id FROM revisiones ORDER BY id").fetchall()
    assert filas == [(1, "devuelta", "Falta soporte del dato", 2), (1, "aprobada", "", 2), (1, "reabierta", "Se detectó un error", 2),
                     (2, "aprobada", "Importado desde Excel", 2)]
    c.close()
