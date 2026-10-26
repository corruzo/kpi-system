"""Calendario de medición: períodos de cada frecuencia agrupados en ejercicios fiscales.

El ejercicio fiscal puede comenzar en cualquier mes (1 = enero, 10 = octubre) y se identifica por el año en
que TERMINA: con inicio en octubre, el ejercicio 2026 va de octubre de 2025 a septiembre de 2026.

Códigos de período — mensual y eventual «2026-03»; anual «2026»; bimestral «2026-B1», trimestral «2026-Q1»,
cuatrimestral «2026-C1» y semestral «2026-S1» (el número cuenta desde el inicio del ejercicio).
El mes de inicio se fija con configurar() a partir de los parámetros del sistema.
"""
import re
from datetime import date, timedelta

MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
         "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
MES3 = ["Ene.", "Feb.", "Mar.", "Abr.", "May.", "Jun.", "Jul.", "Ago.", "Sep.", "Oct.", "Nov.", "Dic."]

FRECUENCIAS = ["mensual", "bimestral", "trimestral", "cuatrimestral", "semestral", "anual", "eventual"]
MESES_POR_PERIODO = {"mensual": 1, "bimestral": 2, "trimestral": 3, "cuatrimestral": 4, "semestral": 6,
                     "anual": 12, "eventual": 1}
PREFIJO = {"bimestral": "B", "trimestral": "Q", "cuatrimestral": "C", "semestral": "S"}
_NOMBRE_CORTO = {"B": "Bim.", "Q": "T", "C": "Cuat.", "S": "S"}
# Períodos ya cerrados que se consideran «por cargar» (eventual: ninguno, se carga cuando ocurre)
VENTANA_PENDIENTE = {"mensual": 3, "bimestral": 2, "trimestral": 2, "cuatrimestral": 1, "semestral": 1,
                     "anual": 1, "eventual": 0}
# Cuántos períodos hacia atrás se ofrecen al cargar
HISTORIAL = {"mensual": 24, "bimestral": 12, "trimestral": 12, "cuatrimestral": 9, "semestral": 8,
             "anual": 5, "eventual": 24}

_inicio = 1  # mes de inicio del ejercicio fiscal


# ------------------------------------------------------------------ configuración
def configurar(mes_inicio: int) -> None:
    """Fija el mes en que comienza el ejercicio fiscal (1 a 12)."""
    global _inicio
    _inicio = min(12, max(1, int(mes_inicio)))


def inicio_mes() -> int:
    return _inicio


# ------------------------------------------------------------------ fechas y ejercicios
def suma_meses(d: date, n: int) -> date:
    """Primer día del mes que resulta de sumar n meses a la fecha."""
    y, m = divmod(d.month - 1 + n, 12)
    return date(d.year + y, m + 1, 1)


def ejercicio_de_fecha(d: date) -> int:
    """Año en que TERMINA el ejercicio fiscal que contiene a la fecha."""
    return d.year if _inicio == 1 else (d.year + 1 if d.month >= _inicio else d.year)


def inicio_ejercicio(y: int) -> date:
    return date(y if _inicio == 1 else y - 1, _inicio, 1)


def limites(y: int) -> tuple[date, date]:
    """(primer día, último día) del ejercicio fiscal y."""
    ini = inicio_ejercicio(y)
    return ini, suma_meses(ini, 12) - timedelta(days=1)


def etiqueta_ejercicio(y: int) -> str:
    return str(y) if _inicio == 1 else f"{y - 1}-{y}"


def meses_del_ejercicio() -> list[str]:
    """Nombres cortos de los 12 meses del ejercicio, en orden fiscal."""
    return [MES3[(_inicio - 1 + k) % 12] for k in range(12)]


# ------------------------------------------------------------------ períodos
def codigo(f: str, d: date) -> str:
    """Código del período de frecuencia f que contiene la fecha d."""
    if f in ("mensual", "eventual"):
        return f"{d.year}-{d.month:02d}"
    y = ejercicio_de_fecha(d)
    if f == "anual":
        return str(y)
    n = ((d.month - _inicio) % 12) // MESES_POR_PERIODO[f] + 1
    return f"{y}-{PREFIJO[f]}{n}"


