"""Fórmulas seguras, semaforización y manejo de períodos."""
import ast
import math
import re
from datetime import date, timedelta

MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
         "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
MES3 = ["Ene.", "Feb.", "Mar.", "Abr.", "May.", "Jun.", "Jul.", "Ago.", "Sep.", "Oct.", "Nov.", "Dic."]
FRECUENCIAS = ["mensual", "bimestral", "trimestral", "cuatrimestral", "semestral", "anual", "eventual"]
MESES_POR_PERIODO = {"mensual": 1, "bimestral": 2, "trimestral": 3, "cuatrimestral": 4, "semestral": 6,
                     "anual": 12, "eventual": 1}
PREFIJO = {"bimestral": "B", "trimestral": "Q", "cuatrimestral": "C", "semestral": "S"}
NOMBRE_CORTO = {"B": "Bim.", "Q": "T", "C": "Cuat.", "S": "S"}
# Cuántos períodos ya cerrados se consideran "por cargar" (eventual: ninguno, se carga cuando ocurre)
VENTANA_PENDIENTE = {"mensual": 3, "bimestral": 2, "trimestral": 2, "cuatrimestral": 1, "semestral": 1,
                     "anual": 1, "eventual": 0}
HISTORIAL = {"mensual": 24, "bimestral": 12, "trimestral": 12, "cuatrimestral": 9, "semestral": 8,
             "anual": 5, "eventual": 24}
# Mes en que inicia el ejercicio fiscal (1 = enero, 10 = octubre). Lo fija la configuración del sistema.
INICIO = 1


class FormulaError(ValueError):
    pass


# ---------------------------------------------------------------- fórmulas
MAX_NODOS = 300
MAX_LARGO = 1000


def _div(a, b, defecto=0.0):
    return defecto if b == 0 else a / b


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


_AGREG = {"min": min, "max": max, "sum": lambda *a: sum(a), "avg": lambda *a: sum(a) / len(a)}
_FUNCS = {
    **_AGREG, "abs": abs, "round": round, "sqrt": math.sqrt, "floor": math.floor, "ceil": math.ceil,
    "div": _div,                              # div(a, b, defecto): división segura
    "pct": lambda a, b: _div(a, b) * 100,     # pct(a, b): a / b × 100 (0 si b = 0)
    "clamp": _clamp,                          # clamp(x, mínimo, máximo)
}
_LAZY = {"si"}                                # si(condición, valor_si, valor_no): solo evalúa la rama elegida
FUNCIONES = sorted(set(_FUNCS) | _LAZY)
RESERVADAS = set(FUNCIONES) | {"and", "or", "not", "if", "else", "True", "False", "None"}

_BIN = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b, ast.Mult: lambda a, b: a * b,
        ast.Div: lambda a, b: a / b, ast.Mod: lambda a, b: a % b, ast.FloorDiv: lambda a, b: a // b}
_CMP = {ast.Lt: lambda a, b: a < b, ast.LtE: lambda a, b: a <= b, ast.Gt: lambda a, b: a > b,
        ast.GtE: lambda a, b: a >= b, ast.Eq: lambda a, b: a == b, ast.NotEq: lambda a, b: a != b}


def normalizar(formula: str) -> str:
    """Admite símbolos amigables (×, ÷, −, ^, saltos de línea) y los convierte a sintaxis estándar."""
    f = (formula or "").replace("×", "*").replace("÷", "/").replace("−", "-").replace("–", "-")
    f = f.replace("≥", ">=").replace("≤", "<=").replace("≠", "!=").replace("^", "**")
    return re.sub(r"\s+", " ", f).strip()


def _check(n, nombres):
    if isinstance(n, ast.BinOp) and type(n.op) in (*_BIN, ast.Pow):
        _check(n.left, nombres)
        _check(n.right, nombres)
    elif isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd, ast.Not)):
        _check(n.operand, nombres)
    elif isinstance(n, ast.Compare) and all(type(o) in _CMP for o in n.ops):
        _check(n.left, nombres)
        for c in n.comparators:
            _check(c, nombres)
    elif isinstance(n, ast.BoolOp):
        for v in n.values:
            _check(v, nombres)
    elif isinstance(n, ast.IfExp):
        _check(n.test, nombres)
        _check(n.body, nombres)
        _check(n.orelse, nombres)
    elif isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
        pass  # incluye True/False
    elif isinstance(n, ast.Name):
        if n.id not in nombres:
            raise FormulaError(f"«{n.id}» no es una variable, constante ni función conocida.")
    elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and not n.keywords:
        f = n.func.id
        if f not in _FUNCS and f not in _LAZY:
            raise FormulaError(f"La función «{f}» no existe. Disponibles: {', '.join(FUNCIONES)}.")
        if f == "si" and len(n.args) != 3:
            raise FormulaError("si(condición, valor_si_cumple, valor_si_no) requiere exactamente 3 argumentos.")
        if f in ("div",) and len(n.args) not in (2, 3):
            raise FormulaError("div(a, b, defecto) requiere 2 o 3 argumentos.")
        if f in ("sqrt", "abs", "floor", "ceil") and len(n.args) != 1:
            raise FormulaError(f"{f}() requiere 1 argumento.")
        if f in ("min", "max", "sum", "avg") and not n.args:
            raise FormulaError(f"{f}() requiere al menos 1 argumento.")
        for a in n.args:
            _check(a, nombres)
    else:
        raise FormulaError("Operación no permitida. Use + − × ÷ ^ % // comparaciones (> < >= <= == !=), "
                           "and / or / not, paréntesis, números, variables y funciones.")


