"""Recordatorios de carga: qué personas tienen períodos pendientes de cargar y cuándo se les avisó por última vez.

El aviso en sí lo envía la persona desde su Outlook (la interfaz abre un correo ya redactado con `mailto:`); aquí solo se
calcula quién debe y se deja constancia en la bitácora. Alcance: únicamente indicadores del ÁMBITO de quien consulta
(su nodo y lo que cuelga de él) y, por tanto, únicamente las personas que los cargan."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..dominio import calendario
from ..errores import Invalido, NoEncontrado
from ..models import Bitacora, Indicador, Usuario
from . import acceso, auditoria, indicadores

ACCION = "RECORDATORIO"
MAX_PERIODOS_POR_INDICADOR = 12


def _ultimos_recordatorios(db: Session, ids: list[int]) -> dict[int, object]:
    if not ids:
        return {}
    filas = db.execute(select(Bitacora.entidad_id, func.max(Bitacora.fecha))
                       .where(Bitacora.accion == ACCION, Bitacora.entidad == "usuario", Bitacora.entidad_id.in_(ids)).group_by(Bitacora.entidad_id))
    return dict(filas.all())


def pendientes_por_persona(db: Session, u: Usuario) -> dict:
    """Períodos vencidos sin cargar (o devueltos para corregir) de los indicadores activos del ámbito de `u`, agrupados
    por cada persona que los carga. Un indicador con varios cargadores aparece en cada uno de ellos."""
    hoy = calendario.hoy()
    inds = list(db.scalars(select(Indicador).where(acceso.condicion_ambito(u)).order_by(Indicador.codigo)))
    estados = indicadores.estados_de_todos(db, [i.id for i in inds]) if inds else {}
    por_persona: dict[int, list[dict]] = {}
    personas: dict[int, Usuario] = {}
    sin_cargador = []
    for ind in inds:
        activos = [x for x in ind.cargadores if x.activo and x.id != u.id]
        for x in activos:
            personas[x.id] = x
        ests = estados.get(ind.id, {})
        pend = calendario.periodos_pendientes(ind.frecuencia, hoy, ests, ind.creado_en.date())
        if not pend:
            continue
        item = {"indicador_id": ind.id, "codigo": ind.codigo, "nombre": ind.nombre, "area": ind.nodo.nombre, "total": len(pend),
                "periodos": [{"periodo": p, "etiqueta": calendario.etiqueta(ind.frecuencia, p), "devuelto": ests.get(p) == "observado"}
                             for p in pend[:MAX_PERIODOS_POR_INDICADOR]]}
        if not [x for x in ind.cargadores if x.activo]:
            sin_cargador.append(item)
        for x in activos:
            por_persona.setdefault(x.id, []).append(item)
    ultimos = _ultimos_recordatorios(db, list(personas))
    lista = []
    for x in personas.values():
        items = por_persona.get(x.id, [])
        lista.append({"id": x.id, "nombre": x.nombre, "email": x.email or "",
                      "area": ", ".join(sorted({i["area"] for i in items})),
                      "total": sum(i["total"] for i in items), "devueltos": sum(p["devuelto"] for i in items for p in i["periodos"]),
                      "indicadores": items, "ultimo_recordatorio": ultimos.get(x.id)})
    lista.sort(key=lambda e: (-e["total"], e["nombre"]))
    return {"personas": lista, "sin_cargador": sin_cargador}


def registrar(db: Session, u: Usuario, usuario_id: int, plantilla: str) -> None:
    """Deja en la bitácora que se le recordó la carga a una persona (se llama al abrir el correo). Solo alcanza a quien
    carga algún indicador del ámbito de quien envía; para el resto responde como si no existiera."""
    destino = db.get(Usuario, usuario_id)
    if destino is not None:
        suyo = Indicador.id.in_(select(acceso.IndicadorCargador.indicador_id).where(acceso.IndicadorCargador.usuario_id == destino.id))
        if not db.scalar(select(Indicador.id).where(acceso.condicion_ambito(u), suyo).limit(1)):
            destino = None
    if destino is None or not destino.activo or destino.id == u.id:
        raise NoEncontrado("Persona no encontrada entre quienes cargan indicadores de su ámbito.")
    if not destino.email:
        raise Invalido("Esta persona no tiene correo registrado.")
    auditoria.registrar(db, u, ACCION, "usuario", destino.id, {"persona": destino.nombre, "correo": destino.email, "mensaje": plantilla[:40]})
    db.commit()
