"""SIGT · Sistema de Indicadores de Gestión — Tripoliven, C.A."""
import csv
import io
import logging
import threading
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from . import audit, calc, security
from .bootstrap import bootstrap_admin, preparar_base
from .config import PRODUCCION, TRUST_PROXY
from .database import get_db
from .models import Area, Bitacora, Indicador, Medicion, NotaAuditoria, Usuario, ahora

STATIC = Path(__file__).parent / "static"
_lock = threading.Lock()  # serializa escrituras para mantener íntegra la cadena de la bitácora


_iniciado = False


def _motivo(e: Exception) -> str:
    """Motivo legible sin exponer credenciales: solo la primera línea del error del driver."""
    if isinstance(e, (OperationalError, RuntimeError)):
        linea = (str(getattr(e, "orig", None) or e).strip().splitlines() or [""])[0]
        return f"{type(e).__name__}: {linea[:300]}"
    return f"{type(e).__name__} (vea Logs de Vercel para el detalle)"


def iniciar():
    """Prepara la base una sola vez por proceso (en serverless no siempre se ejecuta el lifespan)."""
    global _iniciado
    with _lock:
        if not _iniciado:
            preparar_base()
            bootstrap_admin()
            _iniciado = True


@asynccontextmanager
async def lifespan(_):
    try:
        iniciar()
    except Exception:  # no tumbar el proceso: se reintenta en la primera petición y se muestra el motivo
        logging.getLogger("sigt").exception("Fallo al preparar la base de datos")
    yield


app = FastAPI(title="SIGT Tripoliven", lifespan=lifespan,
              docs_url=None if PRODUCCION else "/docs", redoc_url=None,
              openapi_url=None if PRODUCCION else "/openapi.json")
limite_login = security.LimiteIntentos()

CSP = ("default-src 'self'; script-src 'self' 'unsafe-eval' 'unsafe-inline'; "
       "style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; "
       "frame-ancestors 'none'; base-uri 'self'; form-action 'self'")


@app.middleware("http")
async def cabeceras(request: Request, call_next):
    if not _iniciado and request.url.path != "/healthz":
        try:
            await run_in_threadpool(iniciar)
        except Exception as e:
            logging.getLogger("sigt").exception("Fallo al preparar la base de datos")
            return PlainTextResponse(f"SIGT no pudo preparar la base de datos.\n\n{_motivo(e)}\n", status_code=503)
    r = await call_next(request)
    r.headers.update({"X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY",
                      "Referrer-Policy": "same-origin", "Content-Security-Policy": CSP,
                      "Permissions-Policy": "camera=(), microphone=(), geolocation=()"})
    if PRODUCCION:
        r.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if request.url.path.startswith("/api/"):
        r.headers["Cache-Control"] = "no-store"
    return r


