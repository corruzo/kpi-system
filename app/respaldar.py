"""Herramienta de línea de comandos para respaldar y restaurar la base.

    SIGT_BACKUP_KEY='frase de paso larga' python -m app.respaldar crear [--salida carpeta]
    SIGT_BACKUP_KEY=... python -m app.respaldar verificar archivo.sigtbak
    SIGT_BACKUP_KEY=... python -m app.respaldar restaurar archivo.sigtbak     # solo en una base recién migrada y vacía

Usa la misma base que la aplicación (SIGT_DATABASE_URL / SQLite local). Sin SIGT_BACKUP_KEY pide la frase por teclado.
"""
import argparse
import getpass
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from .database import SessionLocal
from .errores import ErrorNegocio
from .servicios import respaldo


def _frase(confirmar: bool = False) -> str:
    frase = os.getenv("SIGT_BACKUP_KEY") or getpass.getpass("Frase de paso del respaldo: ")
    if confirmar and not os.getenv("SIGT_BACKUP_KEY") and getpass.getpass("Repita la frase: ") != frase:
        raise SystemExit("Las frases no coinciden.")
    return frase


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m app.respaldar", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="orden", required=True)
    c = sub.add_parser("crear")
    c.add_argument("--salida", default="respaldos", help="carpeta de destino (por defecto ./respaldos)")
    sub.add_parser("verificar").add_argument("archivo")
    sub.add_parser("restaurar").add_argument("archivo")
    a = ap.parse_args(argv)
    try:
        if a.orden == "crear":
            frase = _frase(confirmar=True)
            with SessionLocal() as db:
                datos, resumen = respaldo.crear(db, frase)
            destino = Path(a.salida)
            destino.mkdir(parents=True, exist_ok=True)
            ruta = destino / f"sigt-respaldo-{datetime.now(UTC):%Y%m%d-%H%M%S}.sigtbak"
            ruta.write_bytes(datos)
            ruta.chmod(0o600)
            print(f"Respaldo creado: {ruta} ({resumen['bytes']} bytes, sha256 {resumen['sha256_archivo'][:16]}…)")
            print("Filas por tabla:", ", ".join(f"{n}={v}" for n, v in resumen["tablas"].items()))
            return 0
        datos = Path(a.archivo).read_bytes()
        if a.orden == "verificar":
            r = respaldo.verificar(datos, _frase())
            print(f"Respaldo íntegro ({r['creado']}, revisión {r['alembic']}, bitácora {'válida' if r['bitacora_ok'] else 'CON ERRORES al respaldar'}).")
            return 0
        with SessionLocal() as db:
            r = respaldo.restaurar(db, datos, _frase())
        print(f"Restaurado. Bitácora verificada: {r['bitacora']['total']} registros, ok={r['bitacora']['ok']}.")
        return 0
    except ErrorNegocio as e:
        print(f"ERROR: {e.detalle}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
