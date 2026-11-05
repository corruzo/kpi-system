"""SGC • TRIPOLIVEN · Sistema de Gestión de la Calidad — indicadores de gestión de Tripoliven, C.A.

Ensamblado de la aplicación: arranque diferido, cabeceras de seguridad, traducción de errores de negocio,
routers de la API y archivos estáticos. La lógica vive en `servicios/` y `dominio/`.
"""
import logging
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.exc import DataError, DBAPIError, IntegrityError, OperationalError
from sqlalchemy.orm import Session

from . import csrf
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


app = FastAPI(title="SGC • TRIPOLIVEN", lifespan=ciclo_de_vida,
              docs_url=None if PRODUCCION else "/docs", redoc_url=None,
              openapi_url=None if PRODUCCION else "/openapi.json")


@app.middleware("http")
async def asegurar_arranque_y_cabeceras(request: Request, call_next):
    if not arranque.esta_iniciado() and request.url.path != "/healthz":
        try:
            await run_in_threadpool(arranque.iniciar)
        except Exception as e:
            log.exception("Fallo al preparar la base de datos")
            return PlainTextResponse(f"SGC • TRIPOLIVEN no pudo preparar la base de datos.\n\n{arranque.motivo_del_fallo(e)}\n", status_code=503)
    if arranque.esta_iniciado() and request.url.path.startswith("/api/"):
        await run_in_threadpool(parametros.refrescar)
    respuesta = await call_next(request)
    respuesta.headers.update(CABECERAS_DE_SEGURIDAD)
    if PRODUCCION:
        respuesta.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if request.url.path.startswith("/api/"):
        respuesta.headers["Cache-Control"] = "no-store"
    return respuesta


@app.middleware("http")   # se registra después: es la capa más externa y corta la petición antes de cualquier trabajo
async def rechazar_peticiones_de_otro_origen(request: Request, call_next):
    if not csrf.peticion_legitima(request):
        return JSONResponse({"detail": "Petición rechazada: origen no permitido."}, status_code=403)
    return await call_next(request)


@app.exception_handler(ErrorNegocio)
async def responder_error_de_negocio(_, e: ErrorNegocio):
    return JSONResponse({"detail": e.detalle}, status_code=e.estado)


@app.exception_handler(RequestValidationError)
async def responder_entrada_invalida(_, e: RequestValidationError):
    """Igual que la respuesta 422 de FastAPI, pero sin `input` ni `ctx`: devolver un NaN/Infinity enviado por el cliente
    haría fallar la serialización a JSON (500), y reflejar la entrada tampoco aporta nada."""
    errores = [{"type": x["type"], "loc": list(x["loc"]), "msg": x["msg"]} for x in e.errors()]
    return JSONResponse({"detail": errores}, status_code=422)


# ---------------------------------------------------------------- errores inesperados: siempre una respuesta JSON clara
@app.exception_handler(IntegrityError)
async def responder_conflicto_de_datos(_, e: IntegrityError):
    """Dos peticiones simultáneas que chocan con una restricción única o de llave foránea: es un conflicto, no un fallo."""
    log.warning("Restricción de base de datos: %s", str(getattr(e, "orig", e)).splitlines()[0][:200])
    return JSONResponse({"detail": "La operación choca con datos que ya existen o están en uso. Actualice la pantalla e intente de nuevo."},
                        status_code=409)


@app.exception_handler(DataError)
@app.exception_handler(OverflowError)
async def responder_valor_fuera_de_rango(_, e: Exception):
    log.warning("Valor fuera de rango: %s", type(e).__name__)
    return JSONResponse({"detail": "Algún valor enviado está fuera del rango permitido."}, status_code=422)


@app.exception_handler(OperationalError)
@app.exception_handler(DBAPIError)
async def responder_base_no_disponible(_, e: DBAPIError):
    log.error("Base de datos no disponible: %s", str(getattr(e, "orig", e)).splitlines()[0][:200])
    return JSONResponse({"detail": "La base de datos no responde en este momento. Intente de nuevo en unos segundos."}, status_code=503)


@app.exception_handler(Exception)
async def responder_error_interno(request: Request, e: Exception):
    """Último recurso: se registra con un código y el usuario recibe ese código (nunca el detalle técnico)."""
    codigo = secrets.token_hex(4).upper()
    log.error("Error interno %s en %s %s", codigo, request.method, request.url.path, exc_info=e)
    return JSONResponse({"detail": f"Error interno del sistema. Informe este código al administrador: {codigo}."}, status_code=500)


for router in ROUTERS:
    app.include_router(router)


@app.get("/healthz", include_in_schema=False)
def salud(db: Session = Depends(get_db)):
    try:
        db.execute(select(1))
    except DBAPIError:
        return JSONResponse({"ok": False}, status_code=503)   # el balanceador debe retirar esta instancia
    return {"ok": True}


app.mount("/static", StaticFiles(directory=ESTATICOS), name="static")


@app.get("/", include_in_schema=False)
def inicio():
    return HTMLResponse(pagina_principal(), headers={"Cache-Control": "no-cache"})