@app.get("/healthz", include_in_schema=False)
def healthz(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {"ok": True}


# ------------------------------------------------------------- seguridad
def usuario_actual(request: Request, db: Session = Depends(get_db)) -> Usuario:
    tok = security.leer_token(request.cookies.get(security.COOKIE))
    u = db.get(Usuario, tok[0]) if tok else None
    if not u or not u.activo or u.sesion_v != tok[1]:
        raise HTTPException(401, "Sesión no válida o expirada.")
    return u


def requiere(*roles: str):
    def dep(u: Usuario = Depends(usuario_actual)) -> Usuario:
        if u.rol not in roles:
            raise HTTPException(403, "No tiene permisos para esta acción.")
        return u
    return dep


def escritura():
    with _lock:
        yield


def iso(d):
    return d.isoformat() + "Z" if d else None


# ---------------------------------------------------------- serializadores
def u_out(u: Usuario):
    return {"id": u.id, "username": u.username, "nombre": u.nombre, "rol": u.rol,
            "area_id": u.area_id, "area": u.area.nombre if u.area else None, "activo": u.activo}


def ind_out(i: Indicador):
    return {"id": i.id, "codigo": i.codigo, "nombre": i.nombre, "objetivo": i.objetivo,
            "area_id": i.area_id, "area": i.area.nombre, "unidad": i.unidad,
            "frecuencia": i.frecuencia, "sentido": i.sentido, "formula": i.formula,
            "variables": i.variables, "meta": i.meta, "limite": i.limite, "activo": i.activo}


def med_out(m: Medicion):
    i = m.indicador
    return {"id": m.id, "indicador_id": i.id, "codigo": i.codigo, "indicador": i.nombre,
            "area": i.area.nombre, "area_id": i.area_id, "unidad": i.unidad,
            "frecuencia": i.frecuencia, "variables": i.variables, "periodo": m.periodo,
            "periodo_etiqueta": calc.etiqueta(i.frecuencia, m.periodo),
            "valores": m.valores, "resultado": m.resultado, "semaforo": m.semaforo,
            "meta": m.meta, "limite": m.limite, "sentido": m.sentido, "estado": m.estado,
            "analisis": m.analisis, "plan_mejora": m.plan_mejora, "version": m.version,
            "cargado_por": m.cargado_por.nombre, "cargado_por_id": m.cargado_por_id, "cargado_en": iso(m.cargado_en),
            "revisado_por": m.revisado_por.nombre if m.revisado_por else None,
            "revisado_en": iso(m.revisado_en), "nota_revision": m.nota_revision,
            "notas": [{"id": n.id, "usuario": n.usuario.nombre, "fecha": iso(n.fecha),
                       "texto": n.texto} for n in m.notas]}


def bit_out(b: Bitacora):
    return {"id": b.id, "fecha": iso(b.fecha), "usuario": b.usuario_nombre, "rol": b.rol,
            "accion": b.accion, "entidad": b.entidad, "entidad_id": b.entidad_id,
            "indicador_id": b.indicador_id, "area_id": b.area_id, "detalle": b.detalle,
            "hash": b.hash}


# ------------------------------------------------------------- esquemas
class LoginIn(BaseModel):
    username: str
    password: str


class ClaveIn(BaseModel):
    actual: str
    nueva: str = Field(min_length=10, max_length=128)


class AreaIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=80)


class UsuarioIn(BaseModel):
    username: str = Field(pattern=r"^[a-z0-9._-]{3,40}$")
    nombre: str = Field(min_length=3, max_length=120)
    rol: Literal["jefe", "gerente", "admin"]
    area_id: int | None = None
    password: str = Field(min_length=10, max_length=128)


class UsuarioEdit(BaseModel):
    nombre: str = Field(min_length=3, max_length=120)
    rol: Literal["jefe", "gerente", "admin"]
    area_id: int | None = None
    activo: bool = True
    password: str | None = Field(default=None, min_length=10, max_length=128)


class CalcIn(BaseModel):
    indicador_id: int
    valores: dict[str, float | None]


class CargaIn(CalcIn):
    periodo: str
    analisis: str = ""
    plan_mejora: str = ""


class RevisionIn(BaseModel):
    accion: Literal["aprobar", "observar"]
    nota: str = ""


class NotaIn(BaseModel):
    texto: str = Field(min_length=3, max_length=2000)


class VariableIn(BaseModel):
    clave: str = Field(pattern=r"^[a-z][a-z0-9_]{0,39}$")
    etiqueta: str = Field(min_length=2, max_length=80)


class IndicadorIn(BaseModel):
    codigo: str = Field(min_length=2, max_length=20)
    nombre: str = Field(min_length=3, max_length=150)
    objetivo: str = ""
    area_id: int
    unidad: Literal["%", "días", "TM", "USD", "cantidad"]
    frecuencia: Literal["mensual", "trimestral", "semestral"]
    sentido: Literal["mayor", "menor"]
    formula: str
    variables: list[VariableIn] = Field(min_length=1, max_length=8)
    meta: float
    limite: float
    activo: bool = True

    @field_validator("codigo")
    @classmethod
    def _cod(cls, v):
        return v.strip().upper()


class FormulaIn(BaseModel):
    formula: str
    claves: list[str]


# --------------------------------------------------------------- helpers
def _ind_visible(db: Session, u: Usuario, ind_id: int) -> Indicador:
    ind = db.get(Indicador, ind_id)
    if not ind or (u.rol != "admin" and not ind.activo):
        raise HTTPException(404, "Indicador no encontrado.")
    if u.rol == "jefe" and ind.area_id != u.area_id:
        raise HTTPException(403, "Este indicador pertenece a otra área.")
    return ind


