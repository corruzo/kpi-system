"""Recursos de la interfaz: tipografía autoalojada (la CSP no permite CDN) y página principal con la nueva hoja de estilos."""


def test_la_tipografia_se_sirve_desde_el_propio_servidor(client):
    for archivo in ("manrope-latin-wght-normal.woff2", "manrope-latin-ext-wght-normal.woff2"):
        r = client.get(f"/static/fonts/{archivo}")
        assert r.status_code == 200 and len(r.content) > 5_000


def test_la_hoja_de_estilos_declara_manrope_y_la_paleta_de_la_guia(client):
    css = client.get("/static/tailwind.css").text
    assert "/static/fonts/manrope-latin-wght-normal.woff2" in css
    assert "rgb(0 107 255" in css and "rgb(11 53 88" in css      # Signal Blue y Ink Navy


def test_la_pagina_principal_carga_los_estilos(client):
    html = client.get("/").text
    assert "/static/tailwind.css" in html and 'content="#f8f9fb"' in html
