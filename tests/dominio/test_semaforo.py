import pytest

from app.dominio import semaforo


@pytest.mark.parametrize("valor, esperado", [(95, "verde"), (90, "verde"), (85, "amarillo"), (80, "amarillo"), (70, "rojo")])
def test_mayor_es_mejor(valor, esperado):
    assert semaforo.clasificar(valor, 90, 80, "mayor") == esperado


@pytest.mark.parametrize("valor, esperado", [(2, "verde"), (3, "verde"), (4, "amarillo"), (5, "amarillo"), (6, "rojo")])
def test_menor_es_mejor(valor, esperado):
    assert semaforo.clasificar(valor, 3, 5, "menor") == esperado


def test_topes_acotan_el_otro_extremo_de_cada_franja():
    assert semaforo.clasificar(600, 96, 85, "mayor", 500, 1000) == "amarillo"   # pasó el tope verde
    assert semaforo.clasificar(1200, 96, 85, "mayor", 500, 1000) == "rojo"
    assert semaforo.clasificar(-0.5, 3, 5, "menor", 0, 0) == "rojo"             # por debajo del mínimo


def test_umbrales_incoherentes_se_rechazan():
    with pytest.raises(ValueError):
        semaforo.validar_umbrales(90, 95, "mayor")
    with pytest.raises(ValueError):
        semaforo.validar_umbrales(3, 2, "menor")
    with pytest.raises(ValueError):
        semaforo.validar_umbrales(96, 85, "mayor", meta_tope=50)
