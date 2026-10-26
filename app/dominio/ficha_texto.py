"""Textos derivados de la ficha técnica de un indicador (los mismos en pantalla y en Excel)."""
import re


def meta_texto(i) -> str:
    """Meta como se escribía en la ficha en papel: «96 Mín.» o «3 Máx.»."""
    return f"{i.meta:g} {'Mín.' if i.sentido == 'mayor' else 'Máx.'}"


def formula_documentada(i) -> str:
    """Fórmula de cálculo con su leyenda de símbolos: «SP = SG * 100 / SR» + «SG = Solicitudes gestionadas»…"""
    f = i.formula
    for v in sorted([*i.variables, *(i.constantes or [])], key=lambda v: -len(v["clave"])):
        f = re.sub(r"\b" + re.escape(v["clave"]) + r"\b", v["clave"].upper(), f)
    lineas = [f"{i.sigla or 'IND'} = {f}"]
    lineas += [f"{v['clave'].upper()} = {v['etiqueta']}" for v in i.variables]
    lineas += [f"{c['clave'].upper()} = {c['etiqueta']} ({c['valor']:g})" for c in (i.constantes or [])]
    return "\n".join(lineas)


def formula_en_palabras(formula: str, variables, constantes=()) -> str:
    """La fórmula con las claves reemplazadas por sus etiquetas."""
    for v in sorted([*variables, *constantes], key=lambda v: -len(v["clave"])):
        formula = re.sub(r"\b" + re.escape(v["clave"]) + r"\b", v["etiqueta"], formula)
    return formula


def franjas(i):
    """((mín, máx) verde, (mín, máx) amarillo, (texto, texto) rojo): la tabla «Min./Max.» del semáforo."""
    mayor = i.sentido == "mayor"
    verde = (i.meta, i.meta_tope) if mayor else (i.meta_tope, i.meta)
    amarillo = (i.limite, i.limite_tope) if mayor else (i.limite_tope, i.limite)
    if mayor:
        rojo = (f"< {i.limite:g}", f"> {i.limite_tope:g}" if i.limite_tope is not None else "")
    else:
        rojo = (f"< {i.limite_tope:g}" if i.limite_tope is not None else "", f"> {i.limite:g}")
    return verde, amarillo, rojo
