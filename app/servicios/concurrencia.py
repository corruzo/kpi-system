"""Serialización de escrituras: mantiene íntegra la cadena de hashes de la bitácora y evita carreras entre las
comprobaciones y las escrituras de un mismo caso de uso.

PostgreSQL: un advisory lock transaccional de la propia base (vale entre todos los procesos y se suelta solo al terminar
la transacción; no hay ningún candado en memoria). SQLite (desarrollo, un solo proceso): un candado de hilos, porque
SQLite no puede esperar entre una lectura y la escritura posterior de la misma transacción.
"""
import threading

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from ..errores import Ocupado

ID_BLOQUEO_ESCRITURA = 727001      # el mismo que usa auditoria.registrar (es reentrante dentro de una sesión)
ESPERA_MAXIMA_MS = 15_000          # pasado este tiempo se responde 503 en vez de ocupar un hilo indefinidamente

candado_escritura = threading.Lock()   # solo SQLite


def bloquear_escritura(db: Session) -> None:
    """Toma el lock de escritura en PostgreSQL; se libera con el commit o rollback de la sesión."""
    try:
        db.execute(text(f"SET LOCAL lock_timeout = {ESPERA_MAXIMA_MS}"))
        db.execute(text(f"SELECT pg_advisory_xact_lock({ID_BLOQUEO_ESCRITURA})"))
    except DBAPIError:
        db.rollback()
        raise Ocupado("El sistema está ocupado con otra operación. Intente de nuevo en unos segundos.") from None
