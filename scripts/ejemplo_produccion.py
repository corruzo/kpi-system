"""Ejemplo completo del flujo del SGC con el área de Producción (para aprender a usar el sistema).

Crea, a través de la API: el área, un jefe y un gerente, cuatro indicadores con sus metas y la carga mensual de datos
reales del ejercicio (aprobada por el gerente salvo el último mes, que queda pendiente, y un mes devuelto y reenviado).

    python scripts/ejemplo_produccion.py --url http://127.0.0.1:8000 --admin admin --clave-admin '...'

Es solo un ejemplo: crea usuarios reales. En un sistema de producción bórrelos (desactívelos) cuando termine.
Requiere `httpx` (pip install -r requirements-dev.txt).
"""
import argparse
import secrets
import sys
from datetime import date

import httpx

AREA = "Producción"

# (código, nombre, objetivo, unidad, sentido, fórmula, variables [(clave, etiqueta, ayuda)], meta, límite, decimales, fuente)
INDICADORES = [
    ("PRO-01", "Cumplimiento del plan de producción", "Producir lo programado cada mes.", "%", "mayor",
     "real / plan * 100", [("plan", "Producción planificada (kg)", "Lo presupuestado para el mes"),
                           ("real", "Producción real (kg)", "Lo efectivamente producido")], 95, 85, 1, "Reporte de planta"),
    ("PRO-02", "Producto conforme a la primera", "Producir sin retrabajos.", "%", "mayor",
     "conformes / producidas * 100", [("producidas", "Unidades producidas", ""), ("conformes", "Unidades conformes", "")],
     98, 95, 1, "Control de calidad"),
    ("PRO-03", "Paradas no programadas", "Reducir el tiempo perdido por averías.", "%", "menor",
     "horas_parada / horas_programadas * 100", [("horas_parada", "Horas de parada", ""),
                                                ("horas_programadas", "Horas programadas", "")], 5, 8, 1, "Bitácora de mantenimiento"),
    ("PRO-04", "Merma de materia prima", "Aprovechar la materia prima.", "%", "menor",
     "merma / materia_prima * 100", [("merma", "Merma (kg)", ""), ("materia_prima", "Materia prima usada (kg)", "")],
     2, 3.5, 2, "Balance de materiales"),
]

# Datos reales por mes (enero…): cada fila corresponde a las variables del indicador, en el mismo orden.
DATOS = {
    "PRO-01": [(12000, 11900), (12000, 12150), (12500, 11300), (12000, 10100), (12000, 11800), (12000, 12400),
               (12000, 11950), (12000, 9800), (12000, 11700), (12000, 12050), (12000, 11500), (12000, 12200)],
    "PRO-02": [(11900, 11700), (12150, 11990), (11300, 11050), (10100, 9500), (11800, 11600), (12400, 12300),
               (11950, 11700), (9800, 9300), (11700, 11500), (12050, 11950), (11500, 11400), (12200, 12100)],
    "PRO-03": [(18, 400), (22, 400), (30, 420), (48, 400), (20, 400), (14, 420),
               (25, 400), (60, 400), (22, 400), (16, 420), (24, 400), (18, 400)],
    "PRO-04": [(210, 11000), (230, 11200), (330, 10800), (520, 9700), (240, 10900), (200, 11300),
               (260, 11000), (480, 9400), (250, 10800), (190, 11100), (240, 10600), (210, 11200)],
}
ANALISIS = ("El resultado quedó fuera de la meta por causas del período (paradas y reprocesos).",
            "Se programó mantenimiento preventivo y revisión del plan con el área de compras.")
DEVUELTO = 8   # índice (0 = enero): este mes el gerente pide corregir y el jefe reenvía


def cliente(url: str, usuario: str, clave: str) -> httpx.Client:
    c = httpx.Client(base_url=url, timeout=30)
    r = c.post("/api/login", json={"username": usuario, "password": clave})
    if r.status_code != 200:
        sys.exit(f"No se pudo ingresar como «{usuario}»: {r.text}")
    return c


