"""El limitador de intentos guarda sus contadores en la base: valen entre procesos y no se pierden al reiniciar."""
import os
import subprocess
import sys
from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.database import SessionLocal
from app.models import IntentoFallido, ahora
from app.servicios.limite_intentos import LimiteIntentos


@pytest.fixture(autouse=True)
def limpio():
    LimiteIntentos().reiniciar()
    yield
    LimiteIntentos().reiniciar()


def test_dos_instancias_comparten_los_contadores():
    a, b = LimiteIntentos(), LimiteIntentos()   # como dos workers distintos
    a.fallo("1.2.3.4|ana")
    a.fallo("1.2.3.4|ana")
    assert b.bloqueado("1.2.3.4|ana", maximo=2)
    assert not b.bloqueado("1.2.3.4|ana", maximo=3)
    assert not b.bloqueado("otra-llave", maximo=1)


def test_otro_proceso_ve_el_bloqueo():
    """Cinco fallos registrados desde un proceso Python distinto bloquean al proceso de las pruebas."""
    codigo = "from app.servicios.limite_intentos import LimiteIntentos as L; l = L(); [l.fallo('x|y') for _ in range(5)]"
    r = subprocess.run([sys.executable, "-c", codigo], env=os.environ.copy(), capture_output=True, text=True, cwd=os.getcwd())
    assert r.returncode == 0, r.stderr
    assert LimiteIntentos().bloqueado("x|y")


def test_los_intentos_vencidos_no_cuentan_y_se_purgan():
    limite = LimiteIntentos(ventana=900)
    with SessionLocal() as db:
        db.add(IntentoFallido(llave=limite._huella("vieja"), fecha=ahora() - timedelta(hours=1)))
        db.commit()
    assert not limite.bloqueado("vieja", maximo=1)
    limite.fallo("cualquiera")
    with SessionLocal() as db:
        assert db.scalar(select(func.count(IntentoFallido.id)).where(IntentoFallido.llave == limite._huella("vieja"))) == 0


def test_la_base_no_guarda_ip_ni_usuario_en_claro():
    LimiteIntentos().fallo("203.0.113.9|ana.perez")
    with SessionLocal() as db:
        llaves = list(db.scalars(select(IntentoFallido.llave)))
    assert llaves and all(len(k) == 64 and "ana" not in k and "203" not in k for k in llaves)


def test_fallo_registra_varias_llaves_y_limpiar_las_borra():
    limite = LimiteIntentos()
    limite.fallo("a", "b", "c")
    assert all(limite.bloqueado(k, maximo=1) for k in "abc")
    limite.limpiar("a", "b")
    assert not limite.bloqueado("a", maximo=1) and limite.bloqueado("c", maximo=1)
    limite.reiniciar()
    assert not limite.bloqueado("c", maximo=1)


def test_un_fallo_de_login_queda_registrado_aunque_la_peticion_se_deshaga(client):
    client.cookies.clear()
    assert client.post("/api/login", json={"username": "nadie", "password": "mala"}).status_code == 401
    assert LimiteIntentos().bloqueado("usuario|nadie", maximo=1)
