"""Presupuesto anual por indicador (paso 3 del flujo): qué se espera lograr en cada período del ejercicio.

El presupuesto se guarda por período de la frecuencia del indicador (12 valores si es mensual, 4 si es trimestral,
1 si es anual…). Se puede escribir período a período o dar un valor anual y repartirlo. Cada cambio queda en la bitácora.
Un período que ya tiene dato real cargado no admite cambios: se compara contra lo que se presupuestó al inicio.
"""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..dominio import calendario, presupuesto
from ..errores import Conflicto, Invalido, NoEncontrado
from ..models import Area, Indicador, Medicion, Presupuesto, Usuario, ahora
from . import auditoria, ejercicios


def se_presupuesta(ind: Indicador) -> bool:
    """Los indicadores «eventuales» se cargan cuando ocurren: no tienen calendario que presupuestar."""
    return ind.frecuencia != "eventual"


def periodos_de(ind: Indicador, anio: int) -> list[str]:
    return calendario.periodos_del_ejercicio(ind.frecuencia, anio) if se_presupuesta(ind) else []


def del_periodo(db: Session, indicador_id: int, periodo: str) -> float | None:
    fila = db.scalar(select(Presupuesto).where(Presupuesto.indicador_id == indicador_id, Presupuesto.periodo == periodo))
    return fila.valor if fila else None


def exigir_presupuestado(db: Session, ind: Indicador, periodo: str) -> float | None:
    """Presupuesto del período; si el indicador debe tenerlo y falta, lanza Conflicto."""
    if not se_presupuesta(ind):
        return None
    valor = del_periodo(db, ind.id, periodo)
    if valor is None:
        raise Conflicto("Este período todavía no tiene presupuesto. Pida al administrador que lo ingrese en "
                        "«Período y presupuesto» antes de cargar el dato real.")
    return valor


# ---------------------------------------------------------------- consulta
def _indicadores(db: Session, area_id: int | None):
    q = select(Indicador).where(Indicador.activo.is_(True)).order_by(Indicador.codigo)
    if area_id:
        q = q.where(Indicador.area_id == area_id)
    return list(db.scalars(q))


def matriz(db: Session, anio: int, area_id: int | None = None) -> dict:
    """Presupuesto del ejercicio: por indicador, sus períodos con valor (o vacío) y si ya tienen dato real."""
    guardados = {(p.indicador_id, p.periodo): p.valor for p in db.scalars(select(Presupuesto).where(Presupuesto.ejercicio == anio))}
    cargados = {(m.indicador_id, m.periodo) for m in db.scalars(select(Medicion).where(Medicion.ejercicio == anio))}
    filas, completos, total = [], 0, 0
    for ind in _indicadores(db, area_id):
        periodos = periodos_de(ind, anio)
        if not periodos:
            continue
        items = [{"periodo": p, "etiqueta": calendario.etiqueta(ind.frecuencia, p), "corta": calendario.etiqueta_corta(ind.frecuencia, p),
                  "valor": guardados.get((ind.id, p)), "bloqueado": (ind.id, p) in cargados} for p in periodos]
        con_valor = sum(i["valor"] is not None for i in items)
        total += 1
        completos += con_valor == len(items)
        filas.append({"indicador_id": ind.id, "codigo": ind.codigo, "nombre": ind.nombre, "area": ind.area.nombre,
                      "area_id": ind.area_id, "unidad": ind.unidad, "frecuencia": ind.frecuencia, "sentido": ind.sentido,
                      "decimales": ind.precision, "periodos": items, "completo": con_valor == len(items), "con_valor": con_valor})
    return {"ejercicio": anio, "etiqueta": calendario.etiqueta_ejercicio(anio), "indicadores": filas,
            "resumen": {"total": total, "completos": completos, "pendientes": total - completos}}


def resumen(db: Session, anio: int) -> dict:
    return matriz(db, anio)["resumen"]