def exigir(r: httpx.Response, que: str):
    if r.status_code >= 300:
        sys.exit(f"{que}: {r.status_code} {r.text}")
    return r.json()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("--admin", default="admin")
    ap.add_argument("--clave-admin", required=True)
    ap.add_argument("--clave-demo", default=None, help="contraseña de los usuarios del ejemplo (por defecto, una aleatoria)")
    ap.add_argument("--inicio-ejercicio", type=int, default=None,
                    help="mes en que inicia el ejercicio fiscal (1 = enero). Solo si aún no hay cargas ni ejercicios cerrados")
    a = ap.parse_args()
    clave = a.clave_demo or secrets.token_urlsafe(12)
    hoy = date.today()

    adm = cliente(a.url, a.admin, a.clave_admin)
    if a.inicio_ejercicio:
        p = exigir(adm.get("/api/parametros"), "Leer parámetros")
        exigir(adm.put("/api/parametros", json={
            "empresa": p["empresa"], "gerencia_emisora": p["gerencia_emisora"], "codigo_formato": p["codigo_formato"],
            "ejercicio_inicio": a.inicio_ejercicio, "proteger_reportes": p["proteger_reportes"], "clave_reportes": ""}),
            "Cambiar el inicio del ejercicio")
    inicio = exigir(adm.get("/api/parametros"), "Leer parámetros")["ejercicio_inicio"]

    # 1) Administrador: área, usuarios y fichas (aquí se fijan las METAS)
    if any(x["nombre"] == AREA for x in exigir(adm.get("/api/areas"), "Listar áreas")):
        sys.exit(f"El área «{AREA}» ya existe: el ejemplo ya fue creado.")
    area = exigir(adm.post("/api/areas", json={"nombre": AREA}), "Crear área")["id"]
    for rol, usuario, nombre in (("jefe", "jefe.produccion", "Jefe de Producción"), ("gerente", "gerente.calidad", "Gerente de Calidad")):
        exigir(adm.post("/api/usuarios", json={"username": usuario, "nombre": nombre, "rol": rol,
                                               "area_id": area if rol == "jefe" else None, "password": clave}), f"Crear {usuario}")
    ids = {}
    for cod, nombre, objetivo, unidad, sentido, formula, variables, meta, limite, dec, fuente in INDICADORES:
        ids[cod] = exigir(adm.post("/api/indicadores", json={
            "codigo": cod, "nombre": nombre, "objetivo": objetivo, "area_id": area, "unidad": unidad, "frecuencia": "mensual",
            "sentido": sentido, "formula": formula, "meta": meta, "limite": limite, "decimales": dec, "fuente": fuente,
            "seguimiento": "proceso", "ref_nombre": "Proceso de Producción", "ref_detalle": "Fabricar según el plan, con calidad y sin desperdicio",
            "variables": [{"clave": k, "etiqueta": e, "ayuda": h} for k, e, h in variables]}), f"Crear {cod}")["id"]

    # 2) Jefe de área: carga mensual de datos reales, de enero (inicio del ejercicio) hasta el mes actual
    jefe, ger = cliente(a.url, "jefe.produccion", clave), cliente(a.url, "gerente.calidad", clave)
    meses = [f"{hoy.year}-{m:02d}" for m in range(inicio, hoy.month + 1)] if inicio <= hoy.month else []
    if not meses:
        sys.exit("El ejercicio fiscal actual empieza en otro año: use --inicio-ejercicio 1 para el ejemplo.")
    cargas = {}
    for i, periodo in enumerate(meses):
        for cod, _, _, _, _, _, variables, meta, limite, *_ in INDICADORES:
            valores = dict(zip((v[0] for v in variables), DATOS[cod][i], strict=True))
            cuerpo = {"indicador_id": ids[cod], "periodo": periodo, "valores": valores, "analisis": ANALISIS[0], "plan_mejora": ANALISIS[1]}
            cargas[(cod, periodo)] = exigir(jefe.post("/api/mediciones", json=cuerpo), f"Cargar {cod} {periodo}")
    # 3) Gerente: aprueba todo salvo el último mes; un mes se devuelve con observación y el jefe lo reenvía
    for (cod, periodo), m in cargas.items():
        if periodo == meses[-1]:
            continue
        if meses.index(periodo) == DEVUELTO and cod == "PRO-01":
            exigir(ger.post(f"/api/mediciones/{m['id']}/revision", json={"accion": "observar", "nota": "Confirme la producción real con el cierre de planta."}), "Devolver")
            valores = dict(zip((v[0] for v in INDICADORES[0][6]), DATOS[cod][DEVUELTO], strict=True))
            m = exigir(jefe.post("/api/mediciones", json={"indicador_id": ids[cod], "periodo": periodo, "valores": valores,
                                                          "analisis": ANALISIS[0], "plan_mejora": ANALISIS[1]}), "Reenviar")
        exigir(ger.post(f"/api/mediciones/{m['id']}/revision", json={"accion": "aprobar", "nota": ""}), "Aprobar")

    print(f"Ejemplo creado: área «{AREA}», 4 indicadores, {len(meses)} meses ({meses[0]} a {meses[-1]}).")
    print(f"  Jefe de área : jefe.produccion   Gerente: gerente.calidad   Contraseña: {clave}")
    print(f"  Queda pendiente de aprobación el mes {meses[-1]} (ingrese como gerente.calidad → Bandeja de aprobación).")


if __name__ == "__main__":
    main()
