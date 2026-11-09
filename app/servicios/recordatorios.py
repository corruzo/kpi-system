"""Recordatorios de carga: qué encargado de proceso tiene períodos pendientes y cuándo se le avisó por última vez.

El aviso en sí lo envía la persona desde su Outlook (la interfaz abre un correo ya redactado con `mailto:`); aquí solo se
calcula quién debe y se deja constancia en la bitácora de que se le recordó."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..dominio import calendario
from ..errores import Invalido, NoEncontrado
from ..models import Bitacora, Indicador, Usuario
from . import auditoria, indicadores

ACCION = "RECORDATORIO"
MAX_PERIODOS_POR_INDICADOR = 12


def _ultimos_recordatorios(db: Session) -> dict[int, object]:
    filas = db.execute(select(Bitacora.entidad_id, func.max(Bitacora.fecha))
                       .where(Bitacora.accion == ACCION, Bitacora.entidad == "usuario").group_by(Bitacora.entidad_id))
    return dict(filas.all())


def pendientes_por_encargado(db: Session) -> dict:
    """Todos los períodos vencidos sin cargar (o devueltos para corregir) de los indicadores activos, por encargado."""
    hoy = calendario.hoy()
    estados = indicadores.estados_de_todos(db)
    por_encargado: dict[int, list[dict]] = {}
    sin_encargado = []
    for ind in db.scalars(select(Indicador).where(Indicador.activo.is_(True)).order_by(Indicador.codigo)):
        ests = estados.get(ind.id, {})
        pend = calendario.periodos_pendientes(ind.frecuencia, hoy, ests, ind.creado_en.date())
        if not pend:
            continue
        item = {"indicador_id": ind.id, "codigo": ind.codigo, "nombre": ind.nombre, "area": ind.area.nombre, "total": len(pend),
                "periodos": [{"periodo": p, "etiqueta": calendario.etiqueta(ind.frecuencia, p), "devuelto": ests.get(p) == "observado"}
                             for p in pend[:MAX_PERIODOS_POR_INDICADOR]]}
        if ind.encargado_id is None:
            sin_encargado.append(item)
        else:
            por_encargado.setdefault(ind.encargado_id, []).append(item)
    ultimos = _ultimos_recordatorios(db)
    encargados = []
    for u in db.scalars(select(Usuario).where(Usuario.rol == "jefe", Usuario.activo.is_(True)).order_by(Usuario.nombre)):
        items = por_encargado.get(u.id, [])
        encargados.append({"id": u.id, "nombre": u.nombre, "email": u.email or "", "area": u.area.nombre if u.area else "",
                           "total": sum(i["total"] for i in items), "devueltos": sum(p["devuelto"] for i in items for p in i["periodos"]),
                           "indicadores": items, "ultimo_recordatorio": ultimos.get(u.id)})
    encargados.sort(key=lambda e: (-e["total"], e["nombre"]))
    return {"encargados": encargados, "sin_encargado": sin_encargado}


def registrar(db: Session, admin: Usuario, usuario_id: int, plantilla: str) -> None:
    """Deja en la bitácora que se le recordó la carga a un encargado (se llama al abrir el correo)."""
    u = db.get(Usuario, usuario_id)
    if not u or u.rol != "jefe":
        raise NoEncontrado("Encargado de proceso no encontrado.")
    if not u.email:
        raise Invalido("Este encargado no tiene correo registrado.")
    auditoria.registrar(db, admin, ACCION, "usuario", u.id, {"encargado": u.nombre, "correo": u.email, "mensaje": plantilla[:40]})
    db.commit()
