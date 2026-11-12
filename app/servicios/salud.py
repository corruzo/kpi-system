"""Salud del sistema para el Desarrollador: infraestructura, código, actividad reciente y diagnóstico automático.

Todo se calcula con consultas ligeras y acotadas (plan gratuito): nada recorre tablas enteras salvo columnas sueltas de
los indicadores activos. El diagnóstico devuelve alertas con su causa y su recomendación, de la más grave a la menos grave.
"""
import json
import os
import platform
import statistics
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime, timedelta
from urllib.parse import urlparse

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from .. import config
from ..database import BASE_DIR, DATABASE_URL, ES_POSTGRES, ES_SQLITE
from ..dominio import calendario, formulas
from ..models import (
    Bitacora,
    Ejercicio,
    Indicador,
    IndicadorCargador,
    IntentoFallido,
    Medicion,
    Meta,
    Rol,
    Unidad,
    Usuario,
    UsuarioUnidad,
    ahora,
)
from . import auditoria, migraciones, personas

LIMITE_BD_MB = float(os.getenv("SIGT_DB_LIMITE_MB", "500"))   # plan gratuito de Supabase
LIMITE_CONEXIONES = int(os.getenv("SIGT_DB_CONEXIONES", "60"))
DIAS_CARGA_ATASCADA = 10
DIAS_MINIMOS_PARA_ESTIMAR = 14   # menos historial que esto no permite proyectar el crecimiento
GRAVEDAD = {"critico": 0, "aviso": 1, "info": 2}


# ------------------------------------------------------------------------------------------ infraestructura
def _tamano_bd(db: Session) -> dict:
    if ES_POSTGRES:
        total = db.scalar(text("select pg_database_size(current_database())")) or 0
        filas = db.execute(text(
            "select relname, pg_total_relation_size(c.oid) from pg_class c join pg_namespace n on n.oid = c.relnamespace "
            "where n.nspname = 'public' and c.relkind = 'r' order by 2 desc limit 6")).all()
        datos = db.scalar(text(
            "select coalesce(sum(pg_total_relation_size(c.oid)), 0) from pg_class c join pg_namespace n on n.oid = c.relnamespace "
            "where n.nspname = 'public' and c.relkind = 'r'")) or 0   # solo lo que genera la aplicación (sin el catálogo interno de PostgreSQL)
        conexiones = db.scalar(text("select count(*) from pg_stat_activity where datname = current_database()")) or 0
        return {"bytes": int(total), "datos": int(datos), "tablas": [{"nombre": n, "bytes": int(b)} for n, b in filas], "conexiones": int(conexiones)}
    ruta = DATABASE_URL.replace("sqlite:///", "")
    total = os.path.getsize(ruta) if os.path.exists(ruta) else 0
    return {"bytes": total, "datos": total, "tablas": [], "conexiones": None}


def base_de_datos(db: Session) -> dict:
    t0 = time.perf_counter()
    db.execute(text("select 1"))
    latencia = round((time.perf_counter() - t0) * 1000)
    tam = _tamano_bd(db)
    usado = tam["bytes"] / 1_048_576
    host = urlparse(DATABASE_URL).hostname if not ES_SQLITE else "archivo local (SQLite)"
    primero = db.scalar(select(func.min(Bitacora.fecha)))
    dias = (ahora() - primero).days if primero else 0
    # Ritmo de crecimiento = datos PROPIOS (no el tamaño total, que incluye ~10 MB fijos del motor) entre los días de historial,
    # y solo con historial suficiente: con pocos días cualquier cifra sería engañosa.
    crecimiento = round(tam["datos"] / 1_048_576 / dias, 3) if dias >= DIAS_MINIMOS_PARA_ESTIMAR else None
    restante = round((LIMITE_BD_MB - usado) / crecimiento) if crecimiento else None
    try:
        actual, cabeza = migraciones.revision_actual(), migraciones.revision_cabeza()
    except Exception:
        actual = cabeza = None
    return {"motor": "PostgreSQL (Supabase)" if ES_POSTGRES else "SQLite (desarrollo)", "host": host, "latencia_ms": latencia,
            "usado_mb": round(usado, 2), "limite_mb": LIMITE_BD_MB, "porcentaje": round(usado / LIMITE_BD_MB * 100, 1),
            "tablas": [{**t, "mb": round(t["bytes"] / 1_048_576, 2)} for t in tam["tablas"]],
            "conexiones": tam["conexiones"], "limite_conexiones": LIMITE_CONEXIONES,
            "crecimiento_mb_dia": crecimiento, "historial_dias": dias, "datos_mb": round(tam["datos"] / 1_048_576, 2), "dias_restantes": restante,
            "migracion": {"actual": actual, "esperada": cabeza, "al_dia": actual == cabeza}}


