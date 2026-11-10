"""Respaldo lógico, cifrado y verificable de TODA la base (independiente del motor: SQLite o PostgreSQL).

Formato del archivo (`.sigtbak`):  b"SIGTBAK1" | sal (16 bytes) | token Fernet( gzip( JSON ) )
- La clave se deriva de una frase de paso con PBKDF2-HMAC-SHA256 (600 000 iteraciones): el respaldo se puede restaurar en
  otro servidor aunque cambie SIGT_SECRET. Contiene hashes de contraseñas y la bitácora: sin la frase no se puede leer.
- El token Fernet es autenticado: cualquier alteración del archivo se detecta al abrirlo.
- El JSON lleva, por tabla, número de filas y SHA-256 del contenido, la revisión de Alembic y el estado de la cadena de
  la bitácora al momento de respaldar. `verificar` los recomprueba sin tocar ninguna base.
- `restaurar` solo escribe en una base RECIÉN MIGRADA y vacía (la bitácora es inmutable y no se puede vaciar): vuelve a
  comprobar conteos y la cadena de la bitácora, y revierte todo si algo no coincide.
"""
import base64
import gzip
import hashlib
import json
import os
from datetime import UTC, date, datetime

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from sqlalchemy import Integer, func, insert, select, text
from sqlalchemy.orm import Session

from ..database import Base
from ..errores import Conflicto, Invalido
from . import auditoria, reinicio

MAGIA = b"SIGTBAK1"
FORMATO = 1
ITERACIONES = 600_000
MIN_FRASE = 12


def _clave(frase: str, sal: bytes) -> Fernet:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=sal, iterations=ITERACIONES)
    return Fernet(base64.urlsafe_b64encode(kdf.derive(frase.encode())))


def _exigir_frase(frase: str) -> None:
    if len(frase or "") < MIN_FRASE:
        raise Invalido(f"La frase de paso del respaldo debe tener al menos {MIN_FRASE} caracteres.")


# ---------------------------------------------------------------- (de)serialización de valores
def _a_json(valor):
    if isinstance(valor, datetime):
        return {"$dt": valor.isoformat()}
    if isinstance(valor, date):
        return {"$d": valor.isoformat()}
    if isinstance(valor, bytes):
        return {"$b": base64.b64encode(valor).decode()}
    return valor


def _de_json(valor):
    if isinstance(valor, dict) and len(valor) == 1:
        if "$dt" in valor:
            return datetime.fromisoformat(valor["$dt"])
        if "$d" in valor:
            return date.fromisoformat(valor["$d"])
        if "$b" in valor:
            return base64.b64decode(valor["$b"])
    return valor


def _huella(filas: list[dict]) -> str:
    canonico = json.dumps(filas, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonico.encode()).hexdigest()


def _revision(db: Session) -> str | None:
    try:
        return db.scalar(text("SELECT version_num FROM alembic_version"))
    except Exception:   # base sin alembic (p. ej. creada con create_all en pruebas)
        db.rollback()
        return None


# ---------------------------------------------------------------- crear
def crear(db: Session, frase: str) -> tuple[bytes, dict]:
    """(archivo cifrado, resumen). Lee todas las tablas en UNA transacción: es una foto consistente."""
    _exigir_frase(frase)
    if db.get_bind().dialect.name == "postgresql":
        db.connection(execution_options={"isolation_level": "REPEATABLE READ"})
    tablas: dict[str, dict] = {}
    for t in Base.metadata.sorted_tables:
        orden = t.c.id if "id" in t.c else list(t.primary_key.columns)[0]
        filas = [{c.name: _a_json(v) for c, v in zip(t.columns, fila, strict=True)} for fila in db.execute(select(t).order_by(orden))]
        tablas[t.name] = {"filas": filas, "n": len(filas), "sha256": _huella(filas)}
    cadena = auditoria.verificar(db)
    contenido = {"formato": FORMATO, "creado": datetime.now(UTC).isoformat(), "alembic": _revision(db),
                 "bitacora": cadena, "tablas": tablas}
    crudo = gzip.compress(json.dumps(contenido, ensure_ascii=False, separators=(",", ":")).encode(), compresslevel=9)
    sal = os.urandom(16)
    archivo = MAGIA + sal + _clave(frase, sal).encrypt(crudo)
    resumen = {"creado": contenido["creado"], "alembic": contenido["alembic"], "bitacora_ok": cadena["ok"],
               "tablas": {n: v["n"] for n, v in tablas.items()}, "bytes": len(archivo),
               "sha256_archivo": hashlib.sha256(archivo).hexdigest()}
    return archivo, resumen


