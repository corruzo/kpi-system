"""Reinicio de fábrica: borra todos los datos del sistema (indicadores, cargas, áreas, usuarios, parámetros,
logo y bitácora) y conserva únicamente la cuenta del administrador que lo ejecuta, para que pueda volver a entrar."""
from sqlalchemy import delete, text
from sqlalchemy.orm import Session

from .. import security
from ..database import ES_POSTGRES, Base
from ..errores import Invalido, NoAutenticado
from ..models import Bitacora, Usuario
from . import parametros, sesion

FRASE = "BORRAR TODO"


def borrar_todo(db: Session, u: Usuario, confirmacion: str, password: str) -> dict:
    """Exige la frase de confirmación y la contraseña del administrador; no deja rastro en la bitácora."""
    if confirmacion.strip() != FRASE:
        raise Invalido(f"Escriba exactamente «{FRASE}» para confirmar.")
    llave = f"reinicio|{u.id}"
    if sesion.limite_intentos.bloqueado(llave):
        raise NoAutenticado("Demasiados intentos fallidos. Intente de nuevo en 15 minutos.")
    if not security.verificar_password(password, u.password_hash):
        sesion.limite_intentos.fallo(llave)
        raise NoAutenticado("La contraseña no es correcta.")
    sesion.limite_intentos.limpiar(llave)

    conservar = u.id
    u.area_id = None                                    # las áreas se borran: la cuenta no puede apuntar a una
    db.flush()
    for tabla in reversed(Base.metadata.sorted_tables):  # primero las tablas que dependen de otras
        if tabla.name == Usuario.__tablename__:
            db.execute(delete(tabla).where(tabla.c.id != conservar))
        elif tabla.name == Bitacora.__tablename__ and ES_POSTGRES:
            db.execute(text('TRUNCATE TABLE "bitacora" RESTART IDENTITY'))   # el trigger solo impide DELETE/UPDATE por fila
        else:
            db.execute(delete(tabla))
    db.commit()
    parametros.crear_faltantes(db)                       # parámetros de fábrica
    parametros.refrescar(forzar=True)
    sesion.limite_intentos._fallos.clear()
    return {"ok": True, "conservado": u.username}