def _calcular(ind: Indicador, valores: dict) -> dict:
    claves = [v["clave"] for v in ind.variables]
    faltan = [v["etiqueta"] for v in ind.variables if valores.get(v["clave"]) is None]
    if faltan:
        return {"ok": False, "error": "Complete: " + ", ".join(faltan) + "."}
    if any(valores[c] < 0 for c in claves):
        return {"ok": False, "error": "Los valores no pueden ser negativos."}
    try:
        res = calc.evaluar(ind.formula, {c: float(valores[c]) for c in claves})
    except calc.FormulaError as e:
        return {"ok": False, "error": str(e)}
    sem = calc.semaforo(res, ind.meta, ind.limite, ind.sentido)
    return {"ok": True, "resultado": res, "semaforo": sem, "requiere_analisis": sem != "verde"}


def _estados(db: Session, ind_id: int) -> dict[str, str]:
    return dict(db.execute(select(Medicion.periodo, Medicion.estado)
                           .where(Medicion.indicador_id == ind_id)).all())


# ------------------------------------------------------------------ auth
def _ip(request: Request) -> str:
    if TRUST_PROXY and request.headers.get("x-forwarded-for"):
        return request.headers["x-forwarded-for"].split(",")[0].strip()
    return request.client.host if request.client else "?"


@app.post("/api/login")
def login(datos: LoginIn, request: Request, response: Response, db: Session = Depends(get_db),
          _=Depends(escritura)):
    clave = f"{_ip(request)}|{datos.username.strip().lower()}"
    if limite_login.bloqueado(clave):
        raise HTTPException(429, "Demasiados intentos fallidos. Intente de nuevo en 15 minutos.")
    u = db.scalar(select(Usuario).where(Usuario.username == datos.username.strip().lower()))
    if not u or not u.activo or not security.verificar_password(datos.password, u.password_hash):
        limite_login.fallo(clave)
        raise HTTPException(401, "Usuario o contraseña incorrectos.")
    limite_login.limpiar(clave)
    audit.registrar(db, u, "INICIO_SESION", "usuario", u.id)
    db.commit()
    response.set_cookie(security.COOKIE, security.crear_token(u.id, u.sesion_v), httponly=True,
                        secure=PRODUCCION, samesite="lax", max_age=security.DURACION)
    return u_out(u)


@app.post("/api/logout")
def logout(response: Response):
    response.delete_cookie(security.COOKIE)
    return {"ok": True}


@app.get("/api/me")
def me(u: Usuario = Depends(usuario_actual)):
    return u_out(u)


@app.post("/api/cambiar-clave")
def cambiar_clave(d: ClaveIn, response: Response, db: Session = Depends(get_db),
                  u: Usuario = Depends(usuario_actual), _=Depends(escritura)):
    if not security.verificar_password(d.actual, u.password_hash):
        raise HTTPException(422, "La contraseña actual no es correcta.")
    u.password_hash = security.hash_password(d.nueva)
    u.sesion_v += 1
    audit.registrar(db, u, "CLAVE_CAMBIADA", "usuario", u.id)
    db.commit()
    response.set_cookie(security.COOKIE, security.crear_token(u.id, u.sesion_v), httponly=True,
                        secure=PRODUCCION, samesite="lax", max_age=security.DURACION)
    return {"ok": True}


# ---------------------------------------------------- administración
@app.post("/api/areas", status_code=201)
def crear_area(d: AreaIn, db: Session = Depends(get_db), u: Usuario = Depends(requiere("admin")),
               _=Depends(escritura)):
    nombre = d.nombre.strip()
    if db.scalar(select(Area).where(func.lower(Area.nombre) == nombre.lower())):
        raise HTTPException(422, "Ya existe un área con ese nombre.")
    a = Area(nombre=nombre)
    db.add(a)
    db.flush()
    audit.registrar(db, u, "AREA_CREADA", "area", a.id, {"nombre": nombre})
    db.commit()
    return {"id": a.id, "nombre": a.nombre}


