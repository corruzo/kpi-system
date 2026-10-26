"""Conversión de los modelos y resultados de servicios al JSON que consume la interfaz."""
from ..dominio import calendario
from ..dominio.ficha_texto import meta_texto
from ..models import Area, Bitacora, Catalogo, Indicador, Medicion, Usuario


def iso(d):
    """Fecha/hora UTC en ISO 8601 con «Z»."""
    return d.isoformat() + "Z" if d else None


def fecha_iso(d):
    return d.isoformat() if d else None


def usuario(u: Usuario) -> dict:
    return {"id": u.id, "username": u.username, "nombre": u.nombre, "rol": u.rol, "area_id": u.area_id,
            "area": u.area.nombre if u.area else None, "activo": u.activo, "tour_visto": bool(u.tour_visto)}


def area(a: Area) -> dict:
    return {"id": a.id, "nombre": a.nombre}


def catalogo(c: Catalogo) -> dict:
    return {"id": c.id, "tipo": c.tipo, "valor": c.valor, "detalle": c.detalle or ""}


def indicador(i: Indicador) -> dict:
    return {"id": i.id, "codigo": i.codigo, "nombre": i.nombre, "objetivo": i.objetivo, "area_id": i.area_id,
            "area": i.area.nombre, "unidad": i.unidad, "frecuencia": i.frecuencia, "sentido": i.sentido,
            "formula": i.formula, "variables": i.variables, "constantes": i.constantes or [], "decimales": i.precision,
            "fuente": i.fuente or "", "notas": i.notas or "", "meta": i.meta, "limite": i.limite,
            "meta_tope": i.meta_tope, "limite_tope": i.limite_tope, "seguimiento": i.seguimiento or "proceso",
            "ref_nombre": i.ref_nombre or "", "ref_detalle": i.ref_detalle or "", "sigla": i.sigla or "",
            "gerencia": i.gerencia or "", "lider": i.lider or "", "resp_medicion": i.resp_medicion or "",
            "resp_registro": i.resp_registro or "", "resp_analisis": i.resp_analisis or "", "activo": i.activo}


def indicador_con_pendientes(i: Indicador, cargas: int, pendientes: list[str]) -> dict:
    return {**indicador(i), "n_mediciones": cargas,
            "pendientes": [{"periodo": p, "etiqueta": calendario.etiqueta(i.frecuencia, p)} for p in pendientes]}


def medicion(m: Medicion) -> dict:
    i = m.indicador
    return {"id": m.id, "indicador_id": i.id, "codigo": i.codigo, "indicador": i.nombre, "area": i.area.nombre,
            "area_id": i.area_id, "unidad": i.unidad, "frecuencia": i.frecuencia, "variables": i.variables,
            "periodo": m.periodo, "periodo_etiqueta": calendario.etiqueta(i.frecuencia, m.periodo),
            "valores": m.valores, "resultado": m.resultado, "decimales": m.precision, "formula": m.formula_aplicada,
            "constantes": m.constantes_aplicadas, "semaforo": m.semaforo, "meta": m.meta, "limite": m.limite,
            "meta_tope": m.meta_tope, "limite_tope": m.limite_tope, "sentido": m.sentido, "estado": m.estado,
            "analisis": m.analisis, "plan_mejora": m.plan_mejora, "version": m.version,
            "cargado_por": m.cargado_por.nombre, "cargado_por_id": m.cargado_por_id, "cargado_en": iso(m.cargado_en),
            "revisado_por": m.revisado_por.nombre if m.revisado_por else None, "revisado_en": iso(m.revisado_en),
            "nota_revision": m.nota_revision,
            "notas": [{"id": n.id, "usuario": n.usuario.nombre, "fecha": iso(n.fecha), "texto": n.texto} for n in m.notas]}


def bitacora(b: Bitacora, codigo: str | None = None) -> dict:
    return {"id": b.id, "fecha": iso(b.fecha), "usuario": b.usuario_nombre, "rol": b.rol, "accion": b.accion,
            "entidad": b.entidad, "entidad_id": b.entidad_id, "indicador_id": b.indicador_id, "area_id": b.area_id,
            "detalle": b.detalle, "hash": b.hash, "codigo": codigo}


# ---------------------------------------------------------------- ejercicios fiscales
def ejercicio(desc: dict) -> dict:
    """Descripción de un ejercicio (servicios.ejercicios.descripcion)."""
    fila = desc["fila"]
    cerrado = desc["estado"] == "cerrado"
    return {"anio": desc["anio"], "etiqueta": desc["etiqueta"], "desde": fecha_iso(desc["desde"]),
            "hasta": fecha_iso(desc["hasta"]), "estado": desc["estado"], "cerrado_por": desc["cerrado_por"],
            "cerrado_en": iso(fila.cerrado_en) if cerrado else None, "nota": (fila.nota or "") if fila else "",
            "reabierto_en": iso(fila.reabierto_en) if fila else None,
            "nota_reapertura": (fila.nota_reapertura or "") if fila else ""}


def fila_del_panel(f: dict) -> dict:
    """Un indicador del panel: ficha + último resultado, serie del ejercicio, mapa de calor y faltantes."""
    ind, ultimo = f["indicador"], f["ultimo"]
    f_ = ind.frecuencia
    return {**indicador(ind),
            "ultimo": ({"periodo": ultimo.periodo, "etiqueta": calendario.etiqueta(f_, ultimo.periodo),
                        "resultado": ultimo.resultado, "semaforo": ultimo.semaforo, "estado": ultimo.estado}
                       if ultimo else None),
            "serie": [{"periodo": m.periodo, "etiqueta": calendario.etiqueta(f_, m.periodo), "resultado": m.resultado,
                       "semaforo": m.semaforo, "meta": m.meta, "limite": m.limite} for m in f["validas"]],
            "celdas": f["celdas"], "faltantes": [calendario.etiqueta(f_, p) for p in f["faltantes"]],
            "devueltas": f["devueltas"], "tendencia": f["tendencia"]}


def ficha_periodos(periodos: list[dict]) -> list[dict]:
    return [{**{k: v for k, v in p.items() if k != "medicion"}, "medicion": medicion(p["medicion"]) if p["medicion"] else None}
            for p in periodos]


def indicador_en_ficha(i: Indicador) -> dict:
    return {**indicador(i), "meta_texto": meta_texto(i)}
