"""Datos de demostración basados en los procesos de Tripoliven, C.A."""
import random
from datetime import date, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import audit, calc
from .models import Area, Indicador, Medicion, NotaAuditoria, Usuario, ahora
from .security import hash_password

CLAVE_DEMO = "tripoliven2026"

AREAS = ["Sistemas", "Producción", "Mantenimiento", "Calidad", "Logística",
         "Almacén", "Compras", "Seguridad y Ambiente", "Recursos Humanos"]

USUARIOS = [
    ("j.sistemas", "Carlos Rondón", "jefe", "Sistemas"),
    ("j.produccion", "María Fernández", "jefe", "Producción"),
    ("j.mantenimiento", "José Pérez", "jefe", "Mantenimiento"),
    ("j.calidad", "Andreína Salas", "jefe", "Calidad"),
    ("j.logistica", "Luis Ortega", "jefe", "Logística"),
    ("j.almacen", "Rosa Medina", "jefe", "Almacén"),
    ("j.compras", "Pedro Linares", "jefe", "Compras"),
    ("j.sha", "Ana Villalobos", "jefe", "Seguridad y Ambiente"),
    ("j.rrhh", "Gabriela Torres", "jefe", "Recursos Humanos"),
    ("gerente", "Ing. Ricardo Mendoza (Gerente / Auditor SGC)", "gerente", None),
    ("admin", "Lic. Flavya Curiel (Administradora SGC)", "admin", "Calidad"),
]


def _ratio(lo, hi):
    """vars[0] / vars[1] * 100 ≈ objetivo."""
    def g(t, r, vs):
        den = r.randint(lo, hi)
        return {vs[0]: round(den * t / 100), vs[1]: den}
    return g


def _directo(t, r, vs):
    return {vs[0]: t}


def _ahorro(t, r, vs):
    ejec = r.randint(40000, 60000)
    return {vs[0]: ejec + t, vs[1]: ejec}


def _horas(t, r, vs):  # disponibilidad: (cal - parada)/cal*100
    cal = r.choice([2160, 2880])
    return {vs[0]: cal, vs[1]: round(cal * (100 - t) / 100)}


def _dias(lo, hi):
    def g(t, r, vs):
        n = r.randint(lo, hi)
        return {vs[0]: round(t * n), vs[1]: n}
    return g


V = lambda *p: [{"clave": c, "etiqueta": e} for c, e in p]  # noqa: E731