def _patron(f: str) -> str:
    if f in ("mensual", "eventual"):
        return r"^(\d{4})-(0[1-9]|1[0-2])$"
    if f == "anual":
        return r"^(\d{4})$"
    return rf"^(\d{{4}})-{PREFIJO[f]}([1-9]\d?)$"


def rango(f: str, p: str) -> tuple[date, date] | None:
    """(primer día, último día) del período, o None si el código no es válido para esa frecuencia."""
    if f not in MESES_POR_PERIODO:
        return None
    m = re.match(_patron(f), p or "")
    if not m:
        return None
    k = MESES_POR_PERIODO[f]
    if f in ("mensual", "eventual"):
        ini = date(int(m.group(1)), int(m.group(2)), 1)
    else:
        n = int(m.group(2)) if m.lastindex > 1 else 1
        if n > 12 // k:
            return None
        ini = suma_meses(inicio_ejercicio(int(m.group(1))), (n - 1) * k)
    return ini, suma_meses(ini, k) - timedelta(days=1)


def periodo_valido(f: str, p: str) -> bool:
    return rango(f, p) is not None


def periodo_actual(f: str, hoy: date) -> str:
    return codigo(f, hoy)


def periodos_recientes(f: str, hoy: date, n: int | None = None) -> list[str]:
    """Del período actual hacia atrás."""
    out, p = [], codigo(f, hoy)
    for _ in range(n or HISTORIAL[f]):
        out.append(p)
        p = codigo(f, rango(f, p)[0] - timedelta(days=1))
    return out


def periodos_cerrados(f: str, hoy: date, n: int) -> list[str]:
    """Los n períodos anteriores al actual."""
    return periodos_recientes(f, hoy, n + 1)[1:]


def periodos_del_ejercicio(f: str, y: int) -> list[str]:
    """Todos los períodos del ejercicio, en orden cronológico."""
    ini, k = inicio_ejercicio(y), MESES_POR_PERIODO[f]
    return [codigo(f, suma_meses(ini, i * k)) for i in range(12 // k)]


def periodos_pendientes(f: str, hoy: date, estados: dict[str, str]) -> list[str]:
    """Períodos cerrados sin carga (o devueltos), del más antiguo al más reciente."""
    ventana = periodos_cerrados(f, hoy, VENTANA_PENDIENTE[f]) if VENTANA_PENDIENTE[f] else []
    return [p for p in reversed(ventana) if estados.get(p) in (None, "observado")]


def es_futuro(f: str, p: str, hoy: date) -> bool:
    return rango(f, p)[0] > hoy


def ejercicio_de(f: str, p: str) -> int:
    """Ejercicio fiscal al que pertenece el período."""
    return ejercicio_de_fecha(rango(f, p)[1])


def indice_de_mes(f: str, p: str) -> int:
    """Posición (0-11) del mes de cierre del período dentro del ejercicio: columna del mapa de calor."""
    return (rango(f, p)[1].month - _inicio) % 12


# ------------------------------------------------------------------ etiquetas
def etiqueta(f: str, p: str) -> str:
    ini, fin = rango(f, p)
    if f in ("mensual", "eventual"):
        return f"{MESES[ini.month - 1]} {ini.year}"
    ej = etiqueta_ejercicio(ejercicio_de(f, p))
    if f == "anual":
        return f"Ejercicio {ej}"
    pref = PREFIJO[f]
    return f"{_NOMBRE_CORTO[pref]}{p.rsplit(pref, 1)[1]} {ej} ({MES3[ini.month - 1][:3]}–{MES3[fin.month - 1][:3]})"


def etiqueta_corta(f: str, p: str) -> str:
    """Encabezado breve de columna: mes de cierre del período (como en las fichas en papel)."""
    return MES3[rango(f, p)[1].month - 1] if f != "anual" else etiqueta_ejercicio(ejercicio_de(f, p))