@app.put("/api/areas/{area_id}")
def editar_area(area_id: int, d: AreaIn, db: Session = Depends(get_db),
                u: Usuario = Depends(requiere("admin")), _=Depends(escritura)):
    a = db.get(Area, area_id)
    if not a:
        raise HTTPException(404, "Área no encontrada.")
    dup = db.scalar(select(Area).where(func.lower(Area.nombre) == d.nombre.strip().lower()))
    if dup and dup.id != a.id:
        raise HTTPException(422, "Ya existe un área con ese nombre.")
    antes, a.nombre = a.nombre, d.nombre.strip()
    audit.registrar(db, u, "AREA_EDITADA", "area", a.id, {"antes": antes, "despues": a.nombre})
    db.commit()
    return {"id": a.id, "nombre": a.nombre}


@app.delete("/api/areas/{area_id}")
def eliminar_area(area_id: int, db: Session = Depends(get_db),
                  u: Usuario = Depends(requiere("admin")), _=Depends(escritura)):
    a = db.get(Area, area_id)
    if not a:
        raise HTTPException(404, "Área no encontrada.")
    if db.scalar(select(Indicador.id).where(Indicador.area_id == a.id).limit(1)) or \
            db.scalar(select(Usuario.id).where(Usuario.area_id == a.id).limit(1)):
        raise HTTPException(409, "El área tiene indicadores o usuarios asignados; no puede eliminarse.")
    audit.registrar(db, u, "AREA_ELIMINADA", "area", a.id, {"nombre": a.nombre})
    db.delete(a)
    db.commit()
    return {"ok": True}


def _validar_rol_area(db: Session, rol: str, area_id: int | None):
    if rol == "jefe" and not area_id:
        raise HTTPException(422, "Un Jefe de Área debe tener un área asignada.")
    if area_id and not db.get(Area, area_id):
        raise HTTPException(422, "Área inexistente.")


@app.get("/api/usuarios")
def listar_usuarios(db: Session = Depends(get_db), _=Depends(requiere("admin"))):
    return [u_out(x) for x in db.scalars(select(Usuario).order_by(Usuario.nombre))]


@app.post("/api/usuarios", status_code=201)
def crear_usuario(d: UsuarioIn, db: Session = Depends(get_db),
                  u: Usuario = Depends(requiere("admin")), _=Depends(escritura)):
    if db.scalar(select(Usuario).where(Usuario.username == d.username)):
        raise HTTPException(422, "Ese nombre de usuario ya existe.")
    _validar_rol_area(db, d.rol, d.area_id)
    n = Usuario(username=d.username, nombre=d.nombre.strip(), rol=d.rol,
                area_id=d.area_id if d.rol == "jefe" else None,
                password_hash=security.hash_password(d.password))
    db.add(n)
    db.flush()
    audit.registrar(db, u, "USUARIO_CREADO", "usuario", n.id,
                    {"username": n.username, "rol": n.rol, "area_id": n.area_id})
    db.commit()
    return u_out(n)


@app.put("/api/usuarios/{uid}")
def editar_usuario(uid: int, d: UsuarioEdit, db: Session = Depends(get_db),
                   u: Usuario = Depends(requiere("admin")), _=Depends(escritura)):
    n = db.get(Usuario, uid)
    if not n:
        raise HTTPException(404, "Usuario no encontrado.")
    if n.id == u.id and (not d.activo or d.rol != "admin"):
        raise HTTPException(422, "No puede desactivarse ni quitarse el rol de administrador a sí mismo.")
    _validar_rol_area(db, d.rol, d.area_id)
    cambios = {}
    for k, v in {"nombre": d.nombre.strip(), "rol": d.rol, "activo": d.activo,
                 "area_id": d.area_id if d.rol == "jefe" else None}.items():
        if getattr(n, k) != v:
            cambios[k] = [getattr(n, k), v]
            setattr(n, k, v)
    if d.password:
        n.password_hash = security.hash_password(d.password)
        n.sesion_v += 1
        cambios["password"] = "restablecida"
    if not d.activo:
        n.sesion_v += 1
    if cambios:
        audit.registrar(db, u, "USUARIO_EDITADO", "usuario", n.id, {"username": n.username, "cambios": cambios})
    db.commit()
    return u_out(n)


@app.get("/api/areas")
def areas(db: Session = Depends(get_db), _=Depends(usuario_actual)):
    return [{"id": a.id, "nombre": a.nombre} for a in db.scalars(select(Area).order_by(Area.nombre))]