# código, nombre, objetivo, área, unidad, frecuencia, sentido, meta, límite, variables, fórmula, generador, serie
INDICADORES = [
    ("SIS-01", "Cumplimiento de solicitudes de soporte", "Atender oportunamente las solicitudes de soporte técnico de los usuarios.",
     "Sistemas", "%", "mensual", "mayor", 90, 80,
     V(("gestionadas", "Solicitudes gestionadas"), ("recibidas", "Solicitudes recibidas")),
     "gestionadas / recibidas * 100", _ratio(110, 160), [92, 94, 89, 91, 86, 93]),
    ("SIS-02", "Disponibilidad de servicios de TI", "Garantizar la continuidad de ERP, red y servidores.",
     "Sistemas", "%", "mensual", "mayor", 99, 95,
     V(("horas_operativas", "Horas operativas"), ("horas_programadas", "Horas programadas")),
     "horas_operativas / horas_programadas * 100", _ratio(720, 720), [99.6, 99.2, 98.1, 99.4, 99.7, 99.5]),
    ("SIS-03", "Tiempo promedio de resolución de tickets", "Reducir el tiempo de respuesta a incidencias.",
     "Sistemas", "días", "mensual", "menor", 2, 4,
     V(("dias_totales", "Días acumulados de resolución"), ("tickets", "Tickets cerrados")),
     "dias_totales / tickets", _dias(60, 120), [1.8, 2.4, 2.1, 1.6, 3.2, 2.2]),
    ("PRO-01", "Cumplimiento del plan de producción", "Cumplir las toneladas planificadas de producto terminado.",
     "Producción", "%", "mensual", "mayor", 95, 85,
     V(("tm_producidas", "TM producidas"), ("tm_planificadas", "TM planificadas")),
     "tm_producidas / tm_planificadas * 100", _ratio(3800, 4400), [97, 93, 88, 96, 82, 90]),
    ("PRO-02", "Rendimiento de molienda", "Maximizar el producto obtenido por tonelada de mineral alimentado.",
     "Producción", "%", "mensual", "mayor", 92, 88,
     V(("tm_producto", "TM de producto"), ("tm_alimentadas", "TM alimentadas")),
     "tm_producto / tm_alimentadas * 100", _ratio(4200, 4800), [93, 92.5, 91, 93.5, 89, 91.5]),
    ("PRO-03", "Merma de proceso", "Reducir las pérdidas de material durante el proceso.",
     "Producción", "%", "mensual", "menor", 3, 5,
     V(("tm_merma", "TM de merma"), ("tm_procesadas", "TM procesadas")),
     "tm_merma / tm_procesadas * 100", _ratio(4200, 4800), [2.4, 2.9, 3.6, 2.7, 5.4, 3.1]),
    ("MAN-01", "Cumplimiento del plan de mantenimiento preventivo", "Ejecutar las órdenes preventivas programadas.",
     "Mantenimiento", "%", "mensual", "mayor", 90, 80,
     V(("ot_ejecutadas", "OT preventivas ejecutadas"), ("ot_programadas", "OT preventivas programadas")),
     "ot_ejecutadas / ot_programadas * 100", _ratio(70, 110), [88, 91, 93, 86, 92, 94]),
    ("MAN-02", "Disponibilidad de equipos críticos", "Asegurar la disponibilidad de molinos, secadores y ensacadoras.",
     "Mantenimiento", "%", "mensual", "mayor", 92, 85,
     V(("horas_calendario", "Horas calendario (equipos críticos)"), ("horas_parada", "Horas de parada")),
     "(horas_calendario - horas_parada) / horas_calendario * 100", _horas, [94, 93, 90, 91, 87, 92]),
    ("MAN-03", "Tiempo medio de ejecución de órdenes de trabajo", "Reducir el tiempo entre la apertura y el cierre de OT.",
     "Mantenimiento", "días", "mensual", "menor", 3, 5,
     V(("dias_totales", "Días acumulados de ejecución"), ("ot_cerradas", "OT cerradas")),
     "dias_totales / ot_cerradas", _dias(80, 140), [3.4, 2.8, 2.6, 3.9, 5.5, 3.2]),
    ("CAL-01", "Lotes conformes con especificación", "Entregar producto dentro de especificación técnica.",
     "Calidad", "%", "mensual", "mayor", 98, 95,
     V(("lotes_conformes", "Lotes conformes"), ("lotes_analizados", "Lotes analizados")),
     "lotes_conformes / lotes_analizados * 100", _ratio(180, 260), [98.6, 98.1, 97, 99, 96.5, 98.4]),
    ("CAL-02", "Reclamos de clientes", "Disminuir los reclamos formales recibidos.",
     "Calidad", "cantidad", "mensual", "menor", 2, 4,
     V(("reclamos", "Reclamos recibidos"),), "reclamos", _directo, [1, 2, 3, 1, 5, 2]),
    ("LOG-01", "Despachos a tiempo (OTIF)", "Cumplir la fecha comprometida de entrega.",
     "Logística", "%", "mensual", "mayor", 95, 88,
     V(("despachos_a_tiempo", "Despachos a tiempo"), ("despachos_totales", "Despachos totales")),
     "despachos_a_tiempo / despachos_totales * 100", _ratio(300, 380), [96, 92, 94, 89, 87, 95]),
    ("ALM-01", "Obsolescencia de inventario", "Mantener bajo el valor de repuestos y materiales sin rotación.",
     "Almacén", "%", "mensual", "menor", 2, 4,
     V(("valor_obsoleto", "Valor obsoleto (USD)"), ("valor_total", "Valor total del inventario (USD)")),
     "valor_obsoleto / valor_total * 100", _ratio(800000, 900000), [1.6, 1.9, 2.4, 2.1, 3.8, 1.8]),
    ("COM-01", "Ahorro generado en compras", "Lograr ahorros frente al presupuesto aprobado.",
     "Compras", "USD", "mensual", "mayor", 5000, 2000,
     V(("presupuesto", "Presupuesto aprobado (USD)"), ("ejecutado", "Monto ejecutado (USD)")),
     "presupuesto - ejecutado", _ahorro, [6200, 5400, 3100, 7800, 1500, 5900]),
    ("SHA-01", "Accidentes con tiempo perdido", "Cero accidentes incapacitantes.",
     "Seguridad y Ambiente", "cantidad", "mensual", "menor", 0, 1,
     V(("accidentes", "Accidentes con tiempo perdido"),), "accidentes", _directo, [0, 0, 1, 0, 2, 0]),
    ("SHA-02", "Cumplimiento del plan de capacitación en SSA", "Ejecutar las capacitaciones de seguridad programadas.",
     "Seguridad y Ambiente", "%", "trimestral", "mayor", 90, 80,
     V(("cap_ejecutadas", "Capacitaciones ejecutadas"), ("cap_programadas", "Capacitaciones programadas")),
     "cap_ejecutadas / cap_programadas * 100", _ratio(20, 30), [88, 93, 95]),
    ("RRH-01", "Rotación de personal", "Retener el talento y reducir la rotación.",
     "Recursos Humanos", "%", "semestral", "menor", 4, 7,
     V(("bajas", "Bajas del período"), ("plantilla", "Plantilla promedio")),
     "bajas / plantilla * 100", _ratio(180, 200), [5.2, 3.6]),
]

