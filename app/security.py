"""Hash de contraseñas y cookie de sesión firmada (solo librería estándar)."""
import base64
import hashlib
import hmac
import os
import secrets
import time

from .database import DATA_DIR

COOKIE = "sigt_sesion"
DURACION = 60 * 60 * 10  # 10 horas


def _clave() -> bytes:
    env = os.getenv("SIGT_SECRET")
    if env:
        return env.encode()
    f = DATA_DIR / ".secret"
    if not f.exists():
        f.write_text(secrets.token_hex(32))
    return f.read_text().strip().encode()


_SECRET = _clave()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(8)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000)
    return f"{salt}${dk.hex()}"


def verificar_password(password: str, almacenado: str) -> bool:
    salt, _, dk = almacenado.partition("$")
    calc = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()
    return hmac.compare_digest(calc, dk)


def crear_token(usuario_id: int) -> str:
    cuerpo = f"{usuario_id}:{int(time.time()) + DURACION}"
    firma = hmac.new(_SECRET, cuerpo.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{cuerpo}:{firma}".encode()).decode()


def leer_token(token: str | None) -> int | None:
    if not token:
        return None
    try:
        uid, exp, firma = base64.urlsafe_b64decode(token.encode()).decode().split(":")
        esperada = hmac.new(_SECRET, f"{uid}:{exp}".encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(firma, esperada) and int(exp) > time.time():
            return int(uid)
    except Exception:
        pass
    return None
