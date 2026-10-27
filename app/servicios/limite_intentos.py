"""Limitador de intentos fallidos con contadores en la base de datos.

Al estar en la base, el bloqueo vale entre todos los workers de Uvicorn y todas las instancias serverless (antes cada
proceso llevaba su propia cuenta en memoria). Cada operación usa una sesión propia con su commit: un intento fallido debe
quedar registrado aunque la petición termine en error y se deshaga su transacción.
"""
import hashlib
from datetime import timedelta

from sqlalchemy import delete, func, select

from ..database import SessionLocal
from ..models import IntentoFallido, ahora


class LimiteIntentos:
    def __init__(self, maximo=5, ventana=900):
        self.maximo, self.ventana = maximo, ventana

    @staticmethod
    def _huella(llave: str) -> str:
        return hashlib.sha256(llave.encode()).hexdigest()   # largo fijo y sin IP ni usuarios en claro

    def _desde(self):
        return ahora() - timedelta(seconds=self.ventana)

    def bloqueado(self, llave: str, maximo: int | None = None) -> bool:
        with SessionLocal() as db:
            fallos = db.scalar(select(func.count(IntentoFallido.id)).where(
                IntentoFallido.llave == self._huella(llave), IntentoFallido.fecha > self._desde()))
        return fallos >= (maximo or self.maximo)

    def fallo(self, *llaves: str) -> None:
        """Registra un fallo en cada llave (en una sola transacción) y purga los vencidos."""
        with SessionLocal() as db:
            db.execute(delete(IntentoFallido).where(IntentoFallido.fecha <= self._desde()))
            db.add_all(IntentoFallido(llave=self._huella(k)) for k in llaves)
            db.commit()

    def limpiar(self, *llaves: str) -> None:
        with SessionLocal() as db:
            db.execute(delete(IntentoFallido).where(IntentoFallido.llave.in_([self._huella(k) for k in llaves])))
            db.commit()

    def reiniciar(self) -> None:
        """Olvida todos los intentos (reinicio de fábrica y pruebas)."""
        with SessionLocal() as db:
            db.execute(delete(IntentoFallido))
            db.commit()
