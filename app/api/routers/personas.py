"""Personas y roles: cuentas y soporte (Desarrollador), asignación de rol / ámbito / indicadores y roles (Coordinador SGC)."""
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from ... import schemas
from ...models import Usuario
from ...servicios import personas, roles
from .. import serializadores as ser
from ..deps import Desde, IdRuta, Limite, con_total, escritura, get_db, requiere_permiso

router = APIRouter(prefix="/api", tags=["personas y roles"])
ve = requiere_permiso("usuarios.ver")
asigna = requiere_permiso("usuarios.asignar")
cuentas = requiere_permiso("usuarios.cuentas")
gestiona_roles = requiere_permiso("roles.gestionar")


def _persona(db: Session, p: Usuario) -> dict:
    return ser.persona(p, personas.detalles(db, [p])[p.id])


# ---------------------------------------------------------------- personas
@router.get("/usuarios")
def listar_usuarios(q: str | None = None, desde: Desde = 0, limite: Limite | None = None, response: Response = None,
                    db: Session = Depends(get_db), u: Usuario = Depends(ve)):
    """Personas con su rol y su posición (paginadas con `limite`; el total va en `X-Total-Count`). Quien no es
    Desarrollador no recibe a los Desarrolladores."""
    if limite is not None:
        con_total(response, personas.contar(db, u, q))
    pagina = personas.listar(db, u, buscar=q, desde=desde, limite=limite)
    ids = [x.id for x in pagina]
    detalle, con_historial, ingresos = personas.detalles(db, pagina), personas.ids_con_historial(db, ids), personas.ultimos_ingresos(db, ids)
    return [{**ser.persona(x, detalle[x.id]), "puede_eliminarse": x.id not in con_historial, "ultimo_ingreso": ser.iso(ingresos.get(x.id))}
            for x in pagina]


@router.get("/usuarios/opciones")
def opciones_usuarios(db: Session = Depends(get_db),
                      u: Usuario = Depends(requiere_permiso("indicadores.crear", "indicadores.asignar", "usuarios.asignar"))):
    """Personas a las que se puede asignar un indicador: uno mismo y quienes están debajo en la estructura."""
    return personas.opciones(db, u)


@router.get("/usuarios/{usuario_id}/alcance")
def alcance(usuario_id: IdRuta, db: Session = Depends(get_db), u: Usuario = Depends(ve)):
    """«Qué ve esta persona» con su asignación actual."""
    return personas.alcance(db, u, usuario_id)


@router.post("/usuarios/{usuario_id}/alcance")
def previsualizar_alcance(usuario_id: IdRuta, datos: schemas.AsignacionIn, db: Session = Depends(get_db), u: Usuario = Depends(asigna)):
    """«Qué vería esta persona» con la asignación que se está por guardar (no guarda nada)."""
    return personas.alcance(db, u, usuario_id, datos.model_dump())


@router.put("/usuarios/{usuario_id}/asignacion")
def asignar(usuario_id: IdRuta, datos: schemas.AsignacionIn, db: Session = Depends(get_db), u: Usuario = Depends(asigna),
            _=Depends(escritura)):
    return _persona(db, personas.asignar(db, u, usuario_id, datos.rol_id, datos.raiz, datos.ambito, datos.miembro))


@router.get("/usuarios/{usuario_id}/indicadores")
def indicadores_de(usuario_id: IdRuta, db: Session = Depends(get_db), u: Usuario = Depends(ve)):
    return personas.indicadores_de(db, u, usuario_id)


@router.put("/usuarios/{usuario_id}/indicadores")
def asignar_indicadores(usuario_id: IdRuta, datos: schemas.IndicadoresDePersonaIn, db: Session = Depends(get_db),
                        u: Usuario = Depends(asigna), _=Depends(escritura)):
    return personas.asignar_indicadores(db, u, usuario_id, datos.responsable, datos.cargador)


# ---------------------------------------------------------------- cuentas y soporte (técnico)
@router.post("/usuarios", status_code=201)
def crear_cuenta(datos: schemas.CuentaIn, db: Session = Depends(get_db), u: Usuario = Depends(cuentas), _=Depends(escritura)):
    """Cuenta nueva sin rol: no accede a nada hasta que el Coordinador SGC la asigne."""
    return _persona(db, personas.crear_cuenta(db, u, datos))


