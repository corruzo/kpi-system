"""Errores de negocio. Los servicios los lanzan sin conocer HTTP; la API los traduce a respuestas JSON."""


class ErrorNegocio(Exception):
    """Base: una regla del sistema impide la operación. `estado` es el código HTTP equivalente."""
    estado = 400

    def __init__(self, detalle: str):
        super().__init__(detalle)
        self.detalle = detalle


class NoAutenticado(ErrorNegocio):
    estado = 401


class Prohibido(ErrorNegocio):
    estado = 403


class NoEncontrado(ErrorNegocio):
    estado = 404


class Conflicto(ErrorNegocio):
    """La operación choca con el estado actual (ya existe, ya fue procesado, ejercicio cerrado…)."""
    estado = 409


class Invalido(ErrorNegocio):
    """Los datos no cumplen las reglas del sistema."""
    estado = 422


class DemasiadosIntentos(ErrorNegocio):
    estado = 429


class Ocupado(ErrorNegocio):
    """El sistema está atendiendo otra escritura y no se pudo esperar más: conviene reintentar."""
    estado = 503