# ------------------------------------------------------------ indicadores
@app.get("/api/indicadores")
def listar_indicadores(db: Session = Depends(get_db), u: Usuario = Depends(usuario_actual)):
    q = select(Indicador).order_by(Indicador.codigo)
    if u.rol == "jefe":
        q = q.where(Indicador.area_id == u.area_id)
    if u.rol != "admin":
        q = q.where(Indicador.activo.is_(True))
    hoy = date.today()
    conteo = dict(db.execute(select(Medicion.indicador_id, func.count(Medicion.id))
                             .group_by(Medicion.indicador_id)).all())
    out = []
    for i in db.scalars(q):
        d = ind_out(i)
        d["n_mediciones"] = conteo.get(i.id, 0)
        pend = calc.periodos_pendientes(i.frecuencia, hoy, _estados(db, i.id))
        d["pendientes"] = [{"periodo": p, "etiqueta": calc.etiqueta(i.frecuencia, p)} for p in pend]
        out.append(d)
    return out


def _validar_ficha(db: Session, d: IndicadorIn, actual_id: int | None = None):
    claves = [v.clave for v in d.variables]
    if len(set(claves)) != len(claves):
        raise HTTPException(422, "Las claves de las variables no pueden repetirse.")
    try:
        calc.validar_formula(d.formula, claves)
        calc.validar_umbrales(d.meta, d.limite, d.sentido)
    except (calc.FormulaError, ValueError) as e:
        raise HTTPException(422, str(e))
    if not db.get(Area, d.area_id):
        raise HTTPException(422, "Área inexistente.")
    dup = db.scalar(select(Indicador).where(Indicador.codigo == d.codigo))
    if dup and dup.id != actual_id:
        raise HTTPException(422, f"Ya existe un indicador con el código {d.codigo}.")


@app.post("/api/formula/validar")
def validar_formula(d: FormulaIn, _=Depends(requiere("admin"))):
    try:
        sin_usar = calc.validar_formula(d.formula, d.claves)
        return {"ok": True, "sin_usar": sin_usar}
    except calc.FormulaError as e:
        return {"ok": False, "error": str(e)}


class ProbarIn(BaseModel):
    formula: str
    valores: dict[str, float]
    meta: float
    limite: float
    sentido: Literal["mayor", "menor"]


@app.post("/api/formula/probar")
def probar_formula(d: ProbarIn, _=Depends(requiere("admin"))):
    """Calcula resultado y semáforo con valores de ejemplo antes de guardar la ficha."""
    try:
        calc.validar_umbrales(d.meta, d.limite, d.sentido)
        r = calc.evaluar(d.formula, d.valores)
    except (calc.FormulaError, ValueError) as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True, "resultado": r, "semaforo": calc.semaforo(r, d.meta, d.limite, d.sentido)}


@app.post("/api/indicadores", status_code=201)
def crear_indicador(d: IndicadorIn, db: Session = Depends(get_db),
                    u: Usuario = Depends(requiere("admin")), _=Depends(escritura)):
    _validar_ficha(db, d)
    ind = Indicador(**d.model_dump(exclude={"variables"}), variables=[v.model_dump() for v in d.variables])
    db.add(ind)
    db.flush()
    audit.registrar(db, u, "INDICADOR_CREADO", "indicador", ind.id,
                    {"codigo": ind.codigo, "nombre": ind.nombre, "formula": ind.formula,
                     "meta": ind.meta, "limite": ind.limite, "sentido": ind.sentido}, ind)
    db.commit()
    return ind_out(ind)