def _parse(formula: str, nombres):
    f = normalizar(formula)
    if not f:
        raise FormulaError("La fórmula está vacía.")
    if len(f) > MAX_LARGO:
        raise FormulaError(f"La fórmula es demasiado larga (máximo {MAX_LARGO} caracteres).")
    try:
        tree = ast.parse(f, mode="eval")
    except SyntaxError as e:
        pos = (e.offset or 1)
        raise FormulaError(f"Error de sintaxis cerca de la posición {pos}: «…{f[max(0, pos - 12):pos + 8]}…». "
                           "Revise paréntesis, operadores y comas.")
    if sum(1 for _ in ast.walk(tree)) > MAX_NODOS:
        raise FormulaError("La fórmula es demasiado compleja. Divídala en indicadores más simples.")
    _check(tree.body, set(nombres))
    return tree.body


def validar_formula(formula: str, nombres, variables=None) -> list[str]:
    """Valida la fórmula y devuelve las variables declaradas que no se usan en ella."""
    tree = _parse(formula, nombres)
    usadas = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    return [c for c in (variables if variables is not None else nombres) if c not in usadas]


def _potencia(a, b):
    if abs(b) > 12 or abs(a) > 1e9:
        raise FormulaError("Potencia fuera de rango (exponente máx. 12).")
    return a ** b


def _eval(n, v):
    if isinstance(n, ast.BinOp):
        a, b = _eval(n.left, v), _eval(n.right, v)
        return _potencia(a, b) if isinstance(n.op, ast.Pow) else _BIN[type(n.op)](a, b)
    if isinstance(n, ast.UnaryOp):
        x = _eval(n.operand, v)
        return (not x) if isinstance(n.op, ast.Not) else (-x if isinstance(n.op, ast.USub) else x)
    if isinstance(n, ast.Compare):
        izq = _eval(n.left, v)
        for op, c in zip(n.ops, n.comparators):
            der = _eval(c, v)
            if not _CMP[type(op)](izq, der):
                return False
            izq = der
        return True
    if isinstance(n, ast.BoolOp):
        vals = (_eval(x, v) for x in n.values)
        return all(vals) if isinstance(n.op, ast.And) else any(vals)
    if isinstance(n, ast.IfExp):
        return _eval(n.body, v) if _eval(n.test, v) else _eval(n.orelse, v)
    if isinstance(n, ast.Constant):
        return n.value
    if isinstance(n, ast.Name):
        return v[n.id]
    if n.func.id == "si":
        return _eval(n.args[1], v) if _eval(n.args[0], v) else _eval(n.args[2], v)
    return _FUNCS[n.func.id](*[_eval(a, v) for a in n.args])


def evaluar(formula: str, valores: dict, constantes: dict | None = None, decimales: int = 2) -> float:
    ambito = {**(constantes or {}), **valores}
    body = _parse(formula, ambito.keys())
    try:
        r = float(_eval(body, ambito))
    except ZeroDivisionError:
        raise FormulaError("División entre cero: proteja el denominador con si(b > 0, a / b, 0) o div(a, b, 0).")
    except (OverflowError, ValueError) as e:
        raise FormulaError(f"No se pudo calcular ({e}).")
    if not math.isfinite(r):
        raise FormulaError("El resultado no es un número válido.")
    return round(r, decimales)


# --------------------------------------------------------------- semáforo
def semaforo(valor: float, meta: float, limite: float, sentido: str,
             meta_tope: float | None = None, limite_tope: float | None = None) -> str:
    """Verde / amarillo / rojo. Los topes opcionales acotan el otro extremo de cada franja
    (mayor es mejor: valor máximo de la franja; menor es mejor: valor mínimo)."""
    if sentido == "mayor":
        if valor >= meta and (meta_tope is None or valor <= meta_tope):
            return "verde"
        return "amarillo" if valor >= limite and (limite_tope is None or valor <= limite_tope) else "rojo"
    if valor <= meta and (meta_tope is None or valor >= meta_tope):
        return "verde"
    return "amarillo" if valor <= limite and (limite_tope is None or valor >= limite_tope) else "rojo"


