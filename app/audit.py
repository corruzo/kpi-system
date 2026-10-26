"""Bitácora inalterable con encadenamiento de hashes."""
import hashlib
import json

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .models import Bitacora, ahora

GENESIS = "0" * 64


def _hash(prev: str, d: dict) -> str:
    canon = json.dumps(d, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(f"{prev}|{canon}".encode()).hexdigest()


def _payload(b: Bitacora) -> dict:
    return {"fecha": b.fecha.isoformat(), "usuario_id": b.usuario_id,
            "usuario_nombre": b.usuario_nombre, "rol": b.rol, "accion": b.accion,
            "entidad": b.entidad, "entidad_id": b.entidad_id,
            "indicador_id": b.indicador_id, "area_id": b.area_id, "detalle": b.detalle}


def registrar(db: Session, usuario, accion: str, entidad: str, entidad_id=None,
              detalle: dict | None = None, indicador=None, fecha=None) -> Bitacora:
    if db.get_bind().dialect.name == "postgresql":  # serializa la cadena entre procesos
        db.execute(text("SELECT pg_advisory_xact_lock(727001)"))
    prev = db.scalar(select(Bitacora.hash).order_by(Bitacora.id.desc()).limit(1)) or GENESIS
    b = Bitacora(
        fecha=fecha or ahora(),
        usuario_id=usuario.id if usuario else None,
        usuario_nombre=usuario.nombre if usuario else "Sistema",
        rol=usuario.rol if usuario else "sistema",
        accion=accion, entidad=entidad, entidad_id=entidad_id,
        indicador_id=indicador.id if indicador else None,
        area_id=indicador.area_id if indicador else (usuario.area_id if usuario else None),
        detalle=detalle or {}, prev_hash=prev, hash="",
    )
    b.hash = _hash(prev, _payload(b))
    db.add(b)
    db.flush()
    return b


def verificar(db: Session) -> dict:
    prev, total = GENESIS, 0
    for b in db.scalars(select(Bitacora).order_by(Bitacora.id)):
        total += 1
        if b.prev_hash != prev or b.hash != _hash(prev, _payload(b)):
            return {"ok": False, "total": total, "primer_error_id": b.id}
        prev = b.hash
    return {"ok": True, "total": total, "primer_error_id": None}
