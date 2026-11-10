import pytest

from app.dominio import meta


def test_repartir_igual_divide_el_total():
    assert meta.repartir(1200, 12, "igual") == [100.0] * 12
    assert meta.repartir(100, 4, "igual") == [25.0] * 4


def test_repetir_conserva_el_valor_en_cada_periodo():
    assert meta.repartir(95, 3, "repetir") == [95, 95, 95]


def test_reparto_invalido():
    with pytest.raises(ValueError):
        meta.repartir(10, 0, "igual")
    with pytest.raises(ValueError):
        meta.repartir(10, 3, "otro")


def test_comparar_mayor_es_mejor():
    r = meta.comparar(110, 100, "mayor")
    assert r == {"meta": 100, "desviacion": 10, "porcentaje": 110.0, "cumple": True}
    assert meta.comparar(90, 100, "mayor")["cumple"] is False


def test_comparar_menor_es_mejor():
    assert meta.comparar(3, 4, "menor")["cumple"] is True
    assert meta.comparar(5, 4, "menor")["cumple"] is False


def test_comparar_sin_meta_o_meta_cero():
    assert meta.comparar(5, None, "mayor") is None
    assert meta.comparar(5, 0, "mayor")["porcentaje"] is None
