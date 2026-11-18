"""Historial de cambios de UN indicador: lo que la bitácora registró sobre él (ficha, asignación, metas, cargas, revisiones,
justificaciones), traducido a lenguaje legible: quién, qué cambió (antes → después) y cuándo.

La bitácora completa es técnica (solo la ve el Desarrollador); esto es la vista por indicador para quien tiene el permiso
`indicadores.historial` y ve el indicador. Solo lee: no agrega ni modifica nada."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..dominio import calendario
from ..models import Bitacora, Indicador, Usuario
from . import indicadores

CAMPOS = {
    "nombre": "Nombre", "objetivo": "Objetivo", "unidad": "Unidad", "frecuencia": "Frecuencia", "sentido": "Sentido",
    "formula": "Fórmula", "variables": "Variables", "constantes": "Constantes", "decimales": "Decimales", "fuente": "Fuente de datos",
    "notas": "Método y observaciones", "nivel_optimo": "Nivel óptimo", "limite": "Límite crítico",
    "nivel_optimo_tope": "Tope de la zona verde", "limite_tope": "Tope de la zona amarilla", "seguimiento": "Seguimiento de",
    "ref_nombre": "Proceso / objetivo", "ref_detalle": "Objetivo del proceso", "sigla": "Sigla", "gerencia": "Gerencia",
    "lider": "Líder de proceso", "resp_medicion": "Responsable de medición", "resp_registro": "Responsable de registro",
    "resp_analisis": "Responsable de análisis", "nodo": "Nodo de la estructura", "responsable": "Responsable principal",
    "suplente": "Suplente", "codigo": "Código",
}
TITULOS = {
    "INDICADOR_CREADO": "Indicador creado", "INDICADOR_EDITADO": "Ficha editada", "INDICADOR_ASIGNADO": "Asignación cambiada",
    "INDICADOR_ARCHIVADO": "Indicador archivado", "INDICADOR_RESTAURADO": "Indicador restaurado", "INDICADOR_ELIMINADO": "Indicador eliminado",
    "META_GUARDADA": "Meta modificada", "CARGA": "Carga enviada", "REENVIO": "Carga corregida y reenviada",
    "APROBACION": "Carga aprobada", "OBSERVACION": "Carga devuelta", "REAPERTURA": "Carga aprobada reabierta",
    "NOTA_AUDITORIA": "Nota de auditoría", "PERIODO_JUSTIFICADO": "Período justificado", "JUSTIFICACION_REVOCADA": "Justificación revocada",
    "IMPORTACION": "Importado desde Excel",
}
SEMAFORO = {"verde": "Verde", "amarillo": "Amarillo", "rojo": "Rojo"}
MAX_TEXTO = 300


def _valor(v) -> str:
    """Un valor de la ficha en texto corto y legible."""
    if v is None or v == "" or v == []:
        return "—"
    if isinstance(v, bool):
        return "Sí" if v else "No"
    if isinstance(v, float):
        return f"{v:g}"
    if isinstance(v, list):
        if v and isinstance(v[0], dict):   # variables o constantes: se resumen por su clave
            return ", ".join(str(x.get("clave") or x.get("etiqueta") or "?") for x in v)
        return ", ".join(_valor(x) for x in v)
    texto = str(v)
    return texto if len(texto) <= MAX_TEXTO else texto[:MAX_TEXTO] + "…"


def _cambio(campo: str, antes, despues) -> dict:
    return {"campo": CAMPOS.get(campo, campo), "antes": _valor(antes), "despues": _valor(despues)}


def _cambios(b: Bitacora, ind: Indicador) -> tuple[list[dict], str]:
    """([{campo, antes, despues}], nota) de una entrada de la bitácora."""
    d, a = b.detalle or {}, b.accion
    etiqueta = lambda p: calendario.etiqueta(ind.frecuencia, p) if p and calendario.periodo_valido(ind.frecuencia, p) else (p or "")   # noqa: E731
    if a in ("INDICADOR_EDITADO", "INDICADOR_ASIGNADO"):
        cambios = [_cambio(k, v[0], v[1]) for k, v in (d.get("cambios") or {}).items() if isinstance(v, list) and len(v) == 2]
        if d.get("dejan_de_cargar"):
            cambios.append({"campo": "Dejan de cargar", "antes": ", ".join(d["dejan_de_cargar"]), "despues": "—"})
        return cambios, d.get("origen", "")
    if a == "INDICADOR_CREADO":
        base = (("nodo", d.get("nodo")), ("responsable", d.get("responsable")), ("suplente", d.get("suplente")),
                ("formula", d.get("formula")), ("nivel_optimo", d.get("nivel_optimo")), ("limite", d.get("limite")), ("sentido", d.get("sentido")))
        return [_cambio(k, None, v) for k, v in base if v not in (None, "")], ""
    if a == "META_GUARDADA":
        return [{"campo": f"Meta de {etiqueta(p)}", "antes": _valor(c.get("antes")), "despues": _valor(c.get("despues"))}
                for p, c in (d.get("cambios") or {}).items() if isinstance(c, dict)], f"Ejercicio {d.get('ejercicio', '')}".strip()
    if a in ("CARGA", "REENVIO"):
        cambios = [{"campo": f"Período {etiqueta(d.get('periodo'))}", "antes": "—", "despues": _valor(d.get("resultado"))}]
        if d.get("semaforo"):
            cambios.append({"campo": "Semáforo", "antes": "—", "despues": SEMAFORO.get(d["semaforo"], d["semaforo"])})
        return cambios, ""
    if a in ("APROBACION", "OBSERVACION", "REAPERTURA"):
        return [{"campo": "Período", "antes": "—", "despues": etiqueta(d.get("periodo"))}], d.get("nota", "")
    if a in ("PERIODO_JUSTIFICADO", "JUSTIFICACION_REVOCADA"):
        return [{"campo": "Período", "antes": "—", "despues": d.get("etiqueta") or etiqueta(d.get("periodo"))},
                {"campo": "Tipo", "antes": "—", "despues": str(d.get("tipo", "")).replace("_", " ")}], d.get("motivo", "")
    if a == "NOTA_AUDITORIA":
        return [{"campo": "Período", "antes": "—", "despues": etiqueta(d.get("periodo"))}], d.get("texto", "")
    if a == "IMPORTACION":
        return [{"campo": "Períodos importados", "antes": "—", "despues": str(len(d.get("periodos") or []))}], d.get("archivo", "")
    return [], ""


def entrada(b: Bitacora, ind: Indicador) -> dict:
    cambios, nota = _cambios(b, ind)
    return {"id": b.id, "fecha": b.fecha.isoformat(timespec="seconds"), "usuario": b.usuario_nombre, "rol": b.rol, "accion": b.accion,
            "titulo": TITULOS.get(b.accion, b.accion), "cambios": cambios, "nota": nota}


def de_indicador(db: Session, u: Usuario, indicador_id: int, desde: int = 0, limite: int = 50) -> tuple[int, list[dict]]:
    """(total, página) del historial del indicador, de lo más reciente a lo más antiguo. Si la persona no ve el indicador, 404."""
    ind = indicadores.obtener_visible(db, u, indicador_id)
    total = db.scalar(select(func.count(Bitacora.id)).where(Bitacora.indicador_id == ind.id)) or 0
    filas = db.scalars(select(Bitacora).where(Bitacora.indicador_id == ind.id).order_by(Bitacora.id.desc())
                       .offset(max(desde, 0)).limit(max(1, min(limite, 200))))
    return total, [entrada(b, ind) for b in filas]
