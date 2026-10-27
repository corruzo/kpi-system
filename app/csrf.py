"""Protección CSRF sin tokens: en peticiones que modifican datos se exige que el navegador declare un origen propio.

Los navegadores envían siempre `Origin` (y `Sec-Fetch-Site`) en POST/PUT/PATCH/DELETE entre sitios y el atacante no puede
falsificarlos. Las peticiones sin ninguna de las dos cabeceras no vienen de un navegador (curl, pruebas, otros servicios)
y no pueden aprovechar la cookie de sesión de la víctima, por lo que se permiten.
"""
from urllib.parse import urlsplit

from fastapi import Request

from .config import TRUST_PROXY

METODOS_SEGUROS = {"GET", "HEAD", "OPTIONS"}
_SITIOS_PROPIOS = {"same-origin", "none"}   # «none»: acción directa del usuario (p. ej. barra de direcciones)


def _hosts_propios(request: Request) -> set[str]:
    hosts = {request.headers.get("host", "").lower()}
    if TRUST_PROXY and request.headers.get("x-forwarded-host"):
        hosts.add(request.headers["x-forwarded-host"].split(",")[0].strip().lower())
    return hosts - {""}


def peticion_legitima(request: Request) -> bool:
    """False si la petición modificadora viene de otro origen según `Sec-Fetch-Site` u `Origin`."""
    if request.method in METODOS_SEGUROS:
        return True
    sitio = request.headers.get("sec-fetch-site")
    if sitio is not None and sitio.lower() not in _SITIOS_PROPIOS:
        return False
    origen = request.headers.get("origin")
    if origen is not None:
        return urlsplit(origen).netloc.lower() in _hosts_propios(request)   # «null» y orígenes ajenos no coinciden
    return True
