"""Routers de la API, en el orden lógico de uso del sistema."""
from . import (
    arranque,
    bitacora,
    ejercicios,
    estructura,
    importacion,
    indicadores,
    mediciones,
    metas,
    organizacion,
    personas,
    recordatorios,
    reportes,
    sesion,
    sistema,
    tablero,
)

# Quién entra → cómo se organiza la empresa y quién puede qué → qué se mide → cada carga → cómo se agrupa por año → qué se espera → qué se obtiene
ROUTERS = [sesion.router, arranque.router, estructura.router, personas.router, organizacion.router, indicadores.router, mediciones.router,
           recordatorios.router, ejercicios.router, metas.router, tablero.router, reportes.router, importacion.router, bitacora.router, sistema.router]
