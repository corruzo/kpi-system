"""Genera `docs/PERMISOS.md` a partir del catálogo (`permisos.py`) y de las rutas reales de la API.

    python -m app.permisos_doc          # reescribe docs/PERMISOS.md

Una prueba (`tests/test_permisos_doc.py`) compara el archivo con lo que este módulo genera: si cambia el catálogo o se
declara otro permiso en una ruta, la documentación deja de coincidir y la prueba falla hasta regenerarla.
"""
from pathlib import Path

from . import permisos as cat

DESTINO = Path(__file__).resolve().parent.parent / "docs" / "PERMISOS.md"
PUBLICAS = {"/api/login", "/api/logout", "/api/publico", "/api/logo"}


def _llamadas(dependant):
    for d in dependant.dependencies:
        yield d.call
        yield from _llamadas(d)


def declaracion(ruta):
    """Permisos exigidos por una ruta (conjunto), 'cuenta' (cualquier sesión válida), 'publica' o None (sin declarar)."""
    llamadas = list(_llamadas(ruta.dependant))
    declarados = [set(c.permisos) for c in llamadas if hasattr(c, "permisos")]
    if declarados:
        return set.intersection(*declarados)
    if any(getattr(c, "propia", False) for c in llamadas):
        return "cuenta"
    return "publica" if ruta.path in PUBLICAS else None


def rutas_por_permiso() -> dict[str, list[str]]:
    from .api.routers import ROUTERS
    salida: dict[str, list[str]] = {}
    for router in ROUTERS:
        for ruta in router.routes:
            d = declaracion(ruta) if ruta.path.startswith("/api/") else None
            if isinstance(d, set):
                for metodo in sorted(ruta.methods - {"HEAD", "OPTIONS"}):
                    for codigo in d:
                        salida.setdefault(codigo, []).append(f"{metodo} {ruta.path}")
    return {k: sorted(v) for k, v in salida.items()}


def _niveles(p: cat.Permiso) -> str:
    return "Ninguno / Ver" if p.niveles == (cat.VER,) else ("Ninguno / Sí" if p.niveles == (cat.MODIFICAR,) else "Ninguno / Ver / Ver y modificar")


def generar() -> str:
    rutas = rutas_por_permiso()
    lineas = ["# Catálogo de permisos de SPE TPV", "",
         "> Documento **generado** desde `app/permisos.py` y las rutas de la API (`python -m app.permisos_doc`). "
         "Una prueba automática verifica que coincida con el código: no se edita a mano.", "",
         "El Coordinador SGC solo elige el **nivel** de cada permiso para un rol; el **alcance** es fijo y lo aplica siempre el motor "
         "(`app/servicios/acceso.py`). «Ver y modificar» incluye «Ver». Lo que no se puede ver responde **404**; lo que se ve pero no se puede "
         "hacer, **403**.", "", "## Reglas del motor (no configurables)", "",
         "- **Visible** = el nodo del indicador está dentro de algún ámbito de la persona, **o** es su responsable, **o** es su cargador, **o** "
         "la persona tiene alcance global (Desarrollador, Coordinador SGC o ámbito en la raíz de la empresa). La visibilidad solo baja por el árbol.",
         "- **Modificar** una ficha (editar, archivar, eliminar): solo su responsable. **Cargar** datos: solo sus cargadores. "
         "Los roles de sistema tienen alcance total.",
         "- **Crear / asignar indicadores y fijar metas**: a sí mismo o a personas que están **debajo** en la estructura.",
         "- **Aprobar**: el superior más cercano hacia arriba que tenga el permiso `cargas.aprobar` y sea distinto del autor; si hay varios en "
         "ese nivel, cualquiera. El Coordinador SGC es respaldo. Nadie aprueba una carga propia.",
         "- **Anti-escalada**: nadie edita su propio rol, nadie concede un permiso que no tiene y los permisos técnicos no se conceden a ningún rol.",
         "- **Usuario nuevo = sin acceso** hasta que el Coordinador SGC le asigne rol, ámbito e indicadores.", "",
         "## Roles de sistema", "",
         "| Rol | Qué es |", "|---|---|",
         "| **Desarrollador** | Todo, incluido lo técnico. Inmutable: no se edita, no se borra, no se le quitan permisos. El sistema nunca queda sin uno activo. |",
         "| **Coordinador SGC** | Todo lo funcional, nada técnico. Define roles y asigna personas. No toca a un Desarrollador ni cambia su propio rol. |", ""]
    for grupo in cat.GRUPOS:
        items = [p for p in cat.CATALOGO if p.grupo == grupo]
        lineas += [f"## {grupo}" + (" (solo Desarrollador)" if items[0].tecnico else ""), "",
              "| Permiso | Función | Niveles | Alcance | Rutas |", "|---|---|---|---|---|"]
        for p in items:
            r = "<br>".join(f"`{x}`" for x in rutas.get(p.codigo, [])) or "—"
            lineas.append(f"| `{p.codigo}` | **{p.etiqueta}**: {p.descripcion} | {_niveles(p)} | {p.alcance} | {r} |")
        lineas.append("")
    lineas += ["## Cuenta propia (todos los usuarios con sesión, no configurable)", "",
          *[f"- {x}" for x in cat.CUENTA_PROPIA], "",
          "Rutas: `GET /api/me`, `POST /api/cambiar-clave`, `POST /api/tour`, `GET /api/arranque` (una cuenta sin rol solo recibe su perfil). "
          "Públicas (sin sesión): `POST /api/login`, `POST /api/logout`, `GET /api/publico`, `GET /api/logo`.", "",
          "## Permisos mínimos del Coordinador SGC", "",
          "Su rol nunca puede quedar sin: " + ", ".join(f"`{c}`" for c in cat.MINIMOS_DEL_COORDINADOR) + ".", ""]
    return "\n".join(lineas)


if __name__ == "__main__":
    DESTINO.write_text(generar(), encoding="utf-8")
    print(f"Escrito {DESTINO}")
