"""Hash de contraseñas, cookie de sesión firmada y límite de intentos (solo librería estándar)."""
import base64
import hashlib
import hmac
import os
import secrets
import time
from collections import defaultdict, deque

from .config import PRODUCCION
from .database import DATA_DIR

COOKIE = "sigt_sesion"
DURACION = 60 * 60 * 10  # 10 horas
ITERACIONES = 210_000


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
    return f.read_text().strip().encode()


_SECRET = _clave()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), ITERACIONES)
    return f"{salt}${dk.hex()}"


def verificar_password(password: str, almacenado: str) -> bool:
    salt, _, dk = almacenado.partition("$")
    calc = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), ITERACIONES).hex()
    return hmac.compare_digest(calc, dk)


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


class LimiteIntentos:
    """Bloquea temporalmente tras demasiados intentos fallidos (en memoria, por proceso).

    Cada llave tiene su propio tope (`maximo`), de modo que se pueden vigilar a la vez la pareja IP+usuario, la IP sola
    (password spraying: muchos usuarios desde un mismo origen) y el usuario solo (muchas IP contra una cuenta)."""

    def __init__(self, maximo=5, ventana=900):
        self.maximo, self.ventana = maximo, ventana
        self._fallos: dict[str, deque] = defaultdict(deque)

    def _limpiar(self, k):
        q = self._fallos.get(k)
        if q is None:
            return ()
        while q and q[0] < time.time() - self.ventana:
            q.popleft()
        if not q:
            del self._fallos[k]    # no acumular llaves vacías (los nombres de usuario los elige el atacante)
        return q

    def bloqueado(self, k: str, maximo: int | None = None) -> bool:
        return len(self._limpiar(k)) >= (maximo or self.maximo)

    def fallo(self, k: str):
        self._limpiar(k)
        self._fallos[k].append(time.time())

    def limpiar(self, k: str):
        self._fallos.pop(k, None)


# Hash válido de una contraseña que nadie conoce: se verifica cuando el usuario no existe para que el tiempo de
# respuesta sea el mismo que con un usuario real (evita enumerar cuentas por temporización).
HASH_FICTICIO = hash_password(secrets.token_hex(16))


def firmar_reporte(contenido: str) -> str:
    """Firma HMAC de la huella de un reporte (separada de la firma de las sesiones)."""
    return hmac.new(_SECRET, b"reporte:" + contenido.encode(), hashlib.sha256).hexdigest()
