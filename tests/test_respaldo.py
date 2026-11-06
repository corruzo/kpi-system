"""Respaldo cifrado: se abre solo con la frase, detecta alteraciones y restaura todo (incluida la cadena de la bitácora)."""
import pytest
from conftest import CLAVE_ADMIN, crear_area, crear_indicador, crear_usuario, entrar
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import sessionmaker

from app.database import Base, SessionLocal
from app.errores import Conflicto, Invalido
from app.servicios import auditoria, respaldo

FRASE = "frase-de-prueba-larga-123"


@pytest.fixture()
def con_datos(client):
    area = crear_area(client)
    crear_usuario(client, "jefe", area)
    crear_indicador(client, area)


def _base_vacia(tmp_path):
    motor = create_engine(f"sqlite:///{tmp_path / 'destino.db'}")
    Base.metadata.create_all(motor)
    with SessionLocal() as db:
        revision = respaldo._revision(db)
    with motor.begin() as c:
        if revision:
            c.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
            c.execute(text("INSERT INTO alembic_version VALUES (:v)"), {"v": revision})
    return sessionmaker(motor)


def test_crear_verificar_y_restaurar_en_una_base_vacia(client, con_datos, tmp_path):
    with SessionLocal() as db:
        archivo, resumen = respaldo.crear(db, FRASE)
        origen = {t.name: db.scalar(select(func.count()).select_from(t)) for t in Base.metadata.sorted_tables}
    assert resumen["bitacora_ok"] and resumen["tablas"] == origen and archivo.startswith(respaldo.MAGIA)
    assert respaldo.verificar(archivo, FRASE)["ok"]
    with _base_vacia(tmp_path)() as destino:
        r = respaldo.restaurar(destino, archivo, FRASE)
        assert r["ok"] and auditoria.verificar(destino)["ok"]
        assert {t.name: destino.scalar(select(func.count()).select_from(t)) for t in Base.metadata.sorted_tables} == origen
        with pytest.raises(Conflicto):   # ya no está vacía: no se sobrescribe
            respaldo.restaurar(destino, archivo, FRASE)


def test_frase_incorrecta_y_archivo_alterado_se_rechazan(client, con_datos):
    with SessionLocal() as db:
        archivo, _ = respaldo.crear(db, FRASE)
    with pytest.raises(Invalido):
        respaldo.abrir(archivo, "otra-frase-distinta-456")
    alterado = bytearray(archivo)
    alterado[-20] ^= 0xFF
    with pytest.raises(Invalido):
        respaldo.abrir(bytes(alterado), FRASE)
    with pytest.raises(Invalido):
        respaldo.abrir(b"no es un respaldo", FRASE)
    with SessionLocal() as db, pytest.raises(Invalido):
        respaldo.crear(db, "corta")


def test_el_respaldo_no_deja_datos_legibles_y_solo_lo_descarga_el_admin(client, con_datos):
    entrar(client, "admin", CLAVE_ADMIN)
    r = client.post("/api/respaldo", json={"frase": FRASE})
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    assert b"password_hash" not in r.content and b"admin" not in r.content
    assert client.post("/api/respaldo", json={"frase": "corta"}).status_code == 422
    from conftest import CLAVE
    jefe = crear_usuario(client, "jefe", crear_area(client))
    entrar(client, jefe, CLAVE)
    assert client.post("/api/respaldo", json={"frase": FRASE}).status_code == 403
