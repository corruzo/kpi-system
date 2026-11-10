"""Importación de fichas históricas en Excel: vista previa (no guarda nada) y confirmación (todo o nada)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..dominio import calendario
from ..errores import Conflicto, Invalido
from ..models import Catalogo, Indicador, Medicion, Unidad, Usuario, ahora
from . import auditoria, ejercicios, estructura, indicadores, lector_excel, mediciones


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
    """Lee el libro y propone códigos únicos; indica qué áreas (nodos de la estructura) ya existen y el inicio de ejercicio actual."""
    try:
        r = lector_excel.leer_libro(contenido, nombre_archivo)
    except ValueError as e:
        raise Invalido(str(e)) from None
    areas = {a.nombre.lower() for a in db.scalars(select(Unidad))}
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


def _nodos_por_nombre(db: Session) -> dict[str, Unidad]:
    """{nombre en minúsculas: nodo}. Si un nombre se repite en el árbol gana el de nivel más alto (el primero en orden de árbol)."""
    por_nombre: dict[str, Unidad] = {}
    for n in estructura.todas(db):
        por_nombre.setdefault(n.nombre.lower(), n)
    return por_nombre


def _resolver_nodo(db: Session, u: Usuario, nombre: str, gerencia: str, nodos: dict, nuevas: set, resumen: dict) -> Unidad:
    """El nodo del indicador: el que ya existe con ese nombre o, si se marcó para crearlo, un departamento nuevo bajo la
    gerencia de la planilla (que también se crea si falta). Sin gerencia en la planilla, se crea como gerencia."""
    nombre, gerencia = " ".join(nombre.split()), " ".join((gerencia or "").split())
    nodo = nodos.get(nombre.lower())
    if nodo:
        return nodo
    if nombre.lower() not in nuevas:
        raise Invalido(f"El área «{nombre}» no existe en la estructura. Márquela para crearla o elija otra.")
    padre = None
    if gerencia and gerencia.lower() != nombre.lower():
        padre = nodos.get(gerencia.lower())
        if padre is None:
            padre = estructura.crear(db, u, gerencia, "gerencia", None, origen="importación", confirmar=False)
            nodos[gerencia.lower()] = padre
            resumen["areas"] += 1
    if padre is not None and padre.nivel == "jefatura":
        raise Invalido(f"«{gerencia}» es una jefatura: no puede tener a «{nombre}» debajo.")
    nivel = "gerencia" if padre is None else ("departamento" if padre.nivel == "gerencia" else "jefatura")
    nodo = estructura.crear(db, u, nombre, nivel, padre.id if padre else None, origen="importación", confirmar=False)
    nodos[nombre.lower()] = nodo
    resumen["areas"] += 1
    return nodo


def _importar_mediciones(db: Session, admin: Usuario, ind: Indicador, datos_ind, archivo: str) -> list[str]:
    periodos = []
    for med in datos_ind.mediciones:
        if not calendario.periodo_valido(ind.frecuencia, med.periodo) or calendario.es_futuro(ind.frecuencia, med.periodo, calendario.hoy()):
            raise Invalido(f"{ind.codigo}: período «{med.periodo}» no válido para la frecuencia.")
        if med.periodo in periodos:
            raise Invalido(f"{ind.codigo}: período {med.periodo} repetido.")
        anio = calendario.ejercicio_de(ind.frecuencia, med.periodo)
        ejercicios.asegurar_creado(db, admin, anio)
        ejercicios.exigir_abierto(db, anio)
        r = mediciones.evaluar_carga(ind, dict(med.valores))   # el resultado se recalcula aquí: no se confía en el cliente
        if not r["ok"]:
            raise Invalido(f"{ind.codigo} {med.periodo}: {r['error']}")
        ahora_ = ahora()
        db.add(Medicion(
            indicador_id=ind.id, periodo=med.periodo, valores=r["valores"], resultado=r["resultado"], semaforo=r["semaforo"],
            nivel_optimo=ind.nivel_optimo, limite=ind.limite, sentido=ind.sentido, nivel_optimo_tope=ind.nivel_optimo_tope, limite_tope=ind.limite_tope,
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
    areas = _nodos_por_nombre(db)
    nuevas = {n.strip().lower() for n in datos.areas_nuevas}
    resumen = {"indicadores": 0, "mediciones": 0, "areas": 0, "catalogos": 0}
    codigos = set()
    for item in datos.indicadores:
        if item.codigo in codigos:
            raise Invalido(f"El código {item.codigo} está repetido en la importación.")
        codigos.add(item.codigo)
        item.nodo_id = _resolver_nodo(db, admin, item.area, item.gerencia, areas, nuevas, resumen).id
        try:
            indicadores.validar_ficha(db, item)
        except Invalido as e:
            raise Invalido(f"{item.codigo}: {e.detalle}") from None
        # llegan SIN responsable ni cargadores: el Coordinador SGC los asigna después en «Personas» o en la ficha
        ind = Indicador(**{**indicadores.campos_de_ficha(item), "responsable_id": None, "activo": True})
        db.add(ind)
        db.flush()
        periodos = _importar_mediciones(db, admin, ind, item, datos.archivo)
        resumen["indicadores"] += 1
        resumen["mediciones"] += len(periodos)
        auditoria.registrar(db, admin, "IMPORTACION", "indicador", ind.id,
                            {"codigo": ind.codigo, "archivo": datos.archivo, "hoja": item.hoja, "periodos": periodos}, ind)
    for nombre in sorted(nuevas - set(areas)):   # departamentos marcados que no tienen indicadores en este archivo
        original = next(n.strip() for n in datos.areas_nuevas if n.strip().lower() == nombre)
        _resolver_nodo(db, admin, original, "", areas, nuevas, resumen)
    resumen["catalogos"] = _importar_catalogos(db, admin, datos)
    db.commit()
    return resumen
