"""`docs/PERMISOS.md` se genera del código: si el catálogo o las rutas cambian, esta prueba obliga a regenerarlo."""
from app import permisos_doc


def test_el_documento_de_permisos_coincide_con_el_codigo():
    actual = permisos_doc.DESTINO.read_text(encoding="utf-8")
    assert actual == permisos_doc.generar(), "docs/PERMISOS.md está desactualizado: ejecute `python -m app.permisos_doc`"


def test_toda_funcion_del_catalogo_figura_en_el_documento():
    from app import permisos as cat
    texto = permisos_doc.DESTINO.read_text(encoding="utf-8")
    assert all(f"`{p.codigo}`" in texto for p in cat.CATALOGO)
