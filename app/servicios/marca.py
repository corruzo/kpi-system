"""Logo de la empresa: se valida, se re-codifica como PNG (≤ 600 px) y se guarda en la base de datos."""
import base64
import hashlib
import io
import time

from sqlalchemy.orm import Session

from ..errores import Invalido
from ..models import Parametro, Usuario
from . import auditoria

MAX_BYTES = 600_000
LADO_MAXIMO = 600
_TIPOS = ("image/png", "image/jpeg", "image/webp")


_CACHE_SEGUNDOS = 60
_cache: dict = {"hasta": 0.0, "datos": None}


def _invalidar() -> None:
    _cache["hasta"] = 0.0


def bytes_logo(db: Session) -> bytes | None:
    """Logo en bytes. Se recuerda 60 s en memoria: es lo que más se pide (pantalla de ingreso) y casi nunca cambia."""
    if time.monotonic() < _cache["hasta"]:
        return _cache["datos"]
    fila = db.get(Parametro, "logo")
    datos = None
    if fila and fila.valor:
        try:
            datos = base64.b64decode(fila.valor.split(",", 1)[1])
        except Exception:
            datos = None
    _cache.update(hasta=time.monotonic() + _CACHE_SEGUNDOS, datos=datos)
    return datos


def url_logo(db: Session) -> str | None:
    """URL pública del logo, con una huella para que el navegador renueve su caché al cambiarlo."""
    datos = bytes_logo(db)
    return f"/api/logo?v={hashlib.sha256(datos).hexdigest()[:10]}" if datos else None


def _decodificar(data_url: str) -> bytes:
    if not data_url.startswith("data:image/") or "," not in data_url:
        raise Invalido("Formato no válido: suba una imagen PNG, JPG o WebP.")
    cabecera, b64 = data_url.split(",", 1)
    if not any(t in cabecera for t in _TIPOS):
        raise Invalido("Solo se admiten imágenes PNG, JPG o WebP.")
    try:
        crudo = base64.b64decode(b64, validate=True)
    except ValueError:
        raise Invalido("No se pudo leer la imagen: verifique que no esté dañada.") from None
    if len(crudo) > MAX_BYTES:
        raise Invalido("La imagen supera 600 KB.")
    return crudo


def _normalizar_png(crudo: bytes):
    """Reabre la imagen con Pillow y la vuelve a codificar: descarta metadatos y cualquier contenido activo."""
    from PIL import Image, UnidentifiedImageError
    try:
        Image.open(io.BytesIO(crudo)).verify()
        img = Image.open(io.BytesIO(crudo)).convert("RGBA")
    except (UnidentifiedImageError, OSError, ValueError):
        raise Invalido("No se pudo leer la imagen: verifique que no esté dañada.") from None
    img.thumbnail((LADO_MAXIMO, LADO_MAXIMO))
    salida = io.BytesIO()
    img.save(salida, "PNG", optimize=True)
    return salida.getvalue(), img.size


def guardar(db: Session, usuario: Usuario, data_url: str) -> str:
    png, (ancho, alto) = _normalizar_png(_decodificar(data_url))
    valor = "data:image/png;base64," + base64.b64encode(png).decode()
    fila = db.get(Parametro, "logo")
    if fila:
        fila.valor = valor
    else:
        db.add(Parametro(clave="logo", valor=valor))
    auditoria.registrar(db, usuario, "LOGO_ACTUALIZADO", "parametro", None, {"bytes": len(png), "ancho": ancho, "alto": alto})
    db.commit()
    _invalidar()
    return url_logo(db)


def quitar(db: Session, usuario: Usuario) -> None:
    fila = db.get(Parametro, "logo")
    if fila:
        db.delete(fila)
        auditoria.registrar(db, usuario, "LOGO_ELIMINADO", "parametro", None, {})
        db.commit()
    _invalidar()