# Estado de la carga más reciente de cada indicador (el resto queda aprobado)
ULTIMO_ESTADO = {"SIS-01": "enviado", "PRO-03": "enviado", "MAN-03": "enviado",
                 "CAL-02": "enviado", "SHA-01": "enviado", "PRO-01": "observado",
                 "LOG-01": None, "ALM-01": None, "COM-01": None}

TEXTOS = {
    "Sistemas": ("Aumento de solicitudes por la migración del servidor de archivos y dos caídas del enlace principal durante la semana de cierre.",
                 "Reforzar el turno de soporte en cierres, habilitar enlace de respaldo y publicar guía de autoservicio. Responsable: Jefe de Sistemas. Fecha: próximo cierre."),
    "Producción": ("Parada no programada del molino 2 por falla de rodamiento y baja alimentación de mineral por lluvias en la cantera.",
                   "Acopio de mineral con 5 días de reserva, reemplazo programado del rodamiento y revisión del plan semanal con Mantenimiento. Verificar eficacia el próximo mes."),
    "Mantenimiento": ("Atrasos por falta de repuestos críticos y reasignación de cuadrillas a reparaciones correctivas urgentes.",
                      "Definir stock mínimo de repuestos críticos con Almacén y reservar horas-hombre fijas para preventivos. Seguimiento semanal."),
    "Calidad": ("Variación granulométrica en un lote por cambio de malla y desviación puntual del proceso de secado.",
                "Verificación de mallas al inicio de turno, ajuste del perfil de secado y capacitación del operador de laboratorio."),
    "Logística": ("Retrasos por disponibilidad de transporte y reprogramación de despachos por el cierre de vía.",
                  "Contratar transportista alterno, confirmar citas con el cliente 48 h antes y comunicar anticipadamente las reprogramaciones."),
    "Almacén": ("Se registraron materiales sin movimiento mayor a 24 meses tras actualización de maestro de inventario.",
                "Depuración trimestral, propuesta de baja o reubicación de excedentes y bloqueo de nuevas compras duplicadas."),
    "Compras": ("Menor cantidad de procesos competitivos por urgencias de mantenimiento que obligaron a compras directas.",
                "Acuerdos marco con proveedores clave y calendario de compras anticipado con las áreas usuarias."),
    "Seguridad y Ambiente": ("Incidente por incumplimiento de procedimiento de bloqueo y etiquetado durante una intervención.",
                             "Reentrenamiento en LOTO, auditoría de permisos de trabajo y divulgación de la lección aprendida."),
    "Recursos Humanos": ("Salidas voluntarias en el área operativa asociadas a ofertas externas.",
                         "Revisión de escala salarial, plan de incentivos por asistencia y entrevistas de salida sistemáticas."),
}