@app.put("/api/indicadores/{ind_id}")
def editar_indicador(ind_id: int, d: IndicadorIn, db: Session = Depends(get_db),
                     u: Usuario = Depends(requiere("admin")), _=Depends(escritura)):
    ind = db.get(Indicador, ind_id)
    if not ind:
        raise HTTPException(404, "Indicador no encontrado.")
    _validar_ficha(db, d, ind_id)
    if db.scalar(select(Medicion.id).where(Medicion.indicador_id == ind_id).limit(1)):
        if d.frecuencia != ind.frecuencia:
            raise HTTPException(422, "No se puede cambiar la frecuencia de un indicador con cargas registradas.")
        if {v.clave for v in d.variables} != {v["clave"] for v in ind.variables}:
            raise HTTPException(422, "No se pueden agregar, quitar ni renombrar claves de variables de un indicador "
                                     "con cargas registradas. Archívelo y cree uno nuevo.")
    nuevos = {**d.model_dump(exclude={"variables"}), "variables": [v.model_dump() for v in d.variables]}
    cambios = {k: [getattr(ind, k), v] for k, v in nuevos.items() if getattr(ind, k) != v}
    for k, v in nuevos.items():
        setattr(ind, k, v)
    if cambios:
        audit.registrar(db, u, "INDICADOR_EDITADO", "indicador", ind.id,
                        {"codigo": ind.codigo, "cambios": cambios}, ind)
    db.commit()
    return ind_out(ind)


@app.delete("/api/indicadores/{ind_id}")
def eliminar_indicador(ind_id: int, db: Session = Depends(get_db),
                       u: Usuario = Depends(requiere("admin")), _=Depends(escritura)):
    ind = db.get(Indicador, ind_id)
    if not ind:
        raise HTTPException(404, "Indicador no encontrado.")
    tiene = db.scalar(select(Medicion.id).where(Medicion.indicador_id == ind_id).limit(1))
    if tiene:  # se conserva la trazabilidad: se archiva en lugar de borrar
        ind.activo = False
        audit.registrar(db, u, "INDICADOR_ARCHIVADO", "indicador", ind.id, {"codigo": ind.codigo}, ind)
        db.commit()
        return {"ok": True, "archivado": True}
    audit.registrar(db, u, "INDICADOR_ELIMINADO", "indicador", ind.id,
                    {"codigo": ind.codigo, "nombre": ind.nombre}, ind)
    db.delete(ind)
    db.commit()
    return {"ok": True, "archivado": False}


@app.get("/api/indicadores/{ind_id}/periodos")
def periodos(ind_id: int, db: Session = Depends(get_db), u: Usuario = Depends(usuario_actual)):
    ind = _ind_visible(db, u, ind_id)
    hoy = date.today()
    meds = {m.periodo: m for m in db.scalars(select(Medicion).where(Medicion.indicador_id == ind_id))}
    pend = calc.periodos_pendientes(ind.frecuencia, hoy, {p: m.estado for p, m in meds.items()})
    return {"sugerido": pend[0] if pend else None,
            "periodos": [{"periodo": p, "etiqueta": calc.etiqueta(ind.frecuencia, p),
                          "actual": i == 0, "pendiente": p in pend,
                          "medicion": med_out(meds[p]) if p in meds else None}
                         for i, p in enumerate(calc.periodos_recientes(ind.frecuencia, hoy))]}


# ------------------------------------------------------------ mediciones
@app.post("/api/calcular")
def calcular(d: CalcIn, db: Session = Depends(get_db), u: Usuario = Depends(requiere("jefe", "admin"))):
    return _calcular(_ind_visible(db, u, d.indicador_id), d.valores)


