"""Serialización de escrituras: advisory lock de la base en PostgreSQL, candado de hilos solo en SQLite."""
import pytest
from sqlalchemy.exc import DBAPIError

from app.api import deps
from app.errores import Ocupado
from app.servicios import concurrencia


class FalsaSesion:
    def __init__(self, fallar=False):
        self.sql, self.fallar, self.revertida = [], fallar, False

    def execute(self, consulta):
        if self.fallar:
            raise DBAPIError("SET LOCAL", {}, Exception("lock timeout"))
        self.sql.append(str(consulta))

    def rollback(self):
        self.revertida = True


def test_postgres_usa_el_advisory_lock_y_ningun_candado_en_memoria(monkeypatch):
    monkeypatch.setattr(deps, "ES_POSTGRES", True)
    db = FalsaSesion()
    pasos = deps.escritura(db)
    next(pasos)
    assert not concurrencia.candado_escritura.locked()
    assert any("lock_timeout" in s for s in db.sql) and any("pg_advisory_xact_lock(727001)" in s for s in db.sql)
    pasos.close()


def test_postgres_responde_ocupado_si_no_consigue_el_lock(monkeypatch):
    monkeypatch.setattr(deps, "ES_POSTGRES", True)
    db = FalsaSesion(fallar=True)
    with pytest.raises(Ocupado) as e:
        next(deps.escritura(db))
    assert e.value.estado == 503 and db.revertida


def test_sqlite_conserva_el_candado_de_hilos(monkeypatch):
    monkeypatch.setattr(deps, "ES_POSTGRES", False)
    db = FalsaSesion()
    pasos = deps.escritura(db)
    next(pasos)
    assert concurrencia.candado_escritura.locked() and db.sql == []
    pasos.close()
    assert not concurrencia.candado_escritura.locked()


def test_el_mismo_id_de_bloqueo_que_la_bitacora():
    import inspect

    from app.servicios import auditoria
    assert f"pg_advisory_xact_lock({concurrencia.ID_BLOQUEO_ESCRITURA})" in inspect.getsource(auditoria.registrar)