def _git(*args) -> str | None:
    try:
        return subprocess.run(["git", *args], cwd=BASE_DIR, capture_output=True, text=True, timeout=2).stdout.strip() or None
    except Exception:
        return None


def despliegue() -> dict:
    sha = os.getenv("VERCEL_GIT_COMMIT_SHA") or _git("rev-parse", "HEAD")
    return {"plataforma": "Vercel" if os.getenv("VERCEL") else "Local", "entorno": os.getenv("VERCEL_ENV") or ("production" if config.PRODUCCION else "development"),
            "region": os.getenv("VERCEL_REGION"), "commit": sha[:7] if sha else None,
            "rama": os.getenv("VERCEL_GIT_COMMIT_REF") or _git("rev-parse", "--abbrev-ref", "HEAD"),
            "mensaje": (os.getenv("VERCEL_GIT_COMMIT_MESSAGE") or _git("log", "-1", "--pretty=%s") or "")[:120] or None,
            "python": platform.python_version(), "produccion": config.PRODUCCION}


# ------------------------------------------------------------------------------------------ estado externo (con caché)
_FUENTES = {"supabase": "https://status.supabase.com/api/v2/status.json", "vercel": "https://www.vercel-status.com/api/v2/status.json"}
_externo: dict = {"hasta": 0.0, "datos": None}


def _consultar(nombre: str, url: str, salida: dict) -> None:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "spe-tpv-salud"}), timeout=2.5) as r:
            s = json.loads(r.read())["status"]
        salida[nombre] = {"indicador": s.get("indicator"), "descripcion": s.get("description")}
    except Exception:
        salida[nombre] = {"indicador": None, "descripcion": "No se pudo consultar"}


def estado_externo() -> dict:
    """Estado público de Supabase y Vercel (sus páginas de estado), en paralelo y recordado 5 minutos."""
    if time.monotonic() < _externo["hasta"] and _externo["datos"]:
        return _externo["datos"]
    salida: dict = {}
    hilos = [threading.Thread(target=_consultar, args=(n, u, salida)) for n, u in _FUENTES.items()]
    [h.start() for h in hilos]
    [h.join(4) for h in hilos]
    _externo.update(hasta=time.monotonic() + (300 if all(v["indicador"] for v in salida.values()) else 30), datos=salida)
    return salida


# ------------------------------------------------------------------------------------------ actividad reciente
def bitacora_reciente(db: Session, n: int = 8) -> list[dict]:
    q = select(Bitacora).order_by(Bitacora.id.desc()).limit(n)
    return [{"id": b.id, "fecha": b.fecha.isoformat(), "usuario": b.usuario_nombre, "accion": b.accion, "entidad": b.entidad} for b in db.scalars(q)]


def cadena_reciente(db: Session, n: int = 400) -> dict:
    """Verifica solo los últimos `n` eslabones de la cadena (la verificación completa vive en la pantalla Bitácora)."""
    filas = list(reversed(list(db.scalars(select(Bitacora).order_by(Bitacora.id.desc()).limit(n)))))
    for i, b in enumerate(filas):
        previo = filas[i - 1].hash if i else b.prev_hash
        if b.prev_hash != previo or b.hash != auditoria._hash(b.prev_hash, auditoria._contenido(b)):
            return {"ok": False, "revisados": len(filas), "primer_error_id": b.id}
    return {"ok": True, "revisados": len(filas), "primer_error_id": None}


