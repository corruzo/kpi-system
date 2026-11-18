"""Hash de contraseñas, cookie de sesión firmada y límite de intentos (solo librería estándar)."""
import base64
import hashlib
import hmac
import os
import secrets
import time

from .config import PRODUCCION
from .database import DATA_DIR

COOKIE = "sigt_sesion"
DURACION = 60 * 60 * 10  # 10 horas
ITERACIONES = 600_000          # PBKDF2-HMAC-SHA256: lo que recomienda OWASP (Password Storage Cheat Sheet)
ITERACIONES_ANTIGUAS = 210_000  # hashes guardados sin prefijo (versión anterior): se siguen aceptando y se actualizan al ingresar
PREFIJO = "pbkdf2_sha256"


def _clave() -> bytes:
    env = os.getenv("SIGT_SECRET")
    if env:
        if PRODUCCION and len(env) < 32:
            raise RuntimeError("SIGT_SECRET debe tener al menos 32 caracteres.")
        return env.encode()
    if PRODUCCION:
        raise RuntimeError("Defina SIGT_SECRET (cadena aleatoria de 32+ caracteres) en producción.")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    f = DATA_DIR / ".secret"
    if not f.exists():
        f.write_text(secrets.token_hex(32))
        f.chmod(0o600)          # solo el propietario puede leer la clave de firma
    return f.read_text().strip().encode()


_SECRET = _clave()


def secreto() -> bytes:
    """SIGT_SECRET: material para derivar otras claves (cifrado de secretos en la base)."""
    return _SECRET


def hash_password(password: str) -> str:
    """`pbkdf2_sha256$<iteraciones>$<sal>$<hash>`: las iteraciones viajan en el hash, así se pueden subir sin invalidar las cuentas."""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), ITERACIONES)
    return f"{PREFIJO}${ITERACIONES}${salt}${dk.hex()}"


def _partes(almacenado: str) -> tuple[int, str, str]:
    """(iteraciones, sal, hash) de un hash guardado, en el formato actual o en el anterior («sal$hash», 210 000 iteraciones)."""
    if almacenado.startswith(PREFIJO + "$"):
        _, it, salt, dk = almacenado.split("$")
        return int(it), salt, dk
    salt, _, dk = almacenado.partition("$")
    return ITERACIONES_ANTIGUAS, salt, dk


def verificar_password(password: str, almacenado: str) -> bool:
    iteraciones, salt, dk = _partes(almacenado)
    calc = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iteraciones).hex()
    return hmac.compare_digest(calc, dk)


def necesita_rehash(almacenado: str) -> bool:
    """¿Se guardó con menos iteraciones (o en el formato anterior) que las actuales? Se actualiza al ingresar con la clave correcta."""
    return _partes(almacenado)[0] < ITERACIONES


def crear_token(usuario_id: int, version: int) -> str:
    cuerpo = f"{usuario_id}:{version}:{int(time.time()) + DURACION}"
    firma = hmac.new(_SECRET, cuerpo.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{cuerpo}:{firma}".encode()).decode()


def leer_token(token: str | None) -> tuple[int, int] | None:
    if not token:
        return None
    try:
        uid, ver, exp, firma = base64.urlsafe_b64decode(token.encode()).decode().split(":")
        esperada = hmac.new(_SECRET, f"{uid}:{ver}:{exp}".encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(firma, esperada) and int(exp) > time.time():
            return int(uid), int(ver)
    except Exception:
        pass
    return None


# Hash válido de una contraseña que nadie conoce: se verifica cuando el usuario no existe para que el tiempo de
# respuesta sea el mismo que con un usuario real (evita enumerar cuentas por temporización).
HASH_FICTICIO = hash_password(secrets.token_hex(16))


def firmar_reporte(contenido: str) -> str:
    """Firma HMAC de la huella de un reporte (separada de la firma de las sesiones)."""
    return hmac.new(_SECRET, b"reporte:" + contenido.encode(), hashlib.sha256).hexdigest()
