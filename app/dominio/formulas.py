"""Evaluador seguro de fórmulas de indicadores.

Admite + − × ÷ ^ % //, comparaciones, and/or/not, si(), «a if c else b» y un conjunto cerrado de funciones.
Nunca usa eval(): la fórmula se analiza como árbol (ast) y se valida nodo por nodo antes de calcular.

Flujo de uso:  normalizar() → validar() al guardar una ficha → evaluar() al calcular un resultado.
"""
import ast
import math
import re

MAX_LARGO = 1000      # caracteres
MAX_NODOS = 300       # complejidad máxima del árbol


class FormulaError(ValueError):
    """La fórmula es inválida o no se puede calcular con los datos dados."""


# ------------------------------------------------------------------ vocabulario permitido
def _dividir(a, b, defecto=0.0):
    return defecto if b == 0 else a / b


_FUNCIONES = {
    "min": min, "max": max, "abs": abs, "round": round, "sqrt": math.sqrt, "floor": math.floor, "ceil": math.ceil,
    "sum": lambda *a: sum(a), "avg": lambda *a: sum(a) / len(a),
    "div": _dividir,                                     # div(a, b, defecto): división segura
    "pct": lambda a, b: _dividir(a, b) * 100,            # pct(a, b): a / b × 100 (0 si b = 0)
    "clamp": lambda x, lo, hi: max(lo, min(hi, x)),      # clamp(x, mínimo, máximo)
}
_PEREZOSAS = {"si"}                                      # si(cond, a, b): solo evalúa la rama elegida
FUNCIONES = sorted(set(_FUNCIONES) | _PEREZOSAS)
RESERVADAS = set(FUNCIONES) | {"and", "or", "not", "if", "else", "True", "False", "None"}

_ARITMETICOS = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b, ast.Mult: lambda a, b: a * b,
                ast.Div: lambda a, b: a / b, ast.Mod: lambda a, b: a % b, ast.FloorDiv: lambda a, b: a // b}
_COMPARACIONES = {ast.Lt: lambda a, b: a < b, ast.LtE: lambda a, b: a <= b, ast.Gt: lambda a, b: a > b,
                  ast.GtE: lambda a, b: a >= b, ast.Eq: lambda a, b: a == b, ast.NotEq: lambda a, b: a != b}
_ARGUMENTOS = {"si": (3, 3), "div": (2, 3), "pct": (2, 2), "clamp": (3, 3), "round": (1, 2),
               "sqrt": (1, 1), "abs": (1, 1), "floor": (1, 1), "ceil": (1, 1)}   # (mín, máx) de argumentos


# ------------------------------------------------------------------ preparación
def normalizar(formula: str) -> str:
    """Admite símbolos amigables (×, ÷, −, ^, ≥, ≤, ≠, saltos de línea) y los convierte a sintaxis estándar."""
    f = (formula or "").replace("×", "*").replace("÷", "/").replace("−", "-").replace("–", "-")
    f = f.replace("≥", ">=").replace("≤", "<=").replace("≠", "!=").replace("^", "**")
    return re.sub(r"\s+", " ", f).strip()


def _analizar(formula: str, nombres) -> ast.expr:
    f = normalizar(formula)
    if not f:
        raise FormulaError("La fórmula está vacía.")
    if len(f) > MAX_LARGO:
        raise FormulaError(f"La fórmula es demasiado larga (máximo {MAX_LARGO} caracteres).")
    try:
        arbol = ast.parse(f, mode="eval")
    except SyntaxError as e:
        pos = e.offset or 1
        raise FormulaError(f"Error de sintaxis cerca de la posición {pos}: «…{f[max(0, pos - 12):pos + 8]}…». "
                           "Revise paréntesis, operadores y comas.") from None
    if sum(1 for _ in ast.walk(arbol)) > MAX_NODOS:
        raise FormulaError("La fórmula es demasiado compleja. Divídala en indicadores más simples.")
    _verificar(arbol.body, set(nombres))
    return arbol.body


def _verificar_llamada(n: ast.Call, nombres: set):
    f = n.func.id if isinstance(n.func, ast.Name) else None
    if f not in _FUNCIONES and f not in _PEREZOSAS or n.keywords:
        raise FormulaError(f"La función «{f}» no existe. Disponibles: {', '.join(FUNCIONES)}.")
    minimo, maximo = _ARGUMENTOS.get(f, (1, 99))
    if not minimo <= len(n.args) <= maximo:
        raise FormulaError(f"{f}() requiere {minimo if minimo == maximo else f'{minimo} a {maximo}'} argumento(s).")
    for a in n.args:
        _verificar(a, nombres)


