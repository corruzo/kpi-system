"""Traduce una fórmula del sistema a una fórmula de Excel, para que los reportes exportados se recalculen solos.

Cada nombre (variable o constante) se reemplaza por lo que indique `celdas`: una referencia («B21») o un número.
Devuelve None si la fórmula usa algo sin equivalente exacto; el reporte deja entonces el valor calculado.
"""
import ast

from . import formulas

_BINARIOS = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/", ast.Pow: "^"}
_COMPARADORES = {ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=", ast.Eq: "=", ast.NotEq: "<>"}
_SIMPLES = {"min": "MIN", "max": "MAX", "abs": "ABS", "sqrt": "SQRT", "sum": "SUM", "avg": "AVERAGE"}


class _SinEquivalente(Exception):
    pass


def _t(n: ast.expr, celdas: dict) -> str:
    if isinstance(n, ast.Constant):
        if isinstance(n.value, bool):
            return "TRUE" if n.value else "FALSE"
        return repr(n.value)
    if isinstance(n, ast.Name):
        return celdas[n.id]
    if isinstance(n, ast.BinOp):
        a, b = _t(n.left, celdas), _t(n.right, celdas)
        if isinstance(n.op, ast.Mod):
            return f"MOD({a},{b})"
        if isinstance(n.op, ast.FloorDiv):
            return f"INT({a}/{b})"
        return f"({a}{_BINARIOS[type(n.op)]}{b})"
    if isinstance(n, ast.UnaryOp):
        x = _t(n.operand, celdas)
        return f"NOT({x})" if isinstance(n.op, ast.Not) else (f"(-{x})" if isinstance(n.op, ast.USub) else x)
    if isinstance(n, ast.Compare):
        partes, izq = [], _t(n.left, celdas)
        for op, c in zip(n.ops, n.comparators, strict=False):
            der = _t(c, celdas)
            partes.append(f"{izq}{_COMPARADORES[type(op)]}{der}")
            izq = der
        return partes[0] if len(partes) == 1 else f"AND({','.join(partes)})"
    if isinstance(n, ast.BoolOp):
        return f"{'AND' if isinstance(n.op, ast.And) else 'OR'}({','.join(_t(v, celdas) for v in n.values)})"
    if isinstance(n, ast.IfExp):
        return f"IF({_t(n.test, celdas)},{_t(n.body, celdas)},{_t(n.orelse, celdas)})"
    if isinstance(n, ast.Call):
        f, a = n.func.id, [_t(x, celdas) for x in n.args]
        if f == "si":
            return f"IF({a[0]},{a[1]},{a[2]})"
        if f in _SIMPLES:
            return f"{_SIMPLES[f]}({','.join(a)})"
        if f == "floor":
            return f"INT({a[0]})"
        if f == "ceil":
            return f"(-INT(-{a[0]}))"
        if f == "round":
            return f"ROUND({a[0]},{a[1] if len(a) > 1 else 0})"
        if f == "div":
            return f"IF({a[1]}=0,{a[2] if len(a) > 2 else 0},{a[0]}/{a[1]})"
        if f == "pct":
            return f"IF({a[1]}=0,0,{a[0]}/{a[1]}*100)"
        if f == "clamp":
            return f"MAX({a[1]},MIN({a[2]},{a[0]}))"
    raise _SinEquivalente


def a_excel(formula: str, celdas: dict[str, str], decimales: int = 2) -> str | None:
    """Fórmula de Excel (con el signo «=» y redondeada a `decimales`) o None si no se puede traducir."""
    try:
        return f"=ROUND({_t(formulas.analizar(formula, celdas.keys()), celdas)},{decimales})"
    except (_SinEquivalente, formulas.FormulaError, KeyError):
        return None