@app.post("/api/mediciones", status_code=201)
def cargar(d: CargaIn, db: Session = Depends(get_db), u: Usuario = Depends(requiere("jefe", "admin")),
           _=Depends(escritura)):
    ind = _ind_visible(db, u, d.indicador_id)
    if not ind.activo:
        raise HTTPException(409, "El indicador está archivado.")
    if not calc.periodo_valido(ind.frecuencia, d.periodo) or \
            calc.es_futuro(ind.frecuencia, d.periodo, date.today()):
        raise HTTPException(422, "Período no válido para la frecuencia del indicador.")
    r = _calcular(ind, d.valores)
    if not r["ok"]:
        raise HTTPException(422, r["error"])
    analisis, plan = d.analisis.strip(), d.plan_mejora.strip()
    if r["requiere_analisis"] and (len(analisis) < 10 or len(plan) < 10):
        raise HTTPException(422, "El indicador está fuera de meta: el análisis de resultados y "
                                 "las correcciones / plan de mejora son obligatorios (ISO 9001:2015, 9.1.3 y 10.2).")
    valores = {v["clave"]: float(d.valores[v["clave"]]) for v in ind.variables}
    m = db.scalar(select(Medicion).where(Medicion.indicador_id == ind.id, Medicion.periodo == d.periodo))
    if m and m.estado != "observado":
        raise HTTPException(409, "Este período ya fue cargado y no puede modificarse.")
    reenvio = m is not None
    if m is None:
        m = Medicion(indicador_id=ind.id, periodo=d.periodo, version=1)
        db.add(m)
    else:
        m.version += 1
    m.valores, m.resultado, m.semaforo = valores, r["resultado"], r["semaforo"]
    m.meta, m.limite, m.sentido = ind.meta, ind.limite, ind.sentido
    m.estado, m.analisis, m.plan_mejora = "enviado", analisis, plan
    m.cargado_por_id, m.cargado_en = u.id, ahora()
    m.revisado_por_id = m.revisado_en = None
    m.nota_revision = ""
    db.flush()
    audit.registrar(db, u, "REENVIO" if reenvio else "CARGA", "medicion", m.id,
                    {"periodo": m.periodo, "valores": valores, "resultado": m.resultado,
                     "semaforo": m.semaforo, "analisis": analisis, "plan_mejora": plan,
                     "version": m.version}, ind)
    db.commit()
    return med_out(m)


@app.get("/api/mediciones")
def listar_mediciones(estado: str | None = None, indicador_id: int | None = None,
                      area_id: int | None = None, limite: int = 300,
                      db: Session = Depends(get_db), u: Usuario = Depends(usuario_actual)):
    q = select(Medicion).join(Indicador).order_by(Medicion.cargado_en.desc()).limit(min(limite, 1000))
    if u.rol == "jefe":
        q = q.where(Indicador.area_id == u.area_id)
    elif area_id:
        q = q.where(Indicador.area_id == area_id)
    if estado:
        q = q.where(Medicion.estado == estado)
    if indicador_id:
        q = q.where(Medicion.indicador_id == indicador_id)
    return [med_out(m) for m in db.scalars(q)]


def _med(db, u, med_id) -> Medicion:
    m = db.get(Medicion, med_id)
    if not m:
        raise HTTPException(404, "Carga no encontrada.")
    return m


@app.post("/api/mediciones/{med_id}/revision")
def revisar(med_id: int, d: RevisionIn, db: Session = Depends(get_db),
            u: Usuario = Depends(requiere("gerente", "admin")), _=Depends(escritura)):
    m = _med(db, u, med_id)
    if m.cargado_por_id == u.id:
        raise HTTPException(403, "Segregación de funciones: una carga propia debe revisarla otra persona.")
    if m.estado != "enviado":
        raise HTTPException(409, "Solo se pueden revisar cargas en estado «enviado».")
    nota = d.nota.strip()
    if d.accion == "observar" and len(nota) < 5:
        raise HTTPException(422, "Indique el motivo de la devolución.")
    m.estado = "aprobado" if d.accion == "aprobar" else "observado"
    m.revisado_por_id, m.revisado_en, m.nota_revision = u.id, ahora(), nota
    audit.registrar(db, u, "APROBACION" if d.accion == "aprobar" else "OBSERVACION", "medicion",
                    m.id, {"periodo": m.periodo, "nota": nota}, m.indicador)
    db.commit()
    return med_out(m)


@app.post("/api/mediciones/{med_id}/notas", status_code=201)
def agregar_nota(med_id: int, d: NotaIn, db: Session = Depends(get_db),
                 u: Usuario = Depends(requiere("gerente", "admin")), _=Depends(escritura)):
    m = _med(db, u, med_id)
    n = NotaAuditoria(medicion_id=m.id, usuario_id=u.id, texto=d.texto.strip(), fecha=ahora())
    db.add(n)
    db.flush()
    audit.registrar(db, u, "NOTA_AUDITORIA", "medicion", m.id,
                    {"periodo": m.periodo, "texto": n.texto}, m.indicador)
    db.commit()
    db.refresh(m)
    return med_out(m)