@router.put("/usuarios/{usuario_id}")
def editar_cuenta(usuario_id: IdRuta, datos: schemas.CuentaEdit, db: Session = Depends(get_db), u: Usuario = Depends(cuentas),
                  _=Depends(escritura)):
    return _persona(db, personas.editar_cuenta(db, u, usuario_id, datos))


@router.delete("/usuarios/{usuario_id}")
def eliminar_cuenta(usuario_id: IdRuta, db: Session = Depends(get_db), u: Usuario = Depends(cuentas), _=Depends(escritura)):
    """Elimina una cuenta sin actividad; si ya tiene historial hay que inhabilitarla (PUT con activo = false)."""
    personas.eliminar_cuenta(db, u, usuario_id)
    return {"ok": True}


@router.post("/usuarios/{usuario_id}/desarrollador")
def designar_desarrollador(usuario_id: IdRuta, datos: schemas.DesarrolladorIn, db: Session = Depends(get_db),
                           u: Usuario = Depends(cuentas), _=Depends(escritura)):
    """Procedimiento explícito entre Desarrolladores (pide la contraseña de quien lo ejecuta): dar o quitar ese rol."""
    return _persona(db, personas.designar_desarrollador(db, u, usuario_id, datos.activar, datos.password))


@router.post("/usuarios/{usuario_id}/cerrar-sesiones")
def cerrar_sesiones(usuario_id: IdRuta, db: Session = Depends(get_db), u: Usuario = Depends(requiere_permiso("soporte.sesiones")),
                    _=Depends(escritura)):
    """Soporte: cierra las sesiones abiertas del usuario en todos sus dispositivos."""
    personas.cerrar_sesiones(db, u, usuario_id)
    return {"ok": True}


@router.post("/sistema/desbloquear-accesos")
def desbloquear_accesos(db: Session = Depends(get_db), u: Usuario = Depends(requiere_permiso("soporte.desbloquear")),
                        _=Depends(escritura)):
    """Soporte: levanta el bloqueo por intentos fallidos de ingreso."""
    personas.desbloquear_accesos(db, u)
    return {"ok": True}


# ---------------------------------------------------------------- roles y permisos
def _rol(db: Session, u: Usuario, rol_id: int) -> dict:
    return next(r for r in roles.listar(db, u) if r["id"] == rol_id)


@router.get("/roles")
def listar_roles(db: Session = Depends(get_db), u: Usuario = Depends(requiere_permiso("roles.gestionar", "usuarios.asignar"))):
    """Roles con sus permisos, cuántas personas los usan y un resumen en lenguaje natural."""
    return roles.listar(db, u)


@router.get("/permisos")
def catalogo_de_permisos(u: Usuario = Depends(gestiona_roles)):
    """El catálogo que alimenta la matriz de permisos (sin los técnicos, salvo para el Desarrollador)."""
    return roles.catalogo_para(u)


@router.post("/roles", status_code=201)
def crear_rol(datos: schemas.RolIn, db: Session = Depends(get_db), u: Usuario = Depends(gestiona_roles), _=Depends(escritura)):
    return _rol(db, u, roles.crear(db, u, datos.nombre, datos.descripcion, datos.permisos).id)


@router.put("/roles/{rol_id}")
def editar_rol(rol_id: IdRuta, datos: schemas.RolIn, db: Session = Depends(get_db), u: Usuario = Depends(gestiona_roles),
               _=Depends(escritura)):
    return _rol(db, u, roles.editar(db, u, rol_id, datos.nombre, datos.descripcion, datos.permisos).id)


@router.post("/roles/{rol_id}/duplicar", status_code=201)
def duplicar_rol(rol_id: IdRuta, datos: schemas.DuplicarRolIn, db: Session = Depends(get_db), u: Usuario = Depends(gestiona_roles),
                 _=Depends(escritura)):
    return _rol(db, u, roles.duplicar(db, u, rol_id, datos.nombre).id)


@router.delete("/roles/{rol_id}")
def eliminar_rol(rol_id: IdRuta, db: Session = Depends(get_db), u: Usuario = Depends(gestiona_roles), _=Depends(escritura)):
    roles.eliminar(db, u, rol_id)
    return {"ok": True}
