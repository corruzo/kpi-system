"""Catálogo de permisos: la ÚNICA fuente de lo que se puede autorizar en el sistema.

Cada función (ruta de la API) declara uno de estos permisos con `requiere_permiso` (ver `api/deps.py`); una prueba
comprueba que no quede ninguna ruta sin declarar ni ningún permiso sin usar, y `docs/PERMISOS.md` se valida contra esta lista.

- `niveles`: qué puede elegir el Coordinador para ese permiso. («ver»,) o («modificar»,) se muestran como «Ninguno / Sí»;
  («ver», «modificar») como «Ninguno / Ver / Ver y modificar». «Modificar» incluye «ver».
- `alcance`: sobre qué datos actúa. NO es editable: lo aplica siempre el motor (`servicios/acceso.py`).
- `tecnico`: solo existe para el rol Desarrollador; nunca se ofrece ni se concede a otro rol.
- `implica`: permisos sin los cuales este no sirve; se conceden junto con él al guardar el rol.
"""
from dataclasses import dataclass

VER, MODIFICAR = "ver", "modificar"
ORDEN = {VER: 1, MODIFICAR: 2}

A_VISIBLES = "Los indicadores de su ámbito (su nodo y lo que cuelga de él) y los que tiene asignados."
A_PROPIOS = "Solo los indicadores de los que es responsable."
A_DEBAJO = "A sí mismo o a personas que están debajo de él en la estructura."
A_GLOBAL = "Toda la empresa."


@dataclass(frozen=True)
class Permiso:
    codigo: str
    grupo: str
    etiqueta: str
    descripcion: str
    alcance: str
    niveles: tuple[str, ...] = (MODIFICAR,)
    tecnico: bool = False
    implica: tuple[str, ...] = ()

    @property
    def minimo(self) -> str:
        return self.niveles[0]


def _p(codigo, grupo, etiqueta, descripcion, alcance, niveles=(MODIFICAR,), tecnico=False, implica=()):
    return Permiso(codigo, grupo, etiqueta, descripcion, alcance, niveles, tecnico, implica)