def validar_umbrales(meta: float, limite: float, sentido: str,
                     meta_tope: float | None = None, limite_tope: float | None = None) -> None:
    if sentido == "mayor" and limite > meta:
        raise ValueError("Con «mayor es mejor», el límite crítico debe ser ≤ la meta.")
    if sentido == "menor" and limite < meta:
        raise ValueError("Con «menor es mejor», el límite crítico debe ser ≥ la meta.")
    mayor = sentido == "mayor"
    if meta_tope is not None and (meta_tope < meta if mayor else meta_tope > meta):
        raise ValueError("El tope de la zona verde debe quedar más allá de la meta.")
    if limite_tope is not None and (limite_tope < limite if mayor else limite_tope > limite):
        raise ValueError("El tope de la zona amarilla debe quedar más allá del límite crítico.")


# ------------------------------------------------- períodos y ejercicio fiscal
def _suma_meses(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    return date(d.year + y, m + 1, 1)


def _ejercicio(d: date) -> int:
    """Año en que TERMINA el ejercicio fiscal que contiene a la fecha."""
    return d.year if INICIO == 1 else (d.year + 1 if d.month >= INICIO else d.year)


def _inicio_ejercicio(y: int) -> date:
    return date(y if INICIO == 1 else y - 1, INICIO, 1)


def etiqueta_ejercicio(y: int) -> str:
    return str(y) if INICIO == 1 else f"{y - 1}-{y}"


def codigo(f: str, d: date) -> str:
    """Código del período de frecuencia f que contiene la fecha d."""
    if f in ("mensual", "eventual"):
        return f"{d.year}-{d.month:02d}"
    y = _ejercicio(d)
    if f == "anual":
        return str(y)
    n = ((d.month - INICIO) % 12) // MESES_POR_PERIODO[f] + 1
    return f"{y}-{PREFIJO[f]}{n}"


def _rx(f: str) -> str:
    if f in ("mensual", "eventual"):
        return r"^(\d{4})-(0[1-9]|1[0-2])$"
    if f == "anual":
        return r"^(\d{4})$"
    return rf"^(\d{{4}})-{PREFIJO[f]}([1-9]\d?)$"


def rango(f: str, p: str) -> tuple[date, date] | None:
    """(primer día, último día) del período, o None si el código no es válido."""
    if f not in MESES_POR_PERIODO:
        return None
    m = re.match(_rx(f), p or "")
    if not m:
        return None
    k = MESES_POR_PERIODO[f]
    if f in ("mensual", "eventual"):
        ini = date(int(m.group(1)), int(m.group(2)), 1)
    else:
        n = int(m.group(2)) if m.lastindex > 1 else 1
        if n > 12 // k:
            return None
        ini = _suma_meses(_inicio_ejercicio(int(m.group(1))), (n - 1) * k)
    return ini, _suma_meses(ini, k) - timedelta(days=1)


def periodo_valido(f: str, p: str) -> bool:
    return rango(f, p) is not None


def periodo_actual(f: str, hoy: date) -> str:
    return codigo(f, hoy)


def periodos_recientes(f: str, hoy: date, n: int | None = None) -> list[str]:
    """Del actual hacia atrás."""
    out, p = [], codigo(f, hoy)
    for _ in range(n or HISTORIAL[f]):
        out.append(p)
        p = codigo(f, rango(f, p)[0] - timedelta(days=1))
    return out


def periodos_cerrados(f: str, hoy: date, n: int) -> list[str]:
    return periodos_recientes(f, hoy, n + 1)[1:]


def es_futuro(f: str, p: str, hoy: date) -> bool:
    return rango(f, p)[0] > hoy


def ejercicio_de(f: str, p: str) -> int:
    """Ejercicio fiscal al que pertenece el período."""
    return _ejercicio(rango(f, p)[1])


def periodos_del_ejercicio(f: str, y: int) -> list[str]:
    """Todos los períodos del ejercicio, en orden cronológico."""
    ini, k = _inicio_ejercicio(y), MESES_POR_PERIODO[f]
    return [codigo(f, _suma_meses(ini, i * k)) for i in range(12 // k)]


def etiqueta(f: str, p: str) -> str:
    ini, fin = rango(f, p)
    if f in ("mensual", "eventual"):
        return f"{MESES[ini.month - 1]} {ini.year}"
    ej = etiqueta_ejercicio(ejercicio_de(f, p))
    if f == "anual":
        return f"Ejercicio {ej}"
    pref = PREFIJO[f]
    n = p.rsplit(pref, 1)[1]
    return f"{NOMBRE_CORTO[pref]}{n} {ej} ({MES3[ini.month - 1][:3]}–{MES3[fin.month - 1][:3]})"


def etiqueta_corta(f: str, p: str) -> str:
    """Encabezado breve de columna (mes de cierre del período, como en las fichas en papel)."""
    ini, fin = rango(f, p)
    return MES3[fin.month - 1] if f != "anual" else etiqueta_ejercicio(ejercicio_de(f, p))


def periodos_pendientes(f: str, hoy: date, estados: dict[str, str]) -> list[str]:
    """Períodos cerrados sin carga (o devueltos) — del más antiguo al más reciente."""
    ventana = periodos_cerrados(f, hoy, VENTANA_PENDIENTE[f]) if VENTANA_PENDIENTE[f] else []
    return [p for p in reversed(ventana) if estados.get(p) in (None, "observado")]
