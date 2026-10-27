from datetime import date

import pytest

from app.dominio import calendario


@pytest.fixture()
def ejercicio_octubre():
    anterior = calendario.inicio_mes()
    calendario.configurar(10)
    yield
    calendario.configurar(anterior)


@pytest.fixture()
def ejercicio_anual_natural():
    anterior = calendario.inicio_mes()
    calendario.configurar(1)
    yield
    calendario.configurar(anterior)


def test_ejercicio_octubre_septiembre(ejercicio_octubre):
    assert calendario.etiqueta_ejercicio(2026) == "2025-2026"
    assert calendario.limites(2026) == (date(2025, 10, 1), date(2026, 9, 30))
    assert calendario.ejercicio_de_fecha(date(2025, 10, 1)) == 2026
    assert calendario.ejercicio_de_fecha(date(2026, 9, 30)) == 2026
    assert calendario.meses_del_ejercicio()[0] == "Oct."


def test_codigos_de_periodo_por_frecuencia(ejercicio_octubre):
    assert calendario.codigo("mensual", date(2025, 10, 15)) == "2025-10"
    assert calendario.codigo("trimestral", date(2025, 12, 31)) == "2026-Q1"
    assert calendario.codigo("trimestral", date(2026, 9, 1)) == "2026-Q4"
    assert calendario.codigo("bimestral", date(2025, 11, 1)) == "2026-B1"
    assert calendario.codigo("cuatrimestral", date(2026, 1, 31)) == "2026-C1"
    assert calendario.codigo("semestral", date(2026, 3, 31)) == "2026-S1"
    assert calendario.codigo("anual", date(2026, 9, 30)) == "2026"
    assert calendario.codigo("anual", date(2026, 10, 1)) == "2027"


def test_columnas_del_ejercicio_como_las_fichas_en_papel(ejercicio_octubre):
    trimestres = calendario.periodos_del_ejercicio("trimestral", 2026)
    assert trimestres == ["2026-Q1", "2026-Q2", "2026-Q3", "2026-Q4"]
    assert [calendario.etiqueta_corta("trimestral", p) for p in trimestres] == ["Dic.", "Mar.", "Jun.", "Sep."]
    assert calendario.etiqueta_corta("bimestral", "2026-B1") == "Nov."
    assert calendario.indice_de_mes("trimestral", "2026-Q1") == 2
    assert calendario.rango("semestral", "2026-S2") == (date(2026, 4, 1), date(2026, 9, 30))


def test_periodos_recientes_y_pendientes(ejercicio_octubre):
    hoy = date(2026, 10, 26)
    assert calendario.periodos_recientes("mensual", hoy, 3) == ["2026-10", "2026-09", "2026-08"]
    assert calendario.periodos_pendientes("mensual", hoy, {"2026-09": "aprobado"}) == ["2026-07", "2026-08"]
    assert calendario.periodos_pendientes("eventual", hoy, {}) == []


def test_validacion_de_codigos(ejercicio_octubre):
    assert calendario.periodo_valido("trimestral", "2026-Q4")
    assert not calendario.periodo_valido("trimestral", "2026-Q5")
    assert not calendario.periodo_valido("mensual", "2026-13")
    assert not calendario.periodo_valido("anual", "26")


def test_con_inicio_en_enero_coincide_con_el_ano_natural(ejercicio_anual_natural):
    assert calendario.codigo("semestral", date(2026, 3, 1)) == "2026-S1"
    assert calendario.etiqueta_ejercicio(2026) == "2026"


def test_un_indicador_nuevo_no_debe_periodos_anteriores_a_su_creacion(ejercicio_octubre):
    hoy = date(2026, 10, 26)
    assert calendario.periodos_pendientes("mensual", hoy, {}, desde=hoy) == []                       # creado hoy: nada debido
    assert calendario.periodos_pendientes("mensual", hoy, {}, desde=date(2026, 8, 15)) == ["2026-08", "2026-09"]
    assert calendario.periodos_pendientes("mensual", hoy, {"2026-07": "observado"}, desde=hoy) == ["2026-07"]   # lo devuelto sigue pendiente
