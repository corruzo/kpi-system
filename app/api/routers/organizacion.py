"""Configuración: listas de apoyo, parámetros del sistema, logo, respaldo y reinicio de fábrica."""
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile
from sqlalchemy.orm import Session

from ... import schemas
from ...errores import Invalido, NoEncontrado
from ...models import Usuario
from ...servicios import acceso, auditoria, marca, organizacion, parametros, reinicio, respaldo
from .. import serializadores as ser
from ..deps import IdRuta, escritura, get_db, requiere_permiso

router = APIRouter(prefix="/api", tags=["configuración"])
listas = requiere_permiso("catalogos.gestionar")
params = requiere_permiso("parametros.gestionar")


# ---------------------------------------------------------------- listas de apoyo
@router.get("/catalogos")
def listar_catalogos(db: Session = Depends(get_db),
                     _=Depends(requiere_permiso("catalogos.gestionar", "indicadores.crear", "indicadores.editar"))):
    """Las listas se ofrecen a quien las mantiene y a quien llena fichas (procesos, objetivos, cargos…)."""
    return [ser.catalogo(c) for c in organizacion.listar_catalogos(db)]


@router.post("/catalogos", status_code=201)
def crear_catalogo(datos: schemas.CatalogoIn, db: Session = Depends(get_db), u: Usuario = Depends(listas),
                   _=Depends(escritura)):
    return ser.catalogo(organizacion.crear_catalogo(db, u, datos))


@router.put("/catalogos/{elemento_id}")
def editar_catalogo(elemento_id: IdRuta, datos: schemas.CatalogoIn, db: Session = Depends(get_db),
                    u: Usuario = Depends(listas), _=Depends(escritura)):
    return ser.catalogo(organizacion.editar_catalogo(db, u, elemento_id, datos))


@router.delete("/catalogos/{elemento_id}")
def eliminar_catalogo(elemento_id: IdRuta, db: Session = Depends(get_db), u: Usuario = Depends(listas), _=Depends(escritura)):
    organizacion.eliminar_catalogo(db, u, elemento_id)
    return {"ok": True}


# ---------------------------------------------------------------- parámetros del sistema
@router.get("/parametros")
def ver_parametros(db: Session = Depends(get_db), _=Depends(params)):
    return parametros.resumen(db)


@router.put("/parametros")
def editar_parametros(datos: schemas.ParametrosIn, db: Session = Depends(get_db), u: Usuario = Depends(params),
                      _=Depends(escritura)):
    return parametros.actualizar(db, u, datos)


# ---------------------------------------------------------------- reinicio de fábrica
@router.post("/sistema/reiniciar")
def reiniciar_sistema(datos: schemas.ReinicioIn, db: Session = Depends(get_db), u: Usuario = Depends(requiere_permiso("sistema.reiniciar")),
                      _=Depends(escritura)):
    """Borra TODOS los datos (incluida la bitácora) y deja solo la cuenta del Desarrollador que lo ejecuta."""
    return reinicio.borrar_todo(db, u, datos.confirmacion, datos.password)


# ---------------------------------------------------------------- logo
@router.get("/logo", include_in_schema=False)
def ver_logo(v: str | None = None, db: Session = Depends(get_db)):
    datos = marca.bytes_logo(db)
    if not datos:
        raise NoEncontrado("Sin logo.")
    # con ?v=<huella> la URL cambia si cambia el logo: el navegador puede guardarlo un año
    cache = "public, max-age=31536000, immutable" if v else "public, max-age=3600"
    return Response(datos, media_type="image/png", headers={"Cache-Control": cache})


@router.put("/logo")
def guardar_logo(datos: schemas.LogoIn, db: Session = Depends(get_db), u: Usuario = Depends(params), _=Depends(escritura)):
    return {"logo_url": marca.guardar(db, u, datos.imagen)}


@router.delete("/logo")
def quitar_logo(db: Session = Depends(get_db), u: Usuario = Depends(params), _=Depends(escritura)):
    marca.quitar(db, u)
    return {"logo_url": None}


@router.post("/respaldo")
def descargar_respaldo(datos: schemas.RespaldoIn, db: Session = Depends(get_db), u: Usuario = Depends(requiere_permiso("respaldo.exportar")), _=Depends(escritura)):
    """Respaldo cifrado de toda la base (se descarga como archivo). La frase de paso no se guarda en ningún lado."""
    archivo, resumen = respaldo.crear(db, datos.frase)
    auditoria.registrar(db, u, "RESPALDO_CREADO", "sistema", None, {"bytes": resumen["bytes"], "sha256": resumen["sha256_archivo"]})
    db.commit()
    nombre = f"sigt-respaldo-{datetime.now(UTC):%Y%m%d-%H%M%S}.sigtbak"
    return Response(archivo, media_type="application/octet-stream",
                    headers={"Content-Disposition": f'attachment; filename="{nombre}"', "Cache-Control": "no-store",
                             "X-Respaldo-Sha256": resumen["sha256_archivo"]})


TOPE_RESPALDO = 60 * 1024 * 1024   # un respaldo mayor no es plausible y agotaría la memoria de la función


@router.post("/respaldo/restaurar")
async def restaurar_respaldo(archivo: UploadFile = File(...), frase: str = Form(..., min_length=12, max_length=200),
                             password: str = Form(..., max_length=128), confirmacion: str = Form(..., max_length=40),
                             db: Session = Depends(get_db), u: Usuario = Depends(requiere_permiso("respaldo.restaurar")), _=Depends(escritura)):
    """Reemplaza TODOS los datos por los del respaldo. Pide la frase del respaldo, la contraseña de quien lo ejecuta y escribir
    RESTAURAR. Todo o nada. Al terminar, las sesiones abiertas dejan de valer: hay que volver a ingresar."""
    if confirmacion.strip() != "RESTAURAR":
        raise Invalido("Escriba exactamente «RESTAURAR» para confirmar.")
    reinicio.exigir_password(u, password, f"restaurar|{u.id}")
    contenido = await archivo.read(TOPE_RESPALDO + 1)
    if len(contenido) > TOPE_RESPALDO:
        raise Invalido("El archivo es demasiado grande para ser un respaldo de este sistema.")
    r = respaldo.restaurar(db, contenido, frase, reemplazar=True)
    db.expire_all()                      # lo cargado antes ya no corresponde a lo restaurado
    restaurado = db.get(Usuario, u.id)   # si quien restaura existe en el respaldo, deja constancia en la cadena restaurada
    if restaurado:
        acceso.preparar(db, restaurado)
        auditoria.registrar(db, restaurado, "RESPALDO_RESTAURADO", "sistema", None, {"respaldo_del": r["creado"]})
        db.commit()
    parametros.refrescar(forzar=True)
    return {"ok": True, "creado": r["creado"], "tablas": r["tablas"]}