def accesos_recientes(db: Session, n: int = 5) -> list[dict]:
    ultimos = personas.ultimos_ingresos(db)
    top = sorted(ultimos.items(), key=lambda x: x[1], reverse=True)[:n]
    por_id = {u.id: u for u in db.scalars(select(Usuario).where(Usuario.id.in_([i for i, _ in top])))} if top else {}
    return [{"id": i, "usuario": por_id[i].username, "nombre": por_id[i].nombre, "rol": por_id[i].rol.nombre if por_id[i].rol else "Sin rol",
             "activo": por_id[i].activo, "ultimo_ingreso": f.isoformat()} for i, f in top if i in por_id]


# ------------------------------------------------------------------------------------------ diagnóstico
def _alerta(nivel, area, titulo, detalle, recomendacion, ir=None) -> dict:
    return {"nivel": nivel, "area": area, "titulo": titulo, "detalle": detalle, "recomendacion": recomendacion, "ir": ir}


def _lista(codigos: list[str], tope: int = 6) -> str:
    return ", ".join(codigos[:tope]) + (f" y {len(codigos) - tope} más" if len(codigos) > tope else "")


def _umbrales(activos: list[Indicador]) -> list[str]:
    """Indicadores cuya zona verde/roja no tiene sentido: el rojo queda del lado bueno del verde."""
    malos = []
    for i in activos:
        mal = i.limite > i.nivel_optimo if i.sentido == "mayor" else i.limite < i.nivel_optimo
        if mal:
            malos.append(i.codigo)
    return malos


def _formulas(activos: list[Indicador]) -> tuple[list[str], list[str]]:
    """(rotas, sin protección contra división entre cero): evalúa cada fórmula con 1 en todas las variables y luego con 0."""
    rotas, sin_proteccion = [], []
    for i in activos:
        claves = [v["clave"] for v in (i.variables or []) if v.get("clave")]
        const = {c["clave"]: c.get("valor", 0) for c in (i.constantes or []) if c.get("clave")}
        try:
            formulas.evaluar(i.formula, dict.fromkeys(claves, 1.0), const, i.decimales)
        except Exception:
            rotas.append(i.codigo)
            continue
        try:
            formulas.evaluar(i.formula, dict.fromkeys(claves, 0.0), const, i.decimales)
        except formulas.FormulaError as e:
            if "cero" in str(e).lower():
                sin_proteccion.append(i.codigo)
        except Exception:
            pass
    return rotas, sin_proteccion


def _atipicos(db: Session, activos: list[Indicador]) -> list[str]:
    """Última medición de cada indicador que se aleja más de 3 desviaciones de su propio historial (mínimo 6 datos)."""
    por_ind: dict[int, list[tuple[str, float]]] = {}
    ids = [i.id for i in activos]
    if not ids:
        return []
    for iid, periodo, res in db.execute(select(Medicion.indicador_id, Medicion.periodo, Medicion.resultado)
                                        .where(Medicion.indicador_id.in_(ids), Medicion.estado != "observado").order_by(Medicion.periodo)):
        por_ind.setdefault(iid, []).append((periodo, res))
    codigo = {i.id: i.codigo for i in activos}
    raros = []
    for iid, serie in por_ind.items():
        if len(serie) < 6:
            continue
        previos = [r for _, r in serie[:-1]]
        sd = statistics.pstdev(previos)
        if sd > 0 and abs(serie[-1][1] - statistics.fmean(previos)) > 3 * sd:
            raros.append(f"{codigo[iid]} ({serie[-1][0]})")
    return raros


