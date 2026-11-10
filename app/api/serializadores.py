"""Conversión de los modelos y resultados de servicios al JSON que consume la interfaz."""
from ..dominio import calendario
from ..dominio.ficha_texto import nivel_optimo_texto
from ..dominio.meta import comparar
from ..models import Bitacora, Catalogo, Indicador, Medicion, Unidad, Usuario
from ..servicios import acceso


def iso(d):
    """Fecha/hora UTC en ISO 8601 con «Z»."""
    return d.isoformat() + "Z" if d else None


def fecha_iso(d):
    return d.isoformat() if d else None


def usuario(u: Usuario) -> dict:
    """Datos básicos de una cuenta (sin rol ni ámbito: eso lo agregan `sesion` y `persona`)."""
    return {"id": u.id, "username": u.username, "nombre": u.nombre, "email": u.email or "", "activo": u.activo,
            "tour_visto": bool(u.tour_visto)}


def sesion(u: Usuario) -> dict:
    """El usuario de la sesión con lo que la interfaz necesita para mostrar solo lo permitido (el servidor decide igual)."""
    c = acceso.contexto(u)
    return {**usuario(u), "rol": c.rol or None, "rol_clave": c.clave, "pendiente": not c.rol, "permisos": c.permisos,
            "alcance_total": c.total, "alcance_global": c.global_, "ambito": [i for i, _ in c.ambito], "miembro": [i for i, _ in c.miembro]}


def persona(u: Usuario, detalle: dict) -> dict:
    return {**usuario(u), **detalle}


def unidad(n: Unidad, ruta_nombres: str = "", personas: int | None = None, indicadores: int | None = None) -> dict:
    d = {"id": n.id, "nombre": n.nombre, "nivel": n.nivel, "padre_id": n.padre_id, "profundidad": n.ruta.count("/") - 2,
         "ruta": ruta_nombres or n.nombre}
    if personas is not None:
        d.update(personas=personas, indicadores=indicadores or 0)
    return d


def catalogo(c: Catalogo) -> dict:
    return {"id": c.id, "tipo": c.tipo, "valor": c.valor, "detalle": c.detalle or ""}


def indicador(i: Indicador, u: Usuario | None = None) -> dict:
    """Con `u`, agrega la relación de esa persona con el indicador (la interfaz muestra así solo los botones que aplican)."""
    d = {"id": i.id, "codigo": i.codigo, "nombre": i.nombre, "objetivo": i.objetivo, "nodo_id": i.nodo_id, "area": i.nodo.nombre,
         "nivel": i.nodo.nivel, "responsable_id": i.responsable_id, "responsable": i.responsable.nombre if i.responsable else None,
         "cargadores": [x.id for x in i.cargadores], "cargadores_info": [{"id": x.id, "nombre": x.nombre} for x in i.cargadores],
         "unidad": i.unidad, "frecuencia": i.frecuencia, "sentido": i.sentido,
         "formula": i.formula, "variables": i.variables, "constantes": i.constantes or [], "decimales": i.precision,
         "fuente": i.fuente or "", "notas": i.notas or "", "nivel_optimo": i.nivel_optimo, "limite": i.limite,
         "nivel_optimo_tope": i.nivel_optimo_tope, "limite_tope": i.limite_tope, "seguimiento": i.seguimiento or "proceso",
         "ref_nombre": i.ref_nombre or "", "ref_detalle": i.ref_detalle or "", "sigla": i.sigla or "",
         "gerencia": i.gerencia or "", "lider": i.lider or "", "resp_medicion": i.resp_medicion or "",
         "resp_registro": i.resp_registro or "", "resp_analisis": i.resp_analisis or "", "activo": i.activo}
    if u is not None:
        total = acceso.alcance_total(u)
        d.update(soy_responsable=total or acceso.es_responsable(u, i), soy_cargador=acceso.puede_cargar(u, i),
                 en_ambito=acceso.en_ambito(u, i))
    return d


def indicador_con_pendientes(i: Indicador, cargas: int, pendientes: list[str], otros: dict[int, int], u: Usuario | None = None) -> dict:
    return {**indicador(i, u), "n_mediciones": cargas,
            "pendientes": [{"periodo": p, "etiqueta": calendario.etiqueta(i.frecuencia, p)} for p in pendientes],
            "pendientes_otros": [{"ejercicio": a, "etiqueta": calendario.etiqueta_ejercicio(a), "n": n} for a, n in sorted(otros.items())]}


