"""Fórmulas seguras, semaforización y manejo de períodos."""
import ast
import math
import re
from datetime import date

MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
         "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
POR_ANIO = {"mensual": 12, "trimestral": 4, "semestral": 2}
# Cuántos períodos ya cerrados se consideran "por cargar"
VENTANA_PENDIENTE = {"mensual": 3, "trimestral": 2, "semestral": 1}
HISTORIAL = {"mensual": 12, "trimestral": 8, "semestral": 6}


class FormulaError(ValueError):
    pass


# ---------------------------------------------------------------- fórmulas
_BIN = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
}
_FUNCS = {"min": min, "max": max, "abs": abs, "round": round}


def _check(n, claves):
    if isinstance(n, ast.BinOp) and type(n.op) in _BIN:
        _check(n.left, claves)
        _check(n.right, claves)
    elif isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
        _check(n.operand, claves)
    elif isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) \
            and not isinstance(n.value, bool):
        pass
    elif isinstance(n, ast.Name):
        if n.id not in claves:
            raise FormulaError(f"Variable desconocida en la fórmula: «{n.id}».")
    elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name) \
            and n.func.id in _FUNCS and not n.keywords:
        for a in n.args:
            _check(a, claves)
    else:
        raise FormulaError("La fórmula solo admite + − × ÷, paréntesis, números, "
                           "variables y min/max/abs/round.")


def _parse(formula: str, claves):
    if not formula or len(formula) > 300:
        raise FormulaError("La fórmula está vacía o es demasiado larga.")
    try:
        tree = ast.parse(formula.strip(), mode="eval")
    except SyntaxError:
        raise FormulaError("La fórmula no tiene una sintaxis válida.")
    _check(tree.body, set(claves))
    return tree.body


def validar_formula(formula: str, claves) -> None:
    _parse(formula, claves)


def _eval(n, v):
    if isinstance(n, ast.BinOp):
        return _BIN[type(n.op)](_eval(n.left, v), _eval(n.right, v))
    if isinstance(n, ast.UnaryOp):
        x = _eval(n.operand, v)
        return -x if isinstance(n.op, ast.USub) else x
    if isinstance(n, ast.Constant):
        return n.value
    if isinstance(n, ast.Name):
        return v[n.id]
    return _FUNCS[n.func.id](*[_eval(a, v) for a in n.args])


def evaluar(formula: str, valores: dict) -> float:
    body = _parse(formula, valores.keys())
    try:
        r = float(_eval(body, valores))
    except ZeroDivisionError:
        raise FormulaError("División entre cero: revise que el denominador sea mayor que cero.")
    if not math.isfinite(r):
        raise FormulaError("El resultado no es un número válido.")
    return round(r, 2)


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
       "semestral": r"^(\d{4})-S([12])$"}


def _fmt(f, y, i):
    return {"mensual": f"{y}-{i:02d}", "trimestral": f"{y}-Q{i}", "semestral": f"{y}-S{i}"}[f]


def _parse_periodo(f, p):
    m = re.match(_RX[f], p or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


def periodo_valido(f: str, p: str) -> bool:
    return _parse_periodo(f, p) is not None


def periodo_actual(f: str, hoy: date) -> str:
    i = {"mensual": hoy.month, "trimestral": (hoy.month - 1) // 3 + 1,
         "semestral": 1 if hoy.month <= 6 else 2}[f]
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
            "semestral": f"S{i} {y}"}[f]


def periodos_pendientes(f: str, hoy: date, estados: dict[str, str]) -> list[str]:
    """Períodos cerrados sin carga (o devueltos) — del más antiguo al más reciente."""
    ventana = periodos_cerrados(f, hoy, VENTANA_PENDIENTE[f])
    return [p for p in reversed(ventana) if estados.get(p) in (None, "observado")]
