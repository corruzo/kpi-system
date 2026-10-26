"""Punto de entrada para Vercel (función serverless de Python)."""
import logging

try:
    from app.main import app as _sigt
    _detalle = None
except Exception as e:  # el arranque falló: mostrar un diagnóstico legible en vez de un 500 opaco
    logging.exception("Fallo al iniciar SIGT")
    _sigt = None
    # Solo se muestran errores de configuración propios; el resto queda en los Logs de Vercel.
    _detalle = f"{type(e).__name__}: {e}" if isinstance(e, (RuntimeError, ImportError)) else \
        f"{type(e).__name__} (vea Deployments → Logs para el detalle)"


async def app(scope, receive, send):
    if _sigt is not None:
        return await _sigt(scope, receive, send)
    if scope["type"] != "http":
        return
    cuerpo = f"SIGT no pudo iniciar.\n\n{_detalle}\n".encode()
    await send({"type": "http.response.start", "status": 503,
                "headers": [(b"content-type", b"text/plain; charset=utf-8")]})
    await send({"type": "http.response.body", "body": cuerpo})
