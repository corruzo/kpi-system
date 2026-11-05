"""Presupuesto de un indicador: reparto de un valor anual entre los períodos y comparación del resultado real.

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


def comparar(resultado: float, presupuesto: float | None, sentido: str) -> dict | None:
    """Real contra presupuesto. None si el período no tenía presupuesto.

    `desviacion` = real − presupuesto; `porcentaje` = real / presupuesto (None si el presupuesto es 0);
    `cumple` = se alcanzó o superó el presupuesto en el sentido del indicador (mayor o menor es mejor)."""
    if presupuesto is None:
        return None
    desviacion = round(resultado - presupuesto, 6)
    porcentaje = round(100 * resultado / presupuesto, 1) if presupuesto else None
    cumple = resultado >= presupuesto if sentido == "mayor" else resultado <= presupuesto
    return {"presupuesto": presupuesto, "desviacion": desviacion, "porcentaje": porcentaje, "cumple": cumple}
