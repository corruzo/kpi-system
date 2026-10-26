"""Fórmulas seguras, semaforización y manejo de períodos."""
import ast
import math
import re
from datetime import date

MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
         "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
POR_ANIO = {"mensual": 12, "trimestral": 4, "semestral": 2, "anual": 1}
# Cuántos períodos ya cerrados se consideran "por cargar"
VENTANA_PENDIENTE = {"mensual": 3, "trimestral": 2, "semestral": 1, "anual": 1}
HISTORIAL = {"mensual": 24, "trimestral": 12, "semestral": 8, "anual": 5}


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
def semaforo(valor: float, meta: float, limite: float, sentido: str) -> str:
    if sentido == "mayor":
        return "verde" if valor >= meta else "amarillo" if valor >= limite else "rojo"
    return "verde" if valor <= meta else "amarillo" if valor <= limite else "rojo"


def validar_umbrales(meta: float, limite: float, sentido: str) -> None:
    if sentido == "mayor" and limite > meta:
        raise ValueError("Con «mayor es mejor», el límite crítico debe ser ≤ la meta.")
    if sentido == "menor" and limite < meta:
        raise ValueError("Con «menor es mejor», el límite crítico debe ser ≥ la meta.")


# ---------------------------------------------------------------- períodos
_RX = {"mensual": r"^(\d{4})-(0[1-9]|1[0-2])$",
       "trimestral": r"^(\d{4})-Q([1-4])$",
       "semestral": r"^(\d{4})-S([12])$",
       "anual": r"^(\d{4})$"}


def _fmt(f, y, i):
    return {"mensual": f"{y}-{i:02d}", "trimestral": f"{y}-Q{i}", "semestral": f"{y}-S{i}", "anual": f"{y}"}[f]


def _parse_periodo(f, p):
    m = re.match(_RX[f], p or "")
    return (int(m.group(1)), int(m.group(2)) if m.lastindex > 1 else 1) if m else None


def periodo_valido(f: str, p: str) -> bool:
    return _parse_periodo(f, p) is not None


def periodo_actual(f: str, hoy: date) -> str:
    i = {"mensual": hoy.month, "trimestral": (hoy.month - 1) // 3 + 1,
         "semestral": 1 if hoy.month <= 6 else 2, "anual": 1}[f]
    return _fmt(f, hoy.year, i)


def periodos_recientes(f: str, hoy: date, n: int | None = None) -> list[str]:
    """Del actual hacia atrás."""
    y, i = _parse_periodo(f, periodo_actual(f, hoy))
    out = []
    for _ in range(n or HISTORIAL[f]):
        out.append(_fmt(f, y, i))
        i -= 1
        if i < 1:
            y, i = y - 1, POR_ANIO[f]
    return out


def periodos_cerrados(f: str, hoy: date, n: int) -> list[str]:
    return periodos_recientes(f, hoy, n + 1)[1:]


def es_futuro(f: str, p: str, hoy: date) -> bool:
    return _parse_periodo(f, p) > _parse_periodo(f, periodo_actual(f, hoy))


def etiqueta(f: str, p: str) -> str:
    y, i = _parse_periodo(f, p)
    return {"mensual": f"{MESES[i - 1]} {y}", "trimestral": f"T{i} {y}",
            "semestral": f"S{i} {y}", "anual": f"Año {y}"}[f]


def periodos_pendientes(f: str, hoy: date, estados: dict[str, str]) -> list[str]:
    """Períodos cerrados sin carga (o devueltos) — del más antiguo al más reciente."""
    ventana = periodos_cerrados(f, hoy, VENTANA_PENDIENTE[f])
    return [p for p in reversed(ventana) if estados.get(p) in (None, "observado")]
