"""Panel de análisis (dashboard) de un ejercicio fiscal con comparativo contra el anterior."""
from datetime import date

from sqlalchemy.orm import Session

from ..dominio import calendario
from . import ejercicios


def _atencion(filas: list[dict], estado_ejercicio: str) -> list[dict]:
    """Indicadores que requieren acción: críticos, en alerta y empeorando, o con períodos sin cargar."""
    items = []
    for f in filas:
        ind, ultimo = f["indicador"], f["ultimo"]
        base = {"id": ind.id, "codigo": ind.codigo, "nombre": ind.nombre, "area": ind.area.nombre,
                "unidad": ind.unidad, "decimales": ind.precision}
        etiqueta = calendario.etiqueta(ind.frecuencia, ultimo.periodo) if ultimo else ""
        if ultimo and ultimo.semaforo == "rojo":
            items.append({**base, "nivel": 3, "motivo": f"Crítico en {etiqueta}", "semaforo": "rojo", "resultado": ultimo.resultado})
        elif ultimo and ultimo.semaforo == "amarillo" and f["tendencia"] and f["tendencia"]["mejora"] is False:
            items.append({**base, "nivel": 2, "motivo": f"En alerta y empeorando ({etiqueta})", "semaforo": "amarillo",
                          "resultado": ultimo.resultado})
        if f["faltantes"] and estado_ejercicio in ("vigente", "terminado"):
            etiquetas = [calendario.etiqueta(ind.frecuencia, p) for p in f["faltantes"]]
            items.append({**base, "nivel": 1, "semaforo": None, "resultado": None,
                          "motivo": f"Sin cargar: {', '.join(etiquetas[:3])}" + ("…" if len(etiquetas) > 3 else "")})
    return sorted(items, key=lambda a: -a["nivel"])[:12]


def _avance_del_tiempo(inicio: date, fin: date, hoy: date) -> float:
    if hoy < inicio:
        return 0.0
    dias = (fin - inicio).days + 1
    return round(max(0.0, min(1.0, ((min(hoy, fin) - inicio).days + 1) / dias)), 4)


def construir(db: Session, anio: int, area_id: int | None = None, hoy: date | None = None) -> dict:
    hoy = hoy or date.today()
    desc = ejercicios.descripcion(db, anio, hoy)
    actual = ejercicios.foto(db, anio, area_id, hoy)
    anterior = ejercicios.foto(db, anio - 1, area_id, hoy)
    cumplimiento_previo = {a["area"]: a["cumplimiento"] for a in anterior["por_area"]}
    for a in actual["por_area"]:
        a["cumplimiento_anterior"] = cumplimiento_previo.get(a["area"])
    comparativo = None
    if anterior["resumen"]["cargas"]:   # sin mediciones el año anterior no es comparable
        comparativo = {"etiqueta": calendario.etiqueta_ejercicio(anio - 1), "cumplimiento": anterior["resumen"]["cumplimiento"],
                       "total": anterior["resumen"]["total"]}
    return {"descripcion": desc, "avance": _avance_del_tiempo(desc["desde"], desc["hasta"], hoy),
            "meses": calendario.meses_del_ejercicio(), "foto": actual, "anterior": comparativo,
            "atencion": _atencion(actual["filas"], desc["estado"])}
