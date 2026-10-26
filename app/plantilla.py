"""Composición de la página principal: index.html + parciales/ (vistas y componentes).

El HTML se divide en archivos pequeños —una vista o ventana por archivo— que `index.html` incluye con
`<!--#incluir parciales/xxx.html-->`. La página se ensambla en el servidor, así que el navegador recibe un solo documento.
"""
import re
from pathlib import Path

from .config import PRODUCCION

BASE = Path(__file__).parent / "static"
_INCLUIR = re.compile(r"<!--#incluir ([\w./-]+)-->")
_cache: str | None = None


def _expandir(texto: str, profundidad: int = 0) -> str:
    if profundidad > 3:
        raise RuntimeError("Inclusiones anidadas en exceso.")

    def sustituir(m: re.Match) -> str:
        ruta = (BASE / m.group(1)).resolve()
        if BASE.resolve() not in ruta.parents or ruta.suffix != ".html":   # solo archivos .html bajo static/
            raise RuntimeError(f"Inclusión no permitida: {m.group(1)}")
        return _expandir(ruta.read_text(encoding="utf-8"), profundidad + 1)

    return _INCLUIR.sub(sustituir, texto)


def pagina_principal() -> str:
    """HTML completo. En producción se arma una vez; en desarrollo se relee para ver los cambios al recargar."""
    global _cache
    if PRODUCCION and _cache is not None:
        return _cache
    html = _expandir((BASE / "index.html").read_text(encoding="utf-8"))
    if PRODUCCION:
        _cache = html
    return html
