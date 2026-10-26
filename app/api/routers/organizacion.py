"""Organización: áreas, usuarios, listas de apoyo, parámetros del sistema y logo."""
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from ... import schemas
from ...errores import NoEncontrado
from ...models import Usuario
from ...servicios import marca, organizacion, parametros
from .. import serializadores as ser
from ..deps import escritura, get_db, requiere, usuario_actual

router = APIRouter(prefix="/api", tags=["organización"])
solo_admin = requiere("admin")


# ---------------------------------------------------------------- áreas
@router.get("/areas")
def listar_areas(db: Session = Depends(get_db), _=Depends(usuario_actual)):
    return [ser.area(a) for a in organizacion.listar_areas(db)]


@router.post("/areas", status_code=201)
def crear_area(datos: schemas.AreaIn, db: Session = Depends(get_db), u: Usuario = Depends(solo_admin), _=Depends(escritura)):
    return ser.area(organizacion.crear_area(db, u, datos.nombre))


@router.put("/areas/{area_id}")
def editar_area(area_id: int, datos: schemas.AreaIn, db: Session = Depends(get_db), u: Usuario = Depends(solo_admin),
                _=Depends(escritura)):
    return ser.area(organizacion.editar_area(db, u, area_id, datos.nombre))


@router.delete("/areas/{area_id}")
def eliminar_area(area_id: int, db: Session = Depends(get_db), u: Usuario = Depends(solo_admin), _=Depends(escritura)):
    organizacion.eliminar_area(db, u, area_id)
    return {"ok": True}


# ---------------------------------------------------------------- usuarios
@router.get("/usuarios")
def listar_usuarios(db: Session = Depends(get_db), _=Depends(solo_admin)):
    return [ser.usuario(x) for x in organizacion.listar_usuarios(db)]


@router.post("/usuarios", status_code=201)
def crear_usuario(datos: schemas.UsuarioIn, db: Session = Depends(get_db), u: Usuario = Depends(solo_admin), _=Depends(escritura)):
    return ser.usuario(organizacion.crear_usuario(db, u, datos))


@router.put("/usuarios/{usuario_id}")
def editar_usuario(usuario_id: int, datos: schemas.UsuarioEdit, db: Session = Depends(get_db),
                   u: Usuario = Depends(solo_admin), _=Depends(escritura)):
    return ser.usuario(organizacion.editar_usuario(db, u, usuario_id, datos))


# ---------------------------------------------------------------- listas de apoyo
@router.get("/catalogos")
def listar_catalogos(db: Session = Depends(get_db), _=Depends(usuario_actual)):
    return [ser.catalogo(c) for c in organizacion.listar_catalogos(db)]


@router.post("/catalogos", status_code=201)
def crear_catalogo(datos: schemas.CatalogoIn, db: Session = Depends(get_db), u: Usuario = Depends(solo_admin),
                   _=Depends(escritura)):
    return ser.catalogo(organizacion.crear_catalogo(db, u, datos))


@router.put("/catalogos/{elemento_id}")
def editar_catalogo(elemento_id: int, datos: schemas.CatalogoIn, db: Session = Depends(get_db),
                    u: Usuario = Depends(solo_admin), _=Depends(escritura)):
    return ser.catalogo(organizacion.editar_catalogo(db, u, elemento_id, datos))


@router.delete("/catalogos/{elemento_id}")
def eliminar_catalogo(elemento_id: int, db: Session = Depends(get_db), u: Usuario = Depends(solo_admin), _=Depends(escritura)):
    organizacion.eliminar_catalogo(db, u, elemento_id)
    return {"ok": True}


# ---------------------------------------------------------------- parámetros del sistema
@router.get("/parametros")
def ver_parametros(db: Session = Depends(get_db), _=Depends(usuario_actual)):
    return parametros.resumen(db)


@router.put("/parametros")
def editar_parametros(datos: schemas.ParametrosIn, db: Session = Depends(get_db), u: Usuario = Depends(solo_admin),
                      _=Depends(escritura)):
    return parametros.actualizar(db, u, datos)


# ---------------------------------------------------------------- logo
@router.get("/logo", include_in_schema=False)
def ver_logo(db: Session = Depends(get_db)):
    datos = marca.bytes_logo(db)
    if not datos:
        raise NoEncontrado("Sin logo.")
    return Response(datos, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})


@router.put("/logo")
def guardar_logo(datos: schemas.LogoIn, db: Session = Depends(get_db), u: Usuario = Depends(solo_admin), _=Depends(escritura)):
    return {"logo_url": marca.guardar(db, u, datos.imagen)}


@router.delete("/logo")
def quitar_logo(db: Session = Depends(get_db), u: Usuario = Depends(solo_admin), _=Depends(escritura)):
    marca.quitar(db, u)
    return {"logo_url": None}