def _verificar(n: ast.expr, nombres: set):
    """Acepta únicamente los nodos del vocabulario permitido."""
    if isinstance(n, ast.BinOp) and type(n.op) in (*_ARITMETICOS, ast.Pow):
        _verificar(n.left, nombres)
        _verificar(n.right, nombres)
    elif isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd, ast.Not)):
        _verificar(n.operand, nombres)
    elif isinstance(n, ast.Compare) and all(type(o) in _COMPARACIONES for o in n.ops):
        for parte in (n.left, *n.comparators):
            _verificar(parte, nombres)
    elif isinstance(n, ast.BoolOp):
        for v in n.values:
            _verificar(v, nombres)
    elif isinstance(n, ast.IfExp):
        for parte in (n.test, n.body, n.orelse):
            _verificar(parte, nombres)
    elif isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
        pass  # incluye True / False
    elif isinstance(n, ast.Name):
        if n.id not in nombres:
            raise FormulaError(f"«{n.id}» no es una variable, constante ni función conocida.")
    elif isinstance(n, ast.Call):
        _verificar_llamada(n, nombres)
    else:
        raise FormulaError("Operación no permitida. Use + − × ÷ ^ % // comparaciones (> < >= <= == !=), "
                           "and / or / not, paréntesis, números, variables y funciones.")


def validar(formula: str, nombres, variables=None) -> list[str]:
    """Valida la fórmula contra los nombres disponibles; devuelve las variables declaradas que no usa."""
    arbol = _analizar(formula, nombres)
    usadas = {n.id for n in ast.walk(arbol) if isinstance(n, ast.Name)}
    return [c for c in (variables if variables is not None else nombres) if c not in usadas]


# ------------------------------------------------------------------ cálculo
def _potencia(a, b):
    if abs(b) > 12 or abs(a) > 1e9:
        raise FormulaError("Potencia fuera de rango (exponente máx. 12).")
    return a ** b


def _calcular(n: ast.expr, v: dict):
    if isinstance(n, ast.BinOp):
        a, b = _calcular(n.left, v), _calcular(n.right, v)
        return _potencia(a, b) if isinstance(n.op, ast.Pow) else _ARITMETICOS[type(n.op)](a, b)
    if isinstance(n, ast.UnaryOp):
        x = _calcular(n.operand, v)
        return (not x) if isinstance(n.op, ast.Not) else (-x if isinstance(n.op, ast.USub) else x)
    if isinstance(n, ast.Compare):
        izq = _calcular(n.left, v)
        for op, c in zip(n.ops, n.comparators, strict=False):
            der = _calcular(c, v)
            if not _COMPARACIONES[type(op)](izq, der):
                return False
            izq = der
        return True
    if isinstance(n, ast.BoolOp):
        valores = (_calcular(x, v) for x in n.values)
        return all(valores) if isinstance(n.op, ast.And) else any(valores)
    if isinstance(n, ast.IfExp):
        return _calcular(n.body, v) if _calcular(n.test, v) else _calcular(n.orelse, v)
    if isinstance(n, ast.Constant):
        return n.value
    if isinstance(n, ast.Name):
        return v[n.id]
    if n.func.id == "si":
        return _calcular(n.args[1], v) if _calcular(n.args[0], v) else _calcular(n.args[2], v)
    return _FUNCIONES[n.func.id](*[_calcular(a, v) for a in n.args])


def evaluar(formula: str, valores: dict, constantes: dict | None = None, decimales: int = 2) -> float:
    """Resultado de la fórmula con los valores y constantes dados, redondeado a `decimales`."""
    ambito = {**(constantes or {}), **valores}
    cuerpo = _analizar(formula, ambito.keys())
    try:
        r = float(_calcular(cuerpo, ambito))
    except ZeroDivisionError:
        raise FormulaError("División entre cero: proteja el denominador con si(b > 0, a / b, 0) o div(a, b, 0).") from None
    except (OverflowError, ValueError) as e:
        raise FormulaError(f"No se pudo calcular ({e}).") from None
    if not math.isfinite(r):
        raise FormulaError("El resultado no es un número válido.")
    return round(r, decimales)
