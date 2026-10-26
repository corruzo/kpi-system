"""Importación de fichas históricas en Excel: vista previa (no guarda nada) y confirmación (todo o nada)."""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..dominio import calendario
from ..errores import Conflicto, Invalido
from ..models import Area, Catalogo, Indicador, Medicion, Usuario, ahora
from . import auditoria, ejercicios, indicadores, lector_excel, mediciones, organizacion


# ---------------------------------------------------------------- vista previa
def _proponer_codigo(sigla: str, area: str, ocupados: set[str], orden: int) -> str:
    base = (sigla or area[:3] or "IND").upper().replace(" ", "")
    if sigla and base not in ocupados:
        return base
    codigo = f"{base[:3]}-{orden:02d}"
    while codigo in ocupados:
        orden += 1
        codigo = f"{base[:3]}-{orden:02d}"
    return codigo


def previsualizar(db: Session, contenido: bytes, nombre_archivo: str) -> dict:
    """Lee el libro y propone códigos únicos; indica qué áreas ya existen y el inicio de ejercicio actual."""
    try:
        r = lector_excel.leer_libro(contenido, nombre_archivo)
    except ValueError as e:
        raise Invalido(str(e)) from None
    areas = {a.nombre.lower() for a in db.scalars(select(Area))}
    ocupados = set(db.scalars(select(Indicador.codigo)))
    for orden, ind in enumerate(r["indicadores"], 1):
        ind["codigo"] = _proponer_codigo(ind["sigla"], ind["area"], ocupados, orden)
        ocupados.add(ind["codigo"])
        ind["area_existe"] = ind["area"].lower() in areas
    r["inicio_actual"] = calendario.inicio_mes()
    return r


# ---------------------------------------------------------------- confirmación
def _exigir_mismo_ejercicio(datos) -> None:
    usa_periodos_fiscales = any(i.frecuencia not in ("mensual", "eventual") and i.mediciones for i in datos.indicadores)
    if usa_periodos_fiscales and datos.inicio_ejercicio and datos.inicio_ejercicio != calendario.inicio_mes():
        raise Conflicto(f"Las fichas usan un ejercicio fiscal que inicia en el mes {datos.inicio_ejercicio}, pero el sistema "
                        f"está configurado en el mes {calendario.inicio_mes()}. Ajuste «Inicio del ejercicio fiscal» en "
                        "Organización → Parámetros y reintente.")


def _resolver_area(db: Session, admin: Usuario, nombre: str, areas: dict, nuevas: set, resumen: dict) -> Area:
    area = areas.get(nombre.strip().lower())
    if area:
        return area
    if nombre.strip().lower() not in nuevas:
        raise Invalido(f"El área «{nombre}» no existe. Márquela para crearla o elija otra.")
    area = organizacion.crear_area(db, admin, nombre, origen="importación", confirmar=False)
    areas[area.nombre.lower()] = area
    resumen["areas"] += 1
    return area


def _importar_mediciones(db: Session, admin: Usuario, ind: Indicador, datos_ind, archivo: str) -> list[str]:
    periodos = []
    for med in datos_ind.mediciones:
        if not calendario.periodo_valido(ind.frecuencia, med.periodo) or calendario.es_futuro(ind.frecuencia, med.periodo, date.today()):
            raise Invalido(f"{ind.codigo}: período «{med.periodo}» no válido para la frecuencia.")
        if med.periodo in periodos:
            raise Invalido(f"{ind.codigo}: período {med.periodo} repetido.")
        anio = calendario.ejercicio_de(ind.frecuencia, med.periodo)
        ejercicios.exigir_abierto(db, anio)
        r = mediciones.evaluar_carga(ind, dict(med.valores))   # el resultado se recalcula aquí: no se confía en el cliente
        if not r["ok"]:
            raise Invalido(f"{ind.codigo} {med.periodo}: {r['error']}")
        ahora_ = ahora()
        db.add(Medicion(
            indicador_id=ind.id, periodo=med.periodo, valores=r["valores"], resultado=r["resultado"], semaforo=r["semaforo"],
            meta=ind.meta, limite=ind.limite, sentido=ind.sentido, meta_tope=ind.meta_tope, limite_tope=ind.limite_tope,
            estado="aprobado", analisis=med.analisis.strip(), plan_mejora=med.plan_mejora.strip(), version=1,
            formula=ind.formula, constantes=ind.constantes or [], decimales=ind.precision, ejercicio=anio,
            cargado_por_id=admin.id, cargado_en=ahora_, revisado_por_id=admin.id, revisado_en=ahora_,
            nota_revision=f"Importado desde Excel «{archivo}» (hoja «{datos_ind.hoja}»)."))
        periodos.append(med.periodo)
    return periodos


def _importar_catalogos(db: Session, admin: Usuario, datos) -> int:
    existentes = {(c.tipo, c.valor.lower()) for c in db.scalars(select(Catalogo))}
    nuevos = 0
    for c in datos.catalogos:
        llave = (c.tipo, c.valor.strip().lower())
        if llave not in existentes:
            db.add(Catalogo(tipo=c.tipo, valor=c.valor.strip(), detalle=c.detalle.strip()))
            existentes.add(llave)
            nuevos += 1
    if nuevos:
        auditoria.registrar(db, admin, "CATALOGO_CREADO", "catalogo", None, {"cantidad": nuevos, "origen": f"importación {datos.archivo}"})
    return nuevos


def confirmar(db: Session, admin: Usuario, datos) -> dict:
    """Crea indicadores, mediciones históricas (aprobadas), áreas y listas de apoyo en una sola transacción."""
    _exigir_mismo_ejercicio(datos)
    areas = {a.nombre.lower(): a for a in db.scalars(select(Area))}
    nuevas = {n.strip().lower() for n in datos.areas_nuevas}
    resumen = {"indicadores": 0, "mediciones": 0, "areas": 0, "catalogos": 0}
    codigos = set()
    for item in datos.indicadores:
        if item.codigo in codigos:
            raise Invalido(f"El código {item.codigo} está repetido en la importación.")
        codigos.add(item.codigo)
        item.area_id = _resolver_area(db, admin, item.area, areas, nuevas, resumen).id
        try:
            indicadores.validar_ficha(db, item)
        except Invalido as e:
            raise Invalido(f"{item.codigo}: {e.detalle}") from None
        ind = Indicador(**indicadores.campos_de_ficha(item))
        db.add(ind)
        db.flush()
        periodos = _importar_mediciones(db, admin, ind, item, datos.archivo)
        resumen["indicadores"] += 1
        resumen["mediciones"] += len(periodos)
        auditoria.registrar(db, admin, "IMPORTACION", "indicador", ind.id,
                            {"codigo": ind.codigo, "archivo": datos.archivo, "hoja": item.hoja, "periodos": periodos}, ind)
    for nombre in sorted(nuevas - set(areas)):   # departamentos marcados que no tienen indicadores en este archivo
        original = next(n.strip() for n in datos.areas_nuevas if n.strip().lower() == nombre)
        organizacion.crear_area(db, admin, original, origen="importación", confirmar=False)
        resumen["areas"] += 1
    resumen["catalogos"] = _importar_catalogos(db, admin, datos)
    db.commit()
    return resumen