_V = (VER,)
CATALOGO: tuple[Permiso, ...] = (
    # ------------------------------------------------------------ Indicadores
    _p("indicadores.ver", "Indicadores", "Ver indicadores", "Consultar la lista de indicadores y su ficha técnica.", A_VISIBLES, _V,
       implica=("ejercicios.ver",)),
    _p("indicadores.crear", "Indicadores", "Crear indicadores",
       "Crear fichas nuevas (el código lo asigna el sistema) y definir su nodo, responsable y quienes cargan.", A_DEBAJO,
       implica=("indicadores.ver",)),
    _p("indicadores.editar", "Indicadores", "Editar indicadores", "Cambiar la ficha: fórmula, variables, semáforo y textos.", A_PROPIOS,
       implica=("indicadores.ver",)),
    _p("indicadores.archivar", "Indicadores", "Archivar y restaurar", "Archivar un indicador (conserva su historial) o restaurarlo.",
       A_PROPIOS, implica=("indicadores.ver",)),
    _p("indicadores.eliminar", "Indicadores", "Eliminar indicadores", "Borrar definitivamente un indicador que no tiene cargas.",
       A_PROPIOS, implica=("indicadores.ver",)),
    _p("indicadores.asignar", "Indicadores", "Asignar responsable y cargadores",
       "Cambiar el nodo, el responsable y las personas que cargan un indicador de su ámbito o propio.", A_DEBAJO,
       implica=("indicadores.ver",)),
    _p("formulas.probar", "Indicadores", "Validar y probar fórmulas", "Usar el validador y el probador de fórmulas de la ficha.",
       "No accede a datos."),
    # ------------------------------------------------------------ Cargas
    _p("cargas.ver", "Cargas", "Ver cargas", "Consultar el historial de cargas, sus períodos y su estado.", A_VISIBLES, _V,
       implica=("indicadores.ver",)),
    _p("cargas.cargar", "Cargas", "Cargar datos", "Digitar el dato real de cada período y corregir las cargas devueltas.",
       "Solo los indicadores en los que es cargador.", implica=("cargas.ver",)),
    _p("cargas.reabrir", "Cargas", "Reabrir cargas aprobadas", "Devolver a quien cargó una carga ya aprobada, con su motivo.",
       "Las cargas que le corresponde aprobar.", implica=("cargas.ver",)),
    _p("cargas.notas", "Cargas", "Notas de auditoría", "Agregar notas de auditoría a una carga.", A_VISIBLES, implica=("cargas.ver",)),
    # ------------------------------------------------------------ Aprobación
    _p("cargas.aprobar", "Aprobación", "Aprobar o devolver cargas",
       "Revisar las cargas enviadas: aprobarlas o devolverlas con observaciones. Nadie aprueba una carga propia.",
       "Las cargas de su ámbito, como superior más cercano de quien cargó (el Coordinador SGC puede aprobar siempre).",
       implica=("cargas.ver",)),
    # ------------------------------------------------------------ Metas
    _p("metas.ver", "Metas", "Ver metas", "Consultar la meta de cada indicador por período.", A_VISIBLES, _V, implica=("indicadores.ver",)),
    _p("metas.cargar", "Metas", "Cargar metas", "Ingresar o cambiar la meta por período o anual repartida.",
       "Sus indicadores y los de quienes están debajo de él.", implica=("metas.ver",)),
    _p("metas.copiar", "Metas", "Copiar metas de otro ejercicio", "Copiar las metas de otro ejercicio a los indicadores que aún no las tienen.",
       "Sus indicadores y los de quienes están debajo de él.", implica=("metas.cargar",)),
    # ------------------------------------------------------------ Ejercicios
    _p("ejercicios.ver", "Ejercicios", "Ver ejercicios fiscales", "Ver los ejercicios fiscales y su estado (los resultados, solo de lo visible).",
       A_GLOBAL, _V),
    _p("ejercicios.crear", "Ejercicios", "Crear ejercicios", "Abrir un período fiscal para fijar metas y cargar datos.", A_GLOBAL,
       implica=("ejercicios.ver",)),
    _p("ejercicios.cerrar", "Ejercicios", "Cerrar ejercicios", "Verificar y cerrar un ejercicio terminado (queda de solo lectura).", A_GLOBAL,
       implica=("ejercicios.ver",)),
    _p("ejercicios.reabrir", "Ejercicios", "Reabrir ejercicios", "Reabrir un ejercicio cerrado, con su motivo.", A_GLOBAL,
       implica=("ejercicios.ver",)),
    # ------------------------------------------------------------ Análisis
    _p("panel.ver", "Análisis", "Panel de control", "Resultados, tendencias, mapa de calor y puntualidad.", A_VISIBLES, _V,
       implica=("cargas.ver",)),
    _p("reportes.general", "Análisis", "Reporte general en Excel", "Descargar el informe «Real vs Meta».", A_VISIBLES, _V,
       implica=("cargas.ver",)),
    _p("reportes.fichas", "Análisis", "Fichas técnicas en Excel", "Descargar las fichas técnicas en el formato NC-16.", A_VISIBLES, _V,
       implica=("indicadores.ver",)),
    _p("reportes.verificar", "Análisis", "Verificar reportes", "Comprobar que un Excel emitido por el sistema no fue modificado.",
       "Cualquier reporte emitido por el sistema.", _V),
    # ------------------------------------------------------------ Recordatorios
    _p("recordatorios.enviar", "Recordatorios", "Recordatorios de carga",
       "Ver quién tiene cargas pendientes y avisarle por correo (Outlook).", "Solo personas que cargan indicadores de su ámbito.",
       implica=("indicadores.ver",)),
    # ------------------------------------------------------------ Estructura
    _p("estructura.ver", "Estructura", "Ver la estructura", "Ver el árbol de gerencias, departamentos y jefaturas.", A_GLOBAL, _V),
    _p("estructura.gestionar", "Estructura", "Gestionar la estructura", "Crear, renombrar, mover y eliminar nodos del árbol.", A_GLOBAL,
       implica=("estructura.ver",)),
    _p("catalogos.gestionar", "Estructura", "Listas de apoyo", "Mantener las listas de la ficha: procesos, objetivos, gerencias y cargos.",
       A_GLOBAL),
    _p("parametros.gestionar", "Estructura", "Parámetros y logo",
       "Empresa, código del formato, inicio del ejercicio fiscal, protección de reportes y logo.", A_GLOBAL),
    _p("importacion.usar", "Estructura", "Importar planillas NC-16", "Traer fichas históricas desde Excel (crea indicadores y cargas aprobadas).",
       A_GLOBAL, implica=("indicadores.ver",)),
    # ------------------------------------------------------------ Personas
    _p("usuarios.ver", "Personas", "Ver personas", "Ver las personas, su rol, su ámbito y lo que alcanzan a ver.",
       "Todas las personas, salvo los Desarrolladores.", _V, implica=("estructura.ver",)),
    _p("usuarios.asignar", "Personas", "Asignar rol, ámbito e indicadores",
       "Dar a cada persona su rol, su posición en la estructura y sus indicadores.", "Todas las personas, salvo los Desarrolladores y uno mismo.",
       implica=("usuarios.ver",)),
    _p("roles.gestionar", "Personas", "Roles y permisos", "Crear, renombrar, duplicar y borrar roles, y elegir sus permisos.",
       "Todos los roles, salvo el propio y el de Desarrollador.", implica=("usuarios.ver",)),
    # ------------------------------------------------------------ Técnico (solo Desarrollador)
    _p("bitacora.ver", "Técnico", "Ver la bitácora", "Consultar la bitácora inalterable y verificar su cadena.", A_GLOBAL, _V, tecnico=True),
    _p("bitacora.exportar", "Técnico", "Exportar la bitácora", "Descargar la bitácora en Excel.", A_GLOBAL, _V, tecnico=True),
    _p("usuarios.cuentas", "Técnico", "Cuentas de usuario",
       "Crear, inhabilitar y eliminar cuentas, restablecer contraseñas y designar Desarrolladores.", A_GLOBAL, tecnico=True),
    _p("soporte.sesiones", "Técnico", "Cerrar sesiones", "Cerrar las sesiones abiertas de una persona.", A_GLOBAL, tecnico=True),
    _p("soporte.desbloquear", "Técnico", "Desbloquear accesos", "Levantar el bloqueo por intentos fallidos de ingreso.", A_GLOBAL, tecnico=True),
    _p("respaldo.exportar", "Técnico", "Exportar respaldo", "Descargar el respaldo cifrado de toda la base.", A_GLOBAL, tecnico=True),
    _p("respaldo.restaurar", "Técnico", "Restaurar respaldo", "Reemplazar todos los datos por los de un respaldo.", A_GLOBAL, tecnico=True),
    _p("sistema.reiniciar", "Técnico", "Reinicio de fábrica", "Borrar todos los datos del sistema.", A_GLOBAL, tecnico=True),
    _p("sistema.puesta_en_marcha", "Técnico", "Guía de puesta en marcha", "Ver el avance de los pasos para arrancar el sistema.", A_GLOBAL, _V,
       tecnico=True),
)

