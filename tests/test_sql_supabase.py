"""El SQL de instalación completa para Supabase debe coincidir con los modelos y las migraciones (se regenera con
`python scripts/generar_sql_supabase.py`)."""
import importlib.util
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def _generador():
    espec = importlib.util.spec_from_file_location("generar_sql_supabase", RAIZ / "scripts" / "generar_sql_supabase.py")
    modulo = importlib.util.module_from_spec(espec)
    espec.loader.exec_module(modulo)
    return modulo


def test_el_sql_de_supabase_coincide_con_los_modelos():
    g = _generador()
    assert g.DESTINO.read_text(encoding="utf-8") == g.generar(), "Regenere: python scripts/generar_sql_supabase.py"


def test_el_sql_crea_todas_las_tablas_y_deja_la_revision_actual():
    from app.database import Base
    sql = _generador().DESTINO.read_text(encoding="utf-8")
    assert all(f"CREATE TABLE {t.name} (" in sql for t in Base.metadata.sorted_tables)
    ultima = sorted((RAIZ / "migrations" / "versions").glob("v2_*.py"))[-1].name[:7]
    assert f"INSERT INTO alembic_version (version_num) VALUES ('{ultima}');" in sql
    assert "ENABLE ROW LEVEL SECURITY" in sql and "bitacora_inmutable" in sql
