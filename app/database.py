"""Conexión a base de datos.

Producción: PostgreSQL (Supabase) mediante SIGT_DATABASE_URL / DATABASE_URL.
Desarrollo: SQLite local si no se define ninguna URL.
"""
import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import PRODUCCION

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("SIGT_DATA_DIR", BASE_DIR / "data"))


def _url() -> str:
    url = os.getenv("SIGT_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not url:
        if PRODUCCION:
            raise RuntimeError("Defina SIGT_DATABASE_URL (cadena de conexión de Supabase) en producción.")
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{DATA_DIR / 'sigt.db'}"
    for pref in ("postgres://", "postgresql://"):  # Supabase entrega estos prefijos
        if url.startswith(pref):
            return "postgresql+psycopg://" + url[len(pref):]
    return url


DATABASE_URL = _url()
ES_SQLITE = DATABASE_URL.startswith("sqlite")
ES_POSTGRES = DATABASE_URL.startswith("postgresql")

if ES_SQLITE:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _pragmas(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA journal_mode=WAL")
        cur.close()
elif ES_POSTGRES:
    # Serverless (Vercel): sin pool propio; el pooler de Supabase gestiona las conexiones.
    _pool = {"poolclass": NullPool} if os.getenv("VERCEL") or os.getenv("SIGT_NULLPOOL") == "1" else \
        {"pool_size": int(os.getenv("SIGT_POOL_SIZE", "5")), "max_overflow": 5, "pool_recycle": 300}
    engine = create_engine(
        DATABASE_URL, pool_pre_ping=True, **_pool,
        # prepare_threshold=None: compatible con el pooler transaccional de Supabase (puerto 6543)
        connect_args={"prepare_threshold": None},
    )
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