# ---------------------------------------------------------------- abrir y verificar
def abrir(archivo: bytes, frase: str) -> dict:
    """Descifra y valida un respaldo. Lanza Invalido si la frase es incorrecta o el archivo está dañado o alterado."""
    if not archivo.startswith(MAGIA) or len(archivo) < len(MAGIA) + 17:
        raise Invalido("No es un respaldo de SPE TPV.")
    sal = archivo[len(MAGIA):len(MAGIA) + 16]
    try:
        contenido = json.loads(gzip.decompress(_clave(frase, sal).decrypt(archivo[len(MAGIA) + 16:])))
    except (InvalidToken, OSError, ValueError):
        raise Invalido("Frase de paso incorrecta o respaldo dañado/alterado.") from None
    if contenido.get("formato") != FORMATO:
        raise Invalido(f"Formato de respaldo no soportado ({contenido.get('formato')}).")
    for nombre, t in contenido["tablas"].items():
        if len(t["filas"]) != t["n"] or _huella(t["filas"]) != t["sha256"]:
            raise Invalido(f"El respaldo está dañado: la tabla «{nombre}» no coincide con su huella.")
    faltan = {t.name for t in Base.metadata.sorted_tables} - set(contenido["tablas"])
    if faltan:
        raise Invalido(f"El respaldo no incluye las tablas: {', '.join(sorted(faltan))}.")
    return contenido


def verificar(archivo: bytes, frase: str) -> dict:
    """Comprueba que el respaldo se puede abrir y está íntegro, sin tocar ninguna base."""
    c = abrir(archivo, frase)
    return {"ok": True, "creado": c["creado"], "alembic": c["alembic"], "bitacora_ok": c["bitacora"]["ok"],
            "tablas": {n: t["n"] for n, t in c["tablas"].items()}}


# ---------------------------------------------------------------- restaurar
def _convertir(tabla, fila: dict) -> dict:
    return {k: _de_json(v) for k, v in fila.items() if k in tabla.c}


def restaurar(db: Session, archivo: bytes, frase: str, reemplazar: bool = False) -> dict:
    """Carga el respaldo. Por defecto solo en una base recién migrada (`alembic upgrade head`) y vacía.
    Con `reemplazar=True` (administrador, desde la interfaz) primero BORRA todo lo que hay. Todo o nada: si algo falla,
    la base queda exactamente como estaba."""
    c = abrir(archivo, frase)
    actual = _revision(db)
    if c["alembic"] and actual != c["alembic"]:
        raise Conflicto(f"La base está en la revisión {actual} y el respaldo en la {c['alembic']}: ejecute `alembic upgrade head` "
                        "con la misma versión del sistema con que se hizo el respaldo.")
    if reemplazar:
        if not any(u.get("rol") == "admin" and u.get("activo") for u in c["tablas"]["usuarios"]["filas"]):
            raise Invalido("El respaldo no contiene ningún administrador activo: restaurarlo dejaría el sistema sin acceso.")
    for t in Base.metadata.sorted_tables if not reemplazar else []:
        if db.scalar(select(func.count()).select_from(t)):
            raise Conflicto(f"La tabla «{t.name}» ya tiene datos: restaure únicamente en una base vacía (sin SIGT_ADMIN_PASSWORD "
                            "al migrar). La bitácora es inmutable y no puede sobrescribirse.")
    try:
        if reemplazar:
            reinicio.vaciar_tablas(db)
        for t in Base.metadata.sorted_tables:
            filas = [_convertir(t, f) for f in c["tablas"][t.name]["filas"]]
            for i in range(0, len(filas), 1000):
                db.execute(insert(t), filas[i:i + 1000])
        if db.get_bind().dialect.name == "postgresql":   # las secuencias deben seguir después del mayor id restaurado
            for t in Base.metadata.sorted_tables:
                if "id" in t.c and isinstance(t.c.id.type, Integer):
                    db.execute(text(f"SELECT setval(pg_get_serial_sequence('{t.name}', 'id'), COALESCE((SELECT MAX(id) FROM \"{t.name}\"), 1))"))
        for t in Base.metadata.sorted_tables:
            n = db.scalar(select(func.count()).select_from(t))
            if n != c["tablas"][t.name]["n"]:
                raise Conflicto(f"Verificación fallida en «{t.name}»: {n} filas cargadas, {c['tablas'][t.name]['n']} esperadas.")
        cadena = auditoria.verificar(db)
        if c["bitacora"]["ok"] and not cadena["ok"]:
            raise Conflicto("La cadena de la bitácora no se verifica tras restaurar: se revirtió todo.")
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"ok": True, "creado": c["creado"], "tablas": {n: t["n"] for n, t in c["tablas"].items()}, "bitacora": cadena}
