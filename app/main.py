"""SIGT · Sistema de Indicadores de Gestión — Tripoliven, C.A.

Ensamblado de la aplicación: arranque diferido, cabeceras de seguridad, traducción de errores de negocio,
routers de la API y archivos estáticos. La lógica vive en `servicios/` y `dominio/`.
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session

from .api.deps import get_db
from .api.routers import ROUTERS
from .config import PRODUCCION
from .errores import ErrorNegocio
from .plantilla import pagina_principal
from .servicios import arranque, parametros

log = logging.getLogger("sigt")
ESTATICOS = Path(__file__).parent / "static"

CSP = ("default-src 'self'; script-src 'self' 'unsafe-eval' 'unsafe-inline'; "
       "style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; "
       "frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
CABECERAS_DE_SEGURIDAD = {"X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY", "Referrer-Policy": "same-origin",
                          "Content-Security-Policy": CSP, "Permissions-Policy": "camera=(), microphone=(), geolocation=()"}


@asynccontextmanager
async def ciclo_de_vida(_):
    try:
        arranque.iniciar()
    except Exception:  # no tumbar el proceso: se reintenta en la primera petición y se muestra el motivo
        log.exception("Fallo al preparar la base de datos")
    yield


app = FastAPI(title="SIGT Tripoliven", lifespan=ciclo_de_vida,
              docs_url=None if PRODUCCION else "/docs", redoc_url=None,
              openapi_url=None if PRODUCCION else "/openapi.json")


@app.middleware("http")
async def asegurar_arranque_y_cabeceras(request: Request, call_next):
    if not arranque.esta_iniciado() and request.url.path != "/healthz":
        try:
            await run_in_threadpool(arranque.iniciar)
        except Exception as e:
            log.exception("Fallo al preparar la base de datos")
            return PlainTextResponse(f"SIGT no pudo preparar la base de datos.\n\n{arranque.motivo_del_fallo(e)}\n", status_code=503)
    if arranque.esta_iniciado() and request.url.path.startswith("/api/"):
        await run_in_threadpool(parametros.refrescar)
    respuesta = await call_next(request)
    respuesta.headers.update(CABECERAS_DE_SEGURIDAD)
    if PRODUCCION:
        respuesta.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if request.url.path.startswith("/api/"):
        respuesta.headers["Cache-Control"] = "no-store"
    return respuesta


@app.exception_handler(ErrorNegocio)
async def responder_error_de_negocio(_, e: ErrorNegocio):
    return JSONResponse({"detail": e.detalle}, status_code=e.estado)


for router in ROUTERS:
    app.include_router(router)


@app.get("/healthz", include_in_schema=False)
def salud(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {"ok": True}


app.mount("/static", StaticFiles(directory=ESTATICOS), name="static")


@app.get("/", include_in_schema=False)
def inicio():
    return HTMLResponse(pagina_principal(), headers={"Cache-Control": "no-cache"})
