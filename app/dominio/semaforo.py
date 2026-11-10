"""Semáforo de un indicador: clasifica un resultado según su nivel óptimo (zona verde) y su límite crítico.

«Mayor es mejor»: verde si resultado ≥ nivel óptimo; amarillo si ≥ límite; rojo en otro caso.
«Menor es mejor»: simétrico. Los topes opcionales acotan el otro extremo de cada franja
(equivalen a las columnas «Mín./Máx.» de la ficha en papel).
"""


def clasificar(valor: float, nivel_optimo: float, limite: float, sentido: str,
               nivel_optimo_tope: float | None = None, limite_tope: float | None = None) -> str:
    if sentido == "mayor":
        if valor >= nivel_optimo and (nivel_optimo_tope is None or valor <= nivel_optimo_tope):
            return "verde"
        return "amarillo" if valor >= limite and (limite_tope is None or valor <= limite_tope) else "rojo"
    if valor <= nivel_optimo and (nivel_optimo_tope is None or valor >= nivel_optimo_tope):
        return "verde"
    return "amarillo" if valor <= limite and (limite_tope is None or valor >= limite_tope) else "rojo"


def validar_umbrales(nivel_optimo: float, limite: float, sentido: str,
                     nivel_optimo_tope: float | None = None, limite_tope: float | None = None) -> None:
    """Comprueba que nivel óptimo, límite y topes sean coherentes con el sentido; lanza ValueError si no."""
    mayor = sentido == "mayor"
    if mayor and limite > nivel_optimo:
        raise ValueError("Con «mayor es mejor», el límite crítico debe ser ≤ el nivel óptimo.")
    if not mayor and limite < nivel_optimo:
        raise ValueError("Con «menor es mejor», el límite crítico debe ser ≥ el nivel óptimo.")
    if nivel_optimo_tope is not None and (nivel_optimo_tope < nivel_optimo if mayor else nivel_optimo_tope > nivel_optimo):
        raise ValueError("El tope de la zona verde debe quedar más allá del nivel óptimo.")
    if limite_tope is not None and (limite_tope < limite if mayor else limite_tope > limite):
        raise ValueError("El tope de la zona amarilla debe quedar más allá del límite crítico.")
