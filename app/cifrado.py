"""Cifrado simétrico de secretos guardados en la base (Fernet), con una clave derivada de SIGT_SECRET.

La clave de cifrado no es SIGT_SECRET sino un derivado (HKDF-SHA256 con un contexto propio), de modo que no se reutiliza
la misma clave que firma las sesiones. Si SIGT_SECRET cambia, los valores cifrados dejan de poder leerse (`ErrorDeCifrado`).
"""
import base64
import functools

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from . import security

PREFIJO = "fernet:"   # distingue un valor cifrado de uno heredado en texto plano


class ErrorDeCifrado(Exception):
    """El valor guardado no se puede descifrar con la SIGT_SECRET actual."""


@functools.lru_cache(maxsize=1)
def _fernet() -> Fernet:
    clave = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"sigt:cifrado:v1").derive(security.secreto())
    return Fernet(base64.urlsafe_b64encode(clave))


def esta_cifrado(valor: str) -> bool:
    return valor.startswith(PREFIJO)


def cifrar(texto: str) -> str:
    return PREFIJO + _fernet().encrypt(texto.encode()).decode()


def descifrar(valor: str) -> str:
    if not esta_cifrado(valor):
        raise ErrorDeCifrado("El valor no está cifrado.")
    try:
        return _fernet().decrypt(valor[len(PREFIJO):].encode()).decode()
    except InvalidToken:
        raise ErrorDeCifrado("No se pudo descifrar: ¿cambió SIGT_SECRET?") from None
