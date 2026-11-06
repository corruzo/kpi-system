"""Panel de control: filtros por rango y granularidad, indicadores clave, presupuesto, carga y permisos."""
import pytest
from conftest import CLAVE_ADMIN, crear_area, crear_indicador, crear_usuario, entrar, periodo_actual

from app.dominio import calendario


def rango_vigente():
    ini, fin = calendario.limites(calendario.ejercicio_de_fecha(calendario.hoy()))
    return f"desde={ini.year}-{ini.month:02d}&hasta={fin.year}-{fin.month:02d}"


@pytest.fixture()
def con_datos(client):
    """Un indicador mensual con presupuesto (meta 2) y dos cargas del jefe: una dentro del presupuesto y otra fuera; la primera aprobada."""
    area = crear_area(client)
    jefe, gerente = crear_usuario(client, "jefe", area), crear_usuario(client, "gerente")
    ind = crear_indicador(client, area, nombre="Tiempo de resolución del tablero")
    entrar(client, jefe)
    actual, anterior = periodo_actual(client, ind["id"], 0), periodo_actual(client, ind["id"], 1)
    carga = lambda per, dias, **x: client.post("/api/mediciones", json={"indicador_id": ind["id"], "periodo": per, "valores": {"dias": dias, "tickets": 10}, **x})  # noqa: E731
    m1 = carga(anterior, 10).json()                                    # 1 día <= presupuesto 2: cumple y es verde
    assert carga(actual, 30, analisis="Retraso del proveedor", plan_mejora="Segundo proveedor").status_code == 201   # 3 días: no alcanza
    entrar(client, gerente)
    assert client.post(f"/api/mediciones/{m1['id']}/revision", json={"accion": "aprobar"}).status_code == 200
    return {"area": area, "ind": ind, "gerente": gerente, "jefe": jefe, "actual": actual, "anterior": anterior}


def test_el_tablero_resume_indicadores_semaforos_y_presupuesto(client, con_datos):
    d = client.get(f"/api/tablero?{rango_vigente()}&area_id={con_datos['area']}").json()
    k = d["kpis"]
    assert k["indicadores"] == 1 and k["mediciones"] == 2 and k["verde"] == 1 and k["amarillo"] == 1 and k["cumplimiento"] == 50.0
    assert k["con_ppto"] == 2 and k["cumplen_ppto"] == 1 and k["cumplimiento_ppto"] == 50.0 and k["real_vs_ppto"] == 100.0   # (50 % + 150 %) / 2
    assert k["por_aprobar"] == 1 and k["cargas"] == 2
    ind = d["indicadores"][0]
    assert ind["codigo"] == con_datos["ind"]["codigo"] and ind["n"] == 2 and len(ind["serie"]) == 2 and ind["serie"][0]["presupuesto"] == 2
    assert d["actual"] == {"verde": 0, "amarillo": 1, "rojo": 0, "sin_datos": 0}        # la última carga está en alerta
    assert {r["nombre"] for r in d["responsables"]} and d["responsables"][0]["cargas"] == 2
    assert all(a["id"] == ind["id"] for a in d["atencion"])                              # lo que requiere atención es de este indicador


@pytest.mark.parametrize("agrupar,max_cubetas", [("mes", 12), ("bimestre", 6), ("trimestre", 4), ("cuatrimestre", 3), ("semestre", 2), ("anio", 1)])
def test_la_vista_se_agrupa_por_la_granularidad_elegida(client, con_datos, agrupar, max_cubetas):
    d = client.get(f"/api/tablero?{rango_vigente()}&agrupar={agrupar}&area_id={con_datos['area']}").json()
    assert len(d["serie"]) == max_cubetas
    assert sum(c["total"] for c in d["serie"]) == d["kpis"]["mediciones"] == 2             # nada se pierde al agrupar
    assert sum(c["con_ppto"] for c in d["serie"]) == 2


def test_el_rango_de_fechas_y_los_filtros_recortan_los_datos(client, con_datos):
    ini = calendario.hoy().replace(day=1)
    solo_este_mes = f"desde={ini.year}-{ini.month:02d}&hasta={ini.year}-{ini.month:02d}&area_id={con_datos['area']}"
    d = client.get(f"/api/tablero?{solo_este_mes}").json()
    assert d["kpis"]["mediciones"] == 1 and len(d["serie"]) == 1 and d["rango"]["meses"] == 1
    assert d["anterior"]["mediciones"] <= 1                                                  # rango anterior de igual duración (1 mes)
    otra_area = crear_area(client)
    entrar(client, con_datos["gerente"])
    assert client.get(f"/api/tablero?{rango_vigente()}&area_id={otra_area}").json()["kpis"]["indicadores"] == 0
    assert client.get(f"/api/tablero?{rango_vigente()}&area_id={con_datos['area']}&frecuencia=anual").json()["kpis"]["indicadores"] == 0
    assert client.get(f"/api/tablero?{rango_vigente()}&area_id={con_datos['area']}&indicador_id={con_datos['ind']['id']}").json()["kpis"]["mediciones"] == 2
    solo_aprobadas = client.get(f"/api/tablero?{rango_vigente()}&area_id={con_datos['area']}&solo_aprobadas=true").json()
    assert solo_aprobadas["kpis"]["mediciones"] == 1 and solo_aprobadas["kpis"]["verde"] == 1


def test_comparativo_por_dimension(client, con_datos):
    for dim in ("area", "gerencia", "seguimiento", "frecuencia", "proceso"):
        d = client.get(f"/api/tablero?{rango_vigente()}&area_id={con_datos['area']}&dimension={dim}").json()
        assert d["dimension"] == dim and sum(g["indicadores"] for g in d["por_dimension"]) == 1


def test_parametros_invalidos_y_permisos(client, con_datos):
    for q in ("desde=2026-05&hasta=2026-01", "desde=2020-01&hasta=2026-01", "desde=abc&hasta=2026-01", "agrupar=semana", "frecuencia=semanal",
              "dimension=otra", "area_id=0"):
        assert client.get(f"/api/tablero?{q}").status_code == 422, q
    entrar(client, con_datos["jefe"])
    assert client.get("/api/tablero").status_code == 403
    entrar(client, "admin", CLAVE_ADMIN)
    assert client.get("/api/tablero").status_code == 200                                   # sin fechas: el ejercicio vigente


def test_las_cargas_importadas_no_cuentan_en_la_puntualidad(client, con_datos):
    from app.database import SessionLocal
    from app.models import Medicion
    with SessionLocal() as db:
        m = db.query(Medicion).filter_by(indicador_id=con_datos["ind"]["id"], periodo=con_datos["anterior"]).one()
        m.nota_revision = "Importado desde Excel «x.xlsx» (hoja «y»)."
        db.commit()
    d = client.get(f"/api/tablero?{rango_vigente()}&area_id={con_datos['area']}").json()
    assert d["kpis"]["cargas"] == 2 and d["responsables"][0]["cargas"] == 1                # solo cuenta la carga hecha por el jefe
