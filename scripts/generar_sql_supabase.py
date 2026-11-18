"""Genera `scripts/supabase_instalacion_completa.sql`: la base de datos COMPLETA desde cero para Supabase (PostgreSQL).

    python scripts/generar_sql_supabase.py          # reescribe el archivo

El SQL sale de los modelos (tablas, claves, índices y restricciones) y de la migración de endurecimiento (bitácora inalterable,
RLS, retiro de permisos a `anon` y `authenticated`), y deja `alembic_version` en la revisión actual: al arrancar, la aplicación
ve el esquema al día y no migra nada. Una prueba (`tests/test_sql_supabase.py`) verifica que el archivo coincida con esto.
"""
import importlib.util
import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "scripts" / "supabase_instalacion_completa.sql"


def _cargar_migracion(nombre: str):
    ruta = next((RAIZ / "migrations" / "versions").glob(f"{nombre}_*.py"))
    espec = importlib.util.spec_from_file_location(nombre, ruta)
    modulo = importlib.util.module_from_spec(espec)
    espec.loader.exec_module(modulo)
    return modulo


def _revision_actual() -> str:
    ultima = sorted((RAIZ / "migrations" / "versions").glob("v2_*.py"))[-1]
    return ultima.name.split("_", 2)[0] + "_" + ultima.name.split("_", 2)[1]


def generar() -> str:
    os.environ.setdefault("SIGT_DATA_DIR", tempfile.mkdtemp())   # el motor de la app se crea al importar: que no toque `data/`
    sys.path.insert(0, str(RAIZ))
    from sqlalchemy.dialects import postgresql
    from sqlalchemy.schema import CreateIndex, CreateTable

    from app import models  # noqa: F401  (registra las tablas)
    from app.database import Base

    dialecto = postgresql.dialect()
    endurecimiento = _cargar_migracion("v2_0002")
    tablas = Base.metadata.sorted_tables
    revision = _revision_actual()

    out = [f"""-- ============================================================================================================
-- SPE TPV · INSTALACIÓN COMPLETA DE LA BASE DE DATOS (Supabase / PostgreSQL) · revisión {revision}
-- GENERADO por scripts/generar_sql_supabase.py: no se edita a mano (una prueba verifica que coincida con los modelos).
--
-- ¡DESTRUCTIVO E IRREVERSIBLE! Borra TODO el esquema `public` (tablas, datos, bitácora) y lo crea de nuevo, vacío.
-- Ejecútelo SOLO en la base correcta, en el SQL Editor de Supabase, de una sola vez.
--
-- Después de ejecutarlo:
--   1. Defina en el despliegue SIGT_ADMIN_USER y SIGT_ADMIN_PASSWORD (10+ caracteres): al arrancar con la base vacía la
--      aplicación crea el primer Desarrollador y siembra los roles de sistema y los parámetros. Elimine la contraseña luego.
--   2. La aplicación ve `alembic_version` = {revision}: no migra nada.
-- ============================================================================================================

BEGIN;

DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;
GRANT USAGE ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO postgres;

-- ----------------------------------------------------------------------------------------------- tablas"""]
    for t in tablas:
        out.append(str(CreateTable(t).compile(dialect=dialecto)).strip() + ";")
        for ix in sorted(t.indexes, key=lambda i: i.name):
            out.append(str(CreateIndex(ix).compile(dialect=dialecto)).strip() + ";")
        out.append("")
    out.append(f"""-- ------------------------------------------------------------------------------------- control de versión (Alembic)
CREATE TABLE alembic_version (
\tversion_num VARCHAR(32) NOT NULL,
\tCONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);
INSERT INTO alembic_version (version_num) VALUES ('{revision}');

-- -------------------------------------------------------------------------------- endurecimiento (migración v2_0002)
-- Bitácora inalterable a nivel de motor:""")
    out += [s.strip() + ";" for s in endurecimiento.TRIGGER]
    out.append("\n-- RLS sin políticas en todas las tablas: la API pública de Supabase (anon/authenticated) no lee ni escribe.")
    out.append("-- La aplicación se conecta con el rol postgres, que ignora RLS.")
    out += [f'ALTER TABLE public."{t.name}" ENABLE ROW LEVEL SECURITY;' for t in tablas]
    out.append('ALTER TABLE public."alembic_version" ENABLE ROW LEVEL SECURITY;')
    out.append("\n-- Sin permisos para los roles públicos de Supabase (solo si existen):")
    out.append("DO $$\nBEGIN\n\tIF EXISTS (SELECT 1 FROM pg_roles WHERE rolname IN ('anon', 'authenticated')) THEN")
    out += [f"\t\tEXECUTE '{s}';" for s in endurecimiento.REVOCAR]
    out.append("\tEND IF;\nEND $$;\n\nCOMMIT;\n")
    return "\n".join(out)


if __name__ == "__main__":
    DESTINO.write_text(generar(), encoding="utf-8")
    print(f"Escrito {DESTINO.relative_to(RAIZ)}")
