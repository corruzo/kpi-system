"""Meta de un indicador: reparto de un valor anual entre los períodos y comparación del resultado real.

Funciones puras (sin BD ni HTTP).
"""

REPARTOS = ("igual", "repetir")


def repartir(valor: float, n: int, modo: str, decimales: int = 6) -> list[float]:
    """Valor anual → un valor por período.

    «igual»: el total se divide en partes iguales (sumas: toneladas, ventas, dólares).
    «repetir»: cada período lleva el mismo valor (razones: porcentajes, promedios, tiempos)."""
    if n < 1:
        raise ValueError("Debe haber al menos un período.")
    if modo == "igual":
        return [round(valor / n, decimales)] * n
    if modo == "repetir":
        return [valor] * n
    raise ValueError("Reparto no válido.")


def comparar(resultado: float, meta: float | None, sentido: str) -> dict | None:
    """Real contra meta. None si el período no tenía meta.

    `desviacion` = real − meta; `porcentaje` = real / meta (None si la meta es 0);
    `cumple` = se alcanzó o superó la meta en el sentido del indicador (mayor o menor es mejor)."""
    if meta is None:
        return None
    desviacion = round(resultado - meta, 6)
    porcentaje = round(100 * resultado / meta, 1) if meta else None
    cumple = resultado >= meta if sentido == "mayor" else resultado <= meta
    return {"meta": meta, "desviacion": desviacion, "porcentaje": porcentaje, "cumple": cumple}