def sembrar(db: Session, hoy: date | None = None) -> None:
    if db.scalar(select(func.count(Usuario.id))):
        return
    hoy = hoy or date.today()
    rnd = random.Random(2026)

    areas = {n: Area(nombre=n) for n in AREAS}
    db.add_all(areas.values())
    db.flush()
    usuarios = {}
    for username, nombre, rol, area in USUARIOS:
        u = Usuario(username=username, nombre=nombre, rol=rol,
                    area_id=areas[area].id if area else None,
                    password_hash=hash_password(CLAVE_DEMO))
        db.add(u)
        usuarios[username] = u
    db.flush()
    admin, gerente = usuarios["admin"], usuarios["gerente"]
    jefe_de = {u.area_id: u for u in usuarios.values() if u.rol == "jefe"}

    eventos = []  # (fecha, usuario, accion, entidad, entidad_id, detalle, indicador)
    inicio = datetime.combine(hoy - timedelta(days=240), time(8, 30))

    for (cod, nom, obj, area, uni, frec, sent, meta, lim, vars_, formula, gen, serie) in INDICADORES:
        ind = Indicador(codigo=cod, nombre=nom, objetivo=obj, area_id=areas[area].id,
                        unidad=uni, frecuencia=frec, sentido=sent, formula=formula,
                        variables=vars_, meta=meta, limite=lim, creado_en=inicio)
        db.add(ind)
        db.flush()
        eventos.append((inicio, admin, "INDICADOR_CREADO", "indicador", ind.id,
                        {"codigo": cod, "nombre": nom, "formula": formula, "meta": meta, "limite": lim}, ind))

        n = len(serie)
        periodos = list(reversed(calc.periodos_cerrados(frec, hoy, n)))  # antiguo → reciente
        claves = [v["clave"] for v in vars_]
        jefe = jefe_de[ind.area_id]
        for i, (per, objetivo_val) in enumerate(zip(periodos, serie)):
            es_ultimo = i == n - 1
            estado = "aprobado"
            if es_ultimo and cod in ULTIMO_ESTADO:
                estado = ULTIMO_ESTADO[cod]
                if estado is None:
                    continue  # carga pendiente
            valores = gen(objetivo_val, rnd, claves)
            res = calc.evaluar(formula, valores)
            sem = calc.semaforo(res, meta, lim, sent)
            y, idx = int(per[:4]), int(per[5:]) if frec == "mensual" else int(per[-1])
            fin = {"mensual": date(y + (idx == 12), idx % 12 + 1, 1),
                   "trimestral": date(y + (idx == 4), (idx * 3) % 12 + 1, 1),
                   "semestral": date(y + (idx == 2), 1 if idx == 2 else 7, 1)}[frec]
            cargado = datetime.combine(fin + timedelta(days=rnd.randint(1, 4)),
                                       time(rnd.randint(8, 16), rnd.randint(0, 59)))
            cargado = min(cargado, ahora() - timedelta(days=1))
            analisis, plan = TEXTOS[area] if sem != "verde" else ("", "")
            m = Medicion(indicador_id=ind.id, periodo=per, valores=valores, resultado=res,
                         semaforo=sem, meta=meta, limite=lim, sentido=sent, estado=estado,
                         analisis=analisis, plan_mejora=plan, version=1,
                         cargado_por_id=jefe.id, cargado_en=cargado)
            if estado in ("aprobado", "observado"):
                m.revisado_por_id = gerente.id
                m.revisado_en = min(cargado + timedelta(days=1, hours=2), ahora())
                if estado == "observado":
                    m.nota_revision = "Detalle la causa raíz de la parada y agregue fecha compromiso y responsable en el plan de mejora."
            db.add(m)
            db.flush()
            eventos.append((cargado, jefe, "CARGA", "medicion", m.id,
                            {"periodo": per, "valores": valores, "resultado": res, "semaforo": sem,
                             "analisis": analisis, "plan_mejora": plan, "version": 1}, ind))
            if estado in ("aprobado", "observado"):
                accion = "APROBACION" if estado == "aprobado" else "OBSERVACION"
                eventos.append((m.revisado_en, gerente, accion, "medicion", m.id,
                                {"periodo": per, "nota": m.nota_revision}, ind))
            if sem == "rojo" and estado == "aprobado":
                nota = NotaAuditoria(medicion_id=m.id, usuario_id=gerente.id, fecha=m.revisado_en,
                                     texto="Se verificará la eficacia del plan de mejora en la próxima revisión por la dirección.")
                db.add(nota)
                db.flush()
                eventos.append((m.revisado_en, gerente, "NOTA_AUDITORIA", "medicion", m.id,
                                {"periodo": per, "texto": nota.texto}, ind))

    for fecha, usr, accion, entidad, eid, det, ind in sorted(eventos, key=lambda e: e[0]):
        audit.registrar(db, usr, accion, entidad, eid, det, indicador=ind, fecha=fecha)
    db.commit()
