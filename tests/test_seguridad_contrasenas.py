"""Contraseñas: PBKDF2 con las iteraciones dentro del hash, y actualización transparente de los hashes antiguos al ingresar."""
import hashlib

from conftest import CLAVE, cuenta, entrar

from app import security
from app.database import SessionLocal
from app.models import Usuario


def _antiguo(password: str) -> str:
    """Un hash en el formato anterior: «sal$hash» con 210 000 iteraciones, sin prefijo."""
    sal = "0123456789abcdef0123456789abcdef"
    return f"{sal}${hashlib.pbkdf2_hmac('sha256', password.encode(), sal.encode(), security.ITERACIONES_ANTIGUAS).hex()}"


def test_el_hash_nuevo_guarda_sus_iteraciones_y_se_verifica():
    h = security.hash_password("una-clave-larga-1")
    prefijo, iteraciones, sal, dk = h.split("$")
    assert prefijo == "pbkdf2_sha256" and int(iteraciones) == security.ITERACIONES and len(sal) == 32 and len(dk) == 64
    assert security.verificar_password("una-clave-larga-1", h) and not security.verificar_password("otra-clave-larga", h)
    assert security.necesita_rehash(h) is False
    assert security.hash_password("una-clave-larga-1") != h                       # sal distinta cada vez


def test_la_produccion_exige_al_menos_lo_que_recomienda_owasp():
    import os
    import subprocess
    import sys
    r = subprocess.run([sys.executable, "-c", "from app import security; print(security.ITERACIONES)"], capture_output=True, text=True,
                       env={**os.environ, "SIGT_DATA_DIR": os.environ.get("SIGT_DATA_DIR", "/tmp")})
    assert r.returncode == 0 and int(r.stdout.strip()) >= 600_000


def test_un_hash_antiguo_sigue_valiendo_y_se_actualiza_al_ingresar(client, monkeypatch):
    monkeypatch.setattr(security, "ITERACIONES", security.ITERACIONES_ANTIGUAS + 90_000)   # las pruebas usan 1 000: aquí, más que el formato antiguo
    usuario = cuenta(client)
    antiguo = _antiguo(CLAVE)
    with SessionLocal() as db:
        db.query(Usuario).filter_by(username=usuario).one().password_hash = antiguo
        db.commit()
    assert security.verificar_password(CLAVE, antiguo) and security.necesita_rehash(antiguo)
    entrar(client, usuario)                                                        # ingresa con su clave de siempre
    with SessionLocal() as db:
        nuevo = db.query(Usuario).filter_by(username=usuario).one().password_hash
    assert nuevo != antiguo and nuevo.startswith("pbkdf2_sha256$") and security.verificar_password(CLAVE, nuevo)
    entrar(client, usuario)                                                        # y sigue pudiendo ingresar