def diagnostico(db: Session, bd: dict | None = None, cadena: dict | None = None) -> list[dict]:
    a: list[dict] = []
    bd = bd or base_de_datos(db)
    if not bd["migracion"]["al_dia"]:
        a.append(_alerta("critico", "Base de datos", "El esquema no está al día", f"La base está en «{bd['migracion']['actual']}» y el código espera «{bd['migracion']['esperada']}».",
                         "Ejecute «alembic upgrade head» (o «make migraciones») antes de seguir usando el sistema."))
    if bd["porcentaje"] >= 90:
        a.append(_alerta("critico", "Base de datos", f"Espacio casi agotado ({bd['porcentaje']} %)", f"Usa {bd['usado_mb']} de {bd['limite_mb']:.0f} MB.",
                         "Exporte un respaldo y evalúe pasar a un plan de pago o archivar datos antiguos."))
    elif bd["porcentaje"] >= 70:
        a.append(_alerta("aviso", "Base de datos", f"Espacio en {bd['porcentaje']} %", f"Usa {bd['usado_mb']} de {bd['limite_mb']:.0f} MB.",
                         "Planifique el crecimiento: revise las tablas más grandes en este panel."))
    if bd["dias_restantes"] is not None and 0 < bd["dias_restantes"] < 120 and bd["porcentaje"] < 90:
        a.append(_alerta("aviso", "Base de datos", f"A este ritmo se llenaría en ~{bd['dias_restantes']} días", f"Los datos propios crecen unos {bd['crecimiento_mb_dia']} MB por día en promedio ({bd['historial_dias']} días de historial).",
                         "Verifique que no haya cargas masivas o importaciones repetidas."))
    if bd["conexiones"] is not None and bd["conexiones"] > bd["limite_conexiones"] * 0.7:
        a.append(_alerta("aviso", "Base de datos", f"Muchas conexiones abiertas ({bd['conexiones']})", f"El límite aproximado del plan es {bd['limite_conexiones']}.",
                         "Use la cadena del pooler de Supabase (puerto 6543) en SIGT_DATABASE_URL."))
    if bd["latencia_ms"] > 800:
        a.append(_alerta("aviso", "Base de datos", f"Respuesta lenta ({bd['latencia_ms']} ms)", "Una consulta mínima tardó demasiado.", "Revise el estado de Supabase y la región de su proyecto frente a la de Vercel."))

    cadena = cadena or cadena_reciente(db)
    if not cadena["ok"]:
        a.append(_alerta("critico", "Seguridad", "La bitácora fue alterada", f"El registro {cadena['primer_error_id']} no coincide con su huella.",
                         "Es una posible manipulación de datos: restaure un respaldo y revise los accesos a la base.", "bitacora"))
    if db.scalar(select(func.count()).select_from(IntentoFallido).where(IntentoFallido.fecha > ahora() - timedelta(hours=24))) >= 15:
        a.append(_alerta("aviso", "Seguridad", "Muchos intentos fallidos de ingreso en 24 h", "Puede ser un olvido de clave o un intento de acceso.",
                         "Revise la bitácora; si no reconoce el patrón, cambie las claves y cierre sesiones.", "bitacora"))
    if (db.scalar(select(func.count()).select_from(Usuario).join(Rol).where(Rol.clave == "desarrollador", Usuario.activo))) == 1:
        a.append(_alerta("info", "Seguridad", "Solo hay un Desarrollador activo", "Si pierde esa cuenta nadie podrá administrar lo técnico.",
                         "Designe un segundo Desarrollador (Personas → Soporte).", "personas"))
    ultimo_resp = db.scalar(select(func.max(Bitacora.fecha)).where(Bitacora.accion == "RESPALDO_CREADO"))
    if not ultimo_resp or ultimo_resp < ahora() - timedelta(days=30):
        a.append(_alerta("aviso", "Operación", "Sin respaldo en los últimos 30 días" if ultimo_resp else "Nunca se ha exportado un respaldo",
                         "Supabase gratuito no conserva copias automáticas.", "Exporte un respaldo cifrado en Configuración → Avanzado.", "config"))

    activos = list(db.scalars(select(Indicador).where(Indicador.activo)))
    if (m := _umbrales(activos)):
        a.append(_alerta("aviso", "Algoritmo", f"{len(m)} indicador(es) con semáforo incoherente", f"El límite crítico queda del lado bueno del nivel óptimo en: {_lista(m)}.",
                         "Corrija el nivel óptimo y el límite crítico en la ficha: hoy el semáforo puede dar resultados engañosos.", "fichas"))
    rotas, sin_prot = _formulas(activos)
    if rotas:
        a.append(_alerta("critico", "Algoritmo", f"{len(rotas)} fórmula(s) no se pueden calcular", f"Fallan con valores de prueba: {_lista(rotas)}.",
                         "Edite la ficha y use el probador de fórmulas; nadie podrá cargar esos indicadores.", "fichas"))
    if sin_prot:
        a.append(_alerta("aviso", "Algoritmo", f"{len(sin_prot)} fórmula(s) sin protección contra división entre cero", f"Una carga con denominador 0 será rechazada: {_lista(sin_prot)}.",
                         "Use si(b > 0, a / b, 0) o div(a, b, 0) en la fórmula.", "fichas"))
    if (r := _atipicos(db, activos)):
        a.append(_alerta("aviso", "Algoritmo", f"{len(r)} dato(s) atípico(s) en la última medición", f"Se alejan más de 3 desviaciones de su historial: {_lista(r)}.",
                         "Pida al cargador que confirme el dato (posible error de digitación o de unidad).", "historial"))

    cargables = {i for (i,) in db.execute(select(IndicadorCargador.indicador_id).join(Usuario).where(Usuario.activo))}
    sin_cargador = [i.codigo for i in activos if i.id not in cargables]
    if sin_cargador:
        a.append(_alerta("aviso", "Datos", f"{len(sin_cargador)} indicador(es) sin nadie que los cargue", _lista(sin_cargador),
                         "Asigne un cargador activo: mientras tanto no recibirán datos ni recordatorios.", "personas"))
    sin_resp = [i.codigo for i in activos if i.responsable_id is None]
    if sin_resp:
        a.append(_alerta("aviso", "Datos", f"{len(sin_resp)} indicador(es) sin responsable", _lista(sin_resp), "Asigne un responsable (el dueño del indicador).", "personas"))
    anio = calendario.ejercicio_de_fecha(calendario.hoy())
    if db.get(Ejercicio, anio) and activos:
        con_meta = {i for (i,) in db.execute(select(Meta.indicador_id).where(Meta.ejercicio == anio).distinct())}
        sin_meta = [i.codigo for i in activos if i.id not in con_meta]
        if sin_meta:
            a.append(_alerta("aviso", "Datos", f"{len(sin_meta)} indicador(es) sin meta en el ejercicio vigente", _lista(sin_meta),
                             "Fije la meta en Período y metas; sin ella no se puede medir el cumplimiento.", "meta"))
    limite = ahora() - timedelta(days=DIAS_CARGA_ATASCADA)
    atascadas = db.scalar(select(func.count()).select_from(Medicion).where(Medicion.estado == "enviado", Medicion.cargado_en < limite)) or 0
    if atascadas:
        a.append(_alerta("aviso", "Operación", f"{atascadas} carga(s) esperan aprobación hace más de {DIAS_CARGA_ATASCADA} días", "Los superiores no las han revisado.",
                         "Use «Pendientes de cargar»/«Por aprobar» en Seguimiento y recuerde a los aprobadores.", "bandeja"))
    sin_rol = db.scalar(select(func.count()).select_from(Usuario).where(Usuario.activo, Usuario.rol_id.is_(None))) or 0
    if sin_rol:
        a.append(_alerta("info", "Datos", f"{sin_rol} cuenta(s) esperan asignación de rol", "Pueden ingresar pero no ven nada.", "Asígneles rol y posición.", "personas"))
    vacias = db.scalar(select(func.count()).select_from(Unidad).where(
        Unidad.nivel == "jefatura", ~Unidad.id.in_(select(Indicador.nodo_id)), ~Unidad.id.in_(select(UsuarioUnidad.unidad_id)))) or 0
    if vacias:
        a.append(_alerta("info", "Datos", f"{vacias} jefatura(s) sin personas ni indicadores", "Nodos creados que aún no se usan.", "Asígneles gente e indicadores o elimínelas.", "estructura"))
    a.sort(key=lambda x: GRAVEDAD[x["nivel"]])
    return a


def resumen(db: Session) -> dict:
    """Todo lo que muestra el inicio del Desarrollador, en una sola respuesta."""
    bd, cadena = base_de_datos(db), cadena_reciente(db)
    alertas = diagnostico(db, bd, cadena)
    cuenta = {n: sum(1 for x in alertas if x["nivel"] == n) for n in GRAVEDAD}
    return {"generado": ahora().isoformat(), "estado": "critico" if cuenta["critico"] else "aviso" if cuenta["aviso"] else "ok",
            "conteo": cuenta, "alertas": alertas, "base_de_datos": bd, "despliegue": despliegue(),
            "cadena": cadena, "bitacora": bitacora_reciente(db), "accesos": accesos_recientes(db),
            "sistema": {"python": sys.version.split()[0], "ahora": datetime.now().isoformat(timespec="seconds")}}
