"""Routers de la API, en el orden lógico de uso del sistema."""
from . import bitacora, ejercicios, importacion, indicadores, mediciones, organizacion, reportes, sesion

# Quién entra → cómo se organiza la empresa → qué se mide → cada carga → cómo se agrupa por año → qué se obtiene
ROUTERS = [sesion.router, organizacion.router, indicadores.router, mediciones.router, ejercicios.router,
           reportes.router, importacion.router, bitacora.router]