def medicion(m: Medicion) -> dict:
    i = m.indicador
    return {"id": m.id, "indicador_id": i.id, "codigo": i.codigo, "indicador": i.nombre, "area": i.nodo.nombre,
            "nodo_id": i.nodo_id, "unidad": i.unidad, "frecuencia": i.frecuencia, "variables": i.variables,
            "periodo": m.periodo, "periodo_etiqueta": calendario.etiqueta(i.frecuencia, m.periodo),
            "ejercicio": (anio := m.ejercicio or calendario.ejercicio_de(i.frecuencia, m.periodo)),
            "ejercicio_etiqueta": calendario.etiqueta_ejercicio(anio),
            "valores": m.valores, "resultado": m.resultado, "decimales": m.precision, "formula": m.formula_aplicada,
            "constantes": m.constantes_aplicadas, "semaforo": m.semaforo, "nivel_optimo": m.nivel_optimo, "limite": m.limite,
            "nivel_optimo_tope": m.nivel_optimo_tope, "limite_tope": m.limite_tope, "sentido": m.sentido, "estado": m.estado,
            "meta": m.meta, "vs_meta": comparar(m.resultado, m.meta, m.sentido),
            "analisis": m.analisis, "plan_mejora": m.plan_mejora, "version": m.version,
            "cargado_por": m.cargado_por.nombre, "cargado_por_id": m.cargado_por_id, "cargado_en": iso(m.cargado_en),
            "revisado_por": m.revisado_por.nombre if m.revisado_por else None, "revisado_en": iso(m.revisado_en),
            "nota_revision": m.nota_revision,
            "notas": [{"id": n.id, "usuario": n.usuario.nombre, "fecha": iso(n.fecha), "texto": n.texto} for n in m.notas]}


def bitacora(b: Bitacora, codigo: str | None = None) -> dict:
    return {"id": b.id, "fecha": iso(b.fecha), "usuario": b.usuario_nombre, "rol": b.rol, "accion": b.accion,
            "entidad": b.entidad, "entidad_id": b.entidad_id, "indicador_id": b.indicador_id, "nodo_id": b.nodo_id,
            "detalle": b.detalle, "hash": b.hash, "codigo": codigo}


# ---------------------------------------------------------------- ejercicios fiscales
def ejercicio(desc: dict) -> dict:
    """Descripción de un ejercicio (servicios.ejercicios.descripcion)."""
    fila = desc["fila"]
    cerrado = desc["estado"] == "cerrado"
    return {"anio": desc["anio"], "etiqueta": desc["etiqueta"], "desde": fecha_iso(desc["desde"]),
            "hasta": fecha_iso(desc["hasta"]), "estado": desc["estado"], "creado": desc["creado"],
            "creado_en": iso(fila.creado_en) if fila else None, "cerrado_por": desc["cerrado_por"],
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
                       "semaforo": m.semaforo, "nivel_optimo": m.nivel_optimo, "limite": m.limite, "meta": m.meta}
                      for m in f["validas"]],
            "vs_meta": _resumen_meta(f["validas"]),
            "celdas": f["celdas"], "faltantes": [calendario.etiqueta(f_, p) for p in f["faltantes"]],
            "devueltas": f["devueltas"], "tendencia": f["tendencia"]}


def _resumen_meta(validas) -> dict:
    """Cuántas cargas tenían meta y cuántas la alcanzaron."""
    con = [m for m in validas if m.meta is not None]
    return {"con_meta": len(con), "cumplen": sum(comparar(m.resultado, m.meta, m.sentido)["cumple"] for m in con)}


def ficha_periodos(periodos: list[dict]) -> list[dict]:
    return [{**{k: v for k, v in p.items() if k != "medicion"}, "medicion": medicion(p["medicion"]) if p["medicion"] else None}
            for p in periodos]


def indicador_en_ficha(i: Indicador, u: Usuario | None = None) -> dict:
    return {**indicador(i, u), "nivel_optimo_texto": nivel_optimo_texto(i)}
