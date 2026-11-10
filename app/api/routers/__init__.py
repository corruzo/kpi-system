"""Routers de la API, en el orden lógico de uso del sistema."""
from . import (
           arranque,
           bitacora,
           ejercicios,
           importacion,
           indicadores,
           mediciones,
           metas,
           organizacion,
           recordatorios,
           reportes,
           sesion,
           tablero,
)

# Quién entra → cómo se organiza la empresa → qué se mide → cada carga → cómo se agrupa por año → cuánto se espera lograr → qué se obtiene
ROUTERS = [sesion.router, arranque.router, organizacion.router, indicadores.router, mediciones.router, recordatorios.router, ejercicios.router,
           metas.router, tablero.router, reportes.router, importacion.router, bitacora.router]
