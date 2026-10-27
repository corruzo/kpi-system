"""Inspección previa de archivos .xlsx (un .xlsx es un zip): evita «zip bombs» antes de que openpyxl los descomprima."""
import io
import zipfile

MAX_DESCOMPRIMIDO = 50 * 1024 * 1024   # suma de los tamaños descomprimidos
MAX_ENTRADAS = 1000                    # archivos dentro del zip


def validar_xlsx(contenido: bytes) -> None:
    """ValueError si no es un zip legible o si su contenido descomprimido excede los límites.
    Los tamaños salen del directorio central del zip; `zipfile` nunca entrega más bytes de los declarados."""
    try:
        with zipfile.ZipFile(io.BytesIO(contenido)) as z:
            entradas = z.infolist()
    except (zipfile.BadZipFile, ValueError, OSError):
        raise ValueError("No se pudo leer el archivo: debe ser un libro de Excel (.xlsx).") from None
    if len(entradas) > MAX_ENTRADAS:
        raise ValueError("El archivo tiene demasiadas partes internas para ser un libro de Excel válido.")
    if sum(e.file_size for e in entradas) > MAX_DESCOMPRIMIDO:
        raise ValueError("El archivo ocupa demasiado al descomprimirse (máximo 50 MB).")
