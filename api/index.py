"""Punto de entrada para Vercel (función serverless de Python)."""
import logging

try:
    from app.main import app  # noqa: F401
except Exception as e:  # el arranque falló: mostrar un diagnóstico legible en vez de un 500 opaco
    logging.exception("Fallo al iniciar SIGT")
    # Solo se muestran errores de configuración propios; el resto queda en los Logs de Vercel.
    detalle = f"{type(e).__name__}: {e}" if isinstance(e, (RuntimeError, ImportError)) else \
        f"{type(e).__name__} (vea Deployments → Logs para el detalle)"

    async def app(scope, receive, send):
        if scope["type"] != "http":
            return
        cuerpo = f"SIGT no pudo iniciar.\n\n{detalle}\n".encode()
        await send({"type": "http.response.start", "status": 503,
                    "headers": [(b"content-type", b"text/plain; charset=utf-8")]})
        await send({"type": "http.response.body", "body": cuerpo})
