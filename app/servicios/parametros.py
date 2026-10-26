"""Parámetros del sistema (tabla clave/valor): empresa, gerencia emisora, código del formato y mes de inicio
del ejercicio fiscal. Mantiene sincronizado el calendario fiscal del proceso con el valor guardado."""
import os
import time
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..dominio import calendario
from ..errores import Conflicto
from ..models import Ejercicio, Indicador, Medicion, Parametro, Usuario
from . import auditoria, ejercicios, marca

_SEGUNDOS_CACHE = 30
_ultima_lectura = 0.0


def leer(db: Session) -> dict:
    """Parámetros guardados; además fija el mes de inicio del ejercicio en el calendario."""
    valores = {p.clave: p.valor for p in db.scalars(select(Parametro))}
    try:
        calendario.configurar(int(valores.get("ejercicio_inicio", 1)))
    except ValueError:
        calendario.configurar(1)
    return valores


def refrescar(forzar: bool = False) -> None:
    """Otro proceso pudo cambiar el ejercicio fiscal: se relee cada 30 s (o de inmediato si se fuerza)."""
    global _ultima_lectura
    if forzar or time.time() - _ultima_lectura > _SEGUNDOS_CACHE:
        with SessionLocal() as db:
            leer(db)
        _ultima_lectura = time.time()


def crear_faltantes(db: Session) -> None:
    """Crea los parámetros que no existan. En una base nueva el ejercicio inicia en octubre (práctica de la
    empresa); si ya hay cargas se conserva el calendario por año natural."""
    existentes = {p.clave for p in db.scalars(select(Parametro))}
    hay_datos = bool(db.scalar(select(func.count(Medicion.id))))
    por_defecto = {"empresa": "TRIPOLIVEN, C.A.", "gerencia_emisora": "Gerencia de Normalización y Calidad",
                   "codigo_formato": "NC-16-7",
                   "ejercicio_inicio": os.getenv("SIGT_EJERCICIO_INICIO", "1" if hay_datos else "10")}
    for clave, valor in por_defecto.items():
        if clave not in existentes:
            db.add(Parametro(clave=clave, valor=valor))
    db.commit()


def resumen(db: Session) -> dict:
    """Lo que la interfaz necesita saber de la configuración."""
    p = leer(db)
    hoy = date.today()
    vigente = calendario.ejercicio_de_fecha(hoy)
    return {"empresa": p.get("empresa", ""), "gerencia_emisora": p.get("gerencia_emisora", ""),
            "codigo_formato": p.get("codigo_formato", ""), "ejercicio_inicio": calendario.inicio_mes(),
            "ejercicio_actual": calendario.etiqueta_ejercicio(vigente), "ejercicio_vigente": vigente,
            "logo_url": marca.url_logo(db)}


def datos_para_reportes(db: Session) -> dict:
    """Encabezado de los reportes y fichas en Excel."""
    p = leer(db)
    return {"empresa": p.get("empresa", ""), "gerencia_emisora": p.get("gerencia_emisora", ""),
            "codigo_formato": p.get("codigo_formato", ""), "logo_bytes": marca.bytes_logo(db)}


def actualizar(db: Session, usuario: Usuario, datos) -> dict:
    actuales = leer(db)
    cambia_inicio = datos.ejercicio_inicio != calendario.inicio_mes()
    if cambia_inicio:
        if db.scalar(select(Ejercicio.anio).where(Ejercicio.estado == "cerrado").limit(1)):
            raise Conflicto("Hay ejercicios fiscales cerrados: reábralos antes de cambiar el mes de inicio.")
        if db.scalar(select(Medicion.id).join(Indicador).where(~Indicador.frecuencia.in_(("mensual", "eventual"))).limit(1)):
            raise Conflicto("Ya existen cargas bimestrales, trimestrales, cuatrimestrales, semestrales o anuales: "
                            "cambiar el mes de inicio del ejercicio fiscal alteraría sus períodos.")
    cambios = {}
    for clave, valor in {**datos.model_dump(), "ejercicio_inicio": str(datos.ejercicio_inicio)}.items():
        if actuales.get(clave) != valor:
            cambios[clave] = [actuales.get(clave), valor]
            fila = db.get(Parametro, clave)
            if fila:
                fila.valor = str(valor)
            else:
                db.add(Parametro(clave=clave, valor=str(valor)))
    if cambios:
        auditoria.registrar(db, usuario, "PARAMETROS_EDITADOS", "parametro", None, {"cambios": cambios})
    db.commit()
    leer(db)
    if cambia_inicio:
        ejercicios.recalcular(db, solo_nulos=False)
    return resumen(db)
