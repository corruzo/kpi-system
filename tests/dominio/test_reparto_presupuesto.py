import pytest

from app.dominio import presupuesto


def test_repartir_igual_divide_el_total():
    assert presupuesto.repartir(1200, 12, "igual") == [100.0] * 12
    assert presupuesto.repartir(100, 4, "igual") == [25.0] * 4


def test_repetir_conserva_el_valor_en_cada_periodo():
    assert presupuesto.repartir(95, 3, "repetir") == [95, 95, 95]


def test_reparto_invalido():
    with pytest.raises(ValueError):
        presupuesto.repartir(10, 0, "igual")
    with pytest.raises(ValueError):
        presupuesto.repartir(10, 3, "otro")


def test_comparar_mayor_es_mejor():
    r = presupuesto.comparar(110, 100, "mayor")
    assert r == {"presupuesto": 100, "desviacion": 10, "porcentaje": 110.0, "cumple": True}
    assert presupuesto.comparar(90, 100, "mayor")["cumple"] is False


def test_comparar_menor_es_mejor():
    assert presupuesto.comparar(3, 4, "menor")["cumple"] is True
    assert presupuesto.comparar(5, 4, "menor")["cumple"] is False


def test_comparar_sin_presupuesto_o_presupuesto_cero():
    assert presupuesto.comparar(5, None, "mayor") is None
    assert presupuesto.comparar(5, 0, "mayor")["porcentaje"] is None