POR_CODIGO: dict[str, Permiso] = {p.codigo: p for p in CATALOGO}
GRUPOS: tuple[str, ...] = tuple(dict.fromkeys(p.grupo for p in CATALOGO))
FUNCIONALES: tuple[Permiso, ...] = tuple(p for p in CATALOGO if not p.tecnico)
# Lo que todo usuario con sesión puede hacer sobre su propia cuenta (no es configurable y no depende del rol).
CUENTA_PROPIA = ("Ver su perfil", "Cambiar su contraseña", "Guía de bienvenida", "Cerrar sesión")
# Sin estos el Coordinador SGC no podría hacer su trabajo: su rol nunca puede quedar sin ellos.
# También aprueba siempre (es el respaldo de la aprobación jerárquica).
MINIMOS_DEL_COORDINADOR = ("roles.gestionar", "usuarios.asignar", "usuarios.ver", "estructura.ver", "cargas.aprobar", "cargas.ver",
                           "indicadores.ver", "ejercicios.ver")

assert len(POR_CODIGO) == len(CATALOGO), "códigos de permiso repetidos"
assert all(i in POR_CODIGO for p in CATALOGO for i in p.implica), "un permiso implica otro que no existe"
assert not any(POR_CODIGO[i].tecnico for p in FUNCIONALES for i in p.implica), "un permiso funcional no puede implicar uno técnico"


def existe(codigo: str) -> bool:
    return codigo in POR_CODIGO


def alcanza(concedido: str | None, pedido: str) -> bool:
    """¿El nivel concedido cubre el pedido? («modificar» incluye «ver»)."""
    return concedido is not None and ORDEN[concedido] >= ORDEN[pedido]


def completos(tecnicos: bool) -> dict[str, str]:
    """Todos los permisos (funcionales, o también los técnicos) a su nivel máximo."""
    return {p.codigo: p.niveles[-1] for p in CATALOGO if tecnicos or not p.tecnico}


def con_implicados(permisos: dict[str, str]) -> dict[str, str]:
    """El conjunto más lo que cada permiso necesita para servir (cierre transitivo, al nivel mínimo del implicado)."""
    salida, pendientes = dict(permisos), list(permisos)
    while pendientes:
        for codigo in POR_CODIGO[pendientes.pop()].implica:
            if codigo not in salida:
                salida[codigo] = POR_CODIGO[codigo].minimo
                pendientes.append(codigo)
    return salida


def resumen(permisos: dict[str, str]) -> list[str]:
    """Lo que un rol puede hacer, en lenguaje natural (una frase por grupo)."""
    frases = []
    for grupo in GRUPOS:
        etiquetas = [p.etiqueta.lower() for p in CATALOGO if p.grupo == grupo and p.codigo in permisos]
        if etiquetas:
            frases.append(f"{grupo}: {', '.join(etiquetas)}.")
    return frases or ["Este rol no puede hacer nada todavía."]