@app.get("/api/export/mediciones.csv")
def exportar(db: Session = Depends(get_db), _=Depends(requiere("gerente", "admin"))):
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Código", "Indicador", "Área", "Período", "Resultado", "Unidad", "Meta", "Límite",
                "Semáforo", "Estado", "Cargado por", "Cargado en", "Análisis", "Plan de mejora"])
    for m in db.scalars(select(Medicion).join(Indicador).order_by(Indicador.codigo, Medicion.periodo)):
        i = m.indicador
        w.writerow([i.codigo, i.nombre, i.area.nombre, m.periodo, m.resultado, i.unidad, m.meta,
                    m.limite, m.semaforo, m.estado, m.cargado_por.nombre, iso(m.cargado_en),
                    m.analisis, m.plan_mejora])
    return StreamingResponse(iter(["﻿" + buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=sigt_mediciones.csv"})


# ------------------------------------------------------------- dashboard
@app.get("/api/dashboard")
def dashboard(area_id: int | None = None, db: Session = Depends(get_db),
              _=Depends(requiere("gerente", "admin"))):
    hoy = date.today()
    q = select(Indicador).where(Indicador.activo.is_(True)).order_by(Indicador.codigo)
    if area_id:
        q = q.where(Indicador.area_id == area_id)
    inds, por_area = [], {}
    resumen = {"total": 0, "verde": 0, "amarillo": 0, "rojo": 0, "sin_datos": 0, "pendientes_carga": 0}
    for i in db.scalars(q):
        meds = db.scalars(select(Medicion).where(Medicion.indicador_id == i.id)
                          .order_by(Medicion.periodo)).all()
        validas = [m for m in meds if m.estado in ("enviado", "aprobado")]
        ultimo = validas[-1] if validas else None
        pend = calc.periodos_pendientes(i.frecuencia, hoy, {m.periodo: m.estado for m in meds})
        inds.append({**ind_out(i), "pendiente": bool(pend),
                     "ultimo": {"periodo": ultimo.periodo, "etiqueta": calc.etiqueta(i.frecuencia, ultimo.periodo),
                                "resultado": ultimo.resultado, "semaforo": ultimo.semaforo,
                                "estado": ultimo.estado} if ultimo else None,
                     "serie": [{"periodo": m.periodo, "etiqueta": calc.etiqueta(i.frecuencia, m.periodo),
                                "resultado": m.resultado, "semaforo": m.semaforo, "meta": m.meta,
                                "limite": m.limite} for m in validas]})
        a = por_area.setdefault(i.area.nombre, {"area": i.area.nombre, "total": 0, "verde": 0,
                                                "amarillo": 0, "rojo": 0, "sin_datos": 0})
        a["total"] += 1
        resumen["total"] += 1
        k = ultimo.semaforo if ultimo else "sin_datos"
        a[k] += 1
        resumen[k] += 1
        resumen["pendientes_carga"] += bool(pend)
    for a in por_area.values():
        a["cumplimiento"] = round(100 * a["verde"] / a["total"], 1)
    resumen["por_aprobar"] = len(db.scalars(select(Medicion.id).where(Medicion.estado == "enviado")).all())
    resumen["cumplimiento"] = round(100 * resumen["verde"] / resumen["total"], 1) if resumen["total"] else 0
    return {"resumen": resumen, "indicadores": inds, "por_area": list(por_area.values())}


# -------------------------------------------------------------- bitácora
@app.get("/api/bitacora")
def bitacora(accion: str | None = None, indicador_id: int | None = None, limite: int = 200,
             db: Session = Depends(get_db), u: Usuario = Depends(usuario_actual)):
    q = select(Bitacora).order_by(Bitacora.id.desc()).limit(min(limite, 1000))
    if u.rol == "jefe":
        q = q.where(Bitacora.area_id == u.area_id, Bitacora.entidad != "usuario")
    if accion:
        q = q.where(Bitacora.accion == accion)
    if indicador_id:
        q = q.where(Bitacora.indicador_id == indicador_id)
    codigos = dict(db.execute(select(Indicador.id, Indicador.codigo)).all())
    return [{**bit_out(b), "codigo": codigos.get(b.indicador_id)} for b in db.scalars(q)]


@app.get("/api/bitacora/verificar")
def verificar_bitacora(db: Session = Depends(get_db), _=Depends(requiere("gerente", "admin"))):
    return audit.verificar(db)


# ---------------------------------------------------------------- estáticos
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})
