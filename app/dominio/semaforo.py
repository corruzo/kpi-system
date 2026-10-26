"""Semáforo de un indicador: clasifica un resultado según su meta (zona verde) y su límite crítico.

«Mayor es mejor»: verde si resultado ≥ meta; amarillo si ≥ límite; rojo en otro caso.
«Menor es mejor»: simétrico. Los topes opcionales acotan el otro extremo de cada franja
(equivalen a las columnas «Mín./Máx.» de la ficha en papel).
"""


def clasificar(valor: float, meta: float, limite: float, sentido: str,
               meta_tope: float | None = None, limite_tope: float | None = None) -> str:
    if sentido == "mayor":
        if valor >= meta and (meta_tope is None or valor <= meta_tope):
            return "verde"
        return "amarillo" if valor >= limite and (limite_tope is None or valor <= limite_tope) else "rojo"
    if valor <= meta and (meta_tope is None or valor >= meta_tope):
        return "verde"
    return "amarillo" if valor <= limite and (limite_tope is None or valor >= limite_tope) else "rojo"


def validar_umbrales(meta: float, limite: float, sentido: str,
                     meta_tope: float | None = None, limite_tope: float | None = None) -> None:
    """Comprueba que meta, límite y topes sean coherentes con el sentido; lanza ValueError si no."""
    mayor = sentido == "mayor"
    if mayor and limite > meta:
        raise ValueError("Con «mayor es mejor», el límite crítico debe ser ≤ la meta.")
    if not mayor and limite < meta:
        raise ValueError("Con «menor es mejor», el límite crítico debe ser ≥ la meta.")
    if meta_tope is not None and (meta_tope < meta if mayor else meta_tope > meta):
        raise ValueError("El tope de la zona verde debe quedar más allá de la meta.")
    if limite_tope is not None and (limite_tope < limite if mayor else limite_tope > limite):
        raise ValueError("El tope de la zona amarilla debe quedar más allá del límite crítico.")