# ---------------------------------------------------------------- escritura
def guardar(db: Session, u: Usuario, anio: int, indicador_id: int, valores: dict[str, float], confirmar: bool = True) -> dict:
    """Guarda (crea o cambia) el presupuesto de un indicador. `valores`: {período: valor}.
    `confirmar=False` deja la transacción abierta para que quien llama confirme una sola vez (todo o nada)."""
    ejercicios.exigir_creado(db, anio)
    ejercicios.exigir_abierto(db, anio)
    ind = db.get(Indicador, indicador_id)
    if not ind or not ind.activo:
        raise NoEncontrado("Indicador no encontrado.")
    if not se_presupuesta(ind):
        raise Invalido("Los indicadores eventuales no se presupuestan: se cargan cuando ocurren.")
    validos = set(periodos_de(ind, anio))
    if not valores:
        raise Invalido("No hay valores que guardar.")
    desconocidos = sorted(set(valores) - validos)
    if desconocidos:
        raise Invalido("Períodos que no pertenecen a este indicador en el ejercicio: " + ", ".join(desconocidos) + ".")
    existentes = {p.periodo: p for p in db.scalars(select(Presupuesto).where(Presupuesto.indicador_id == ind.id,
                                                                            Presupuesto.periodo.in_(list(valores))))}
    cargados = set(db.scalars(select(Medicion.periodo).where(Medicion.indicador_id == ind.id, Medicion.periodo.in_(list(valores)))))
    cambios = {}
    for periodo, valor in valores.items():
        previo = existentes.get(periodo)
        if previo and previo.valor == valor:
            continue
        if periodo in cargados:
            raise Conflicto(f"El período {calendario.etiqueta(ind.frecuencia, periodo)} ya tiene dato real cargado: "
                            "su presupuesto no puede cambiarse.")
        if previo:
            previo.valor, previo.actualizado_por_id, previo.actualizado_en = valor, u.id, ahora()
        else:
            db.add(Presupuesto(ejercicio=anio, indicador_id=ind.id, periodo=periodo, valor=valor,
                               actualizado_por_id=u.id, actualizado_en=ahora()))
        cambios[periodo] = {"antes": previo.valor if previo else None, "despues": valor}
    if cambios:
        auditoria.registrar(db, u, "PRESUPUESTO_GUARDADO", "presupuesto", ind.id,
                            {"ejercicio": calendario.etiqueta_ejercicio(anio), "cambios": cambios}, ind)
    if confirmar:
        db.commit()
    return {"guardados": len(cambios)}


def repartir_anual(db: Session, u: Usuario, anio: int, indicador_id: int, valor: float, modo: str) -> dict:
    """Atajo: un valor anual repartido entre todos los períodos del ejercicio del indicador."""
    ind = db.get(Indicador, indicador_id)
    if not ind:
        raise NoEncontrado("Indicador no encontrado.")
    periodos = periodos_de(ind, anio)
    if not periodos:
        raise Invalido("Los indicadores eventuales no se presupuestan.")
    try:
        partes = presupuesto.repartir(valor, len(periodos), modo, ind.precision + 2)
    except ValueError as e:
        raise Invalido(str(e)) from None
    return guardar(db, u, anio, indicador_id, dict(zip(periodos, partes, strict=True)))


def copiar_de(db: Session, u: Usuario, anio: int, origen: int) -> dict:
    """Copia el presupuesto de otro ejercicio a este (solo indicadores sin presupuesto aquí), período a período por posición."""
    ejercicios.exigir_creado(db, anio)
    ejercicios.exigir_abierto(db, anio)
    anteriores = {(p.indicador_id, p.periodo): p.valor for p in db.scalars(select(Presupuesto).where(Presupuesto.ejercicio == origen))}
    copiados = 0
    for ind in _indicadores(db, None):
        destino, fuente = periodos_de(ind, anio), periodos_de(ind, origen)
        if not destino or any(del_periodo(db, ind.id, p) is not None for p in destino):
            continue
        valores = [anteriores.get((ind.id, p)) for p in fuente]
        if any(v is None for v in valores):
            continue
        guardar(db, u, anio, ind.id, dict(zip(destino, valores, strict=True)), confirmar=False)
        copiados += 1
    db.commit()      # una sola transacción: o se copian todos los indicadores o ninguno
    return {"indicadores": copiados}


# ---------------------------------------------------------------- puesta en marcha (guía del administrador)
def avance_de_puesta_en_marcha(db: Session, hoy: date) -> dict:
    """Estado de cada paso para arrancar el sistema, en el orden en que deben hacerse."""
    n_areas = len(list(db.scalars(select(Area.id))))
    usuarios = list(db.scalars(select(Usuario).where(Usuario.activo.is_(True))))
    jefes = [x for x in usuarios if x.rol == "jefe" and x.area_id]
    n_ind = len(list(db.scalars(select(Indicador.id).where(Indicador.activo.is_(True)))))
    anio = calendario.ejercicio_de_fecha(hoy)
    periodo_creado = ejercicios.creado(db, anio)
    pres = resumen(db, anio) if periodo_creado else {"total": 0, "completos": 0, "pendientes": 0}
    cargas = len(list(db.scalars(select(Medicion.id).where(Medicion.ejercicio == anio))))
    return {"ejercicio": anio, "etiqueta": calendario.etiqueta_ejercicio(anio), "pasos": [
        {"id": "org", "hecho": n_areas > 0 and bool(jefes), "detalle": f"{n_areas} área(s) · {len(jefes)} jefe(s) de área"},
        {"id": "fichas", "hecho": n_ind > 0, "detalle": f"{n_ind} indicador(es)"},
        {"id": "periodo", "hecho": periodo_creado, "detalle": calendario.etiqueta_ejercicio(anio) + (" creado" if periodo_creado else " sin crear")},
        {"id": "presupuesto", "hecho": periodo_creado and pres["total"] > 0 and pres["pendientes"] == 0,
         "detalle": f"{pres['completos']} de {pres['total']} indicadores presupuestados"},
        {"id": "carga", "hecho": cargas > 0, "detalle": f"{cargas} carga(s) en el ejercicio"},
    ]}
