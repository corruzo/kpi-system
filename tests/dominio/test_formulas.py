import pytest

from app.dominio import formulas


def test_operaciones_basicas_y_simbolos_amigables():
    assert formulas.evaluar("a / b * 100", {"a": 1, "b": 4}) == 25
    assert formulas.evaluar("a ^ 2 ÷ 4", {"a": 6}) == 9
    assert formulas.evaluar("a if a > 3 else 0", {"a": 5}) == 5


def test_si_y_division_segura_no_fallan_con_cero():
    assert formulas.evaluar("si(b > 0, a / b * 100, 100)", {"a": 5, "b": 0}) == 100
    assert formulas.evaluar("pct(a, b)", {"a": 1, "b": 0}) == 0
    assert formulas.evaluar("div(a, b, 7)", {"a": 1, "b": 0}) == 7


def test_constantes_y_decimales():
    assert formulas.evaluar("a * factor / h", {"a": 2, "h": 400000}, {"factor": 1000000}, 3) == 5.0
    assert formulas.evaluar("a / 3", {"a": 1}, decimales=4) == 0.3333


def test_division_entre_cero_da_mensaje_util():
    with pytest.raises(formulas.FormulaError, match="División entre cero"):
        formulas.evaluar("a / b", {"a": 1, "b": 0})


@pytest.mark.parametrize("formula", ["__import__('os').system('ls')", "a.b", "x + 1", "si(a)", "a /", "open('f')"])
def test_formulas_peligrosas_o_invalidas_se_rechazan(formula):
    with pytest.raises(formulas.FormulaError):
        formulas.evaluar(formula, {"a": 1})


def test_validar_informa_variables_sin_usar():
    assert formulas.validar("a * 2", ["a", "b"]) == ["b"]
    assert formulas.validar("a * 2", ["a", "b"], ["a"]) == []


def test_limites_de_tamano_y_potencia():
    with pytest.raises(formulas.FormulaError):
        formulas.evaluar("a ** 50", {"a": 2})
    with pytest.raises(formulas.FormulaError):
        formulas.evaluar("a + " * 400 + "a", {"a": 1})
