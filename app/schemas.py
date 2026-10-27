"""Esquemas de entrada (validación de los datos que llegan a la API), ordenados por dominio."""
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

from .dominio import formulas
from .dominio.calendario import FRECUENCIAS

Rol = Literal["jefe", "gerente", "admin"]
Frecuencia = Literal[tuple(FRECUENCIAS)]
CLAVE_RX = r"^[a-z][a-z0-9_]{0,39}$"
Numero = Annotated[float, Field(allow_inf_nan=False)]   # rechaza NaN e Infinity (no son datos válidos)


# ---------------------------------------------------------------- sesión
class LoginIn(BaseModel):
    username: str = Field(max_length=40)      # mismo tope que al crear el usuario
    password: str = Field(max_length=128)


class ClaveIn(BaseModel):
    actual: str = Field(max_length=128)
    nueva: str = Field(min_length=10, max_length=128)


class TourIn(BaseModel):
    visto: bool = True


# ---------------------------------------------------------------- organización
class AreaIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=80)


class UsuarioIn(BaseModel):
    username: str = Field(pattern=r"^[a-z0-9._-]{3,40}$")
    nombre: str = Field(min_length=3, max_length=120)
    rol: Rol
    area_id: int | None = None
    password: str = Field(min_length=10, max_length=128)


class UsuarioEdit(BaseModel):
    nombre: str = Field(min_length=3, max_length=120)
    rol: Rol
    area_id: int | None = None
    activo: bool = True
    password: str | None = Field(default=None, min_length=10, max_length=128)


class CatalogoIn(BaseModel):
    tipo: Literal["gerencia", "proceso", "objetivo", "cargo"]
    valor: str = Field(min_length=2, max_length=300)
    detalle: str = Field(default="", max_length=2000)


class ParametrosIn(BaseModel):
    empresa: str = Field(min_length=2, max_length=120)
    gerencia_emisora: str = Field(default="", max_length=150)
    codigo_formato: str = Field(default="", max_length=30)
    ejercicio_inicio: int = Field(ge=1, le=12)
    proteger_reportes: bool = False
    clave_reportes: str = Field(default="", max_length=64)   # vacía = conservar la actual


class ReinicioIn(BaseModel):
    confirmacion: str = Field(max_length=40)
    password: str = Field(max_length=200)


class LogoIn(BaseModel):
    imagen: str = Field(max_length=1_200_000)  # data URL (png/jpeg/webp)


# ---------------------------------------------------------------- indicadores
class VariableIn(BaseModel):
    clave: str = Field(pattern=CLAVE_RX)
    etiqueta: str = Field(min_length=2, max_length=80)
    ayuda: str = Field(default="", max_length=300)      # texto de apoyo para quien carga el dato
    unidad: str = Field(default="", max_length=12)      # sufijo informativo (ej. TM, h, USD)
    opcional: bool = False                              # si queda vacía se usa «defecto»
    defecto: Numero = 0
    negativo: bool = False                              # permite valores negativos


class ConstanteIn(BaseModel):
    clave: str = Field(pattern=CLAVE_RX)
    etiqueta: str = Field(min_length=2, max_length=80)
    valor: Numero


class IndicadorIn(BaseModel):
    codigo: str = Field(min_length=2, max_length=20)
    nombre: str = Field(min_length=3, max_length=150)
    objetivo: str = Field(default="", max_length=1000)
    area_id: int
    unidad: str = Field(min_length=1, max_length=12)
    frecuencia: Frecuencia
    sentido: Literal["mayor", "menor"]
    formula: str = Field(min_length=1, max_length=formulas.MAX_LARGO * 2)
    variables: list[VariableIn] = Field(min_length=1, max_length=12)
    constantes: list[ConstanteIn] = Field(default_factory=list, max_length=12)
    decimales: int = Field(default=2, ge=0, le=6)
    fuente: str = Field(default="", max_length=500)
    notas: str = Field(default="", max_length=2000)
    seguimiento: Literal["proceso", "objetivo", "proveedor"] = "proceso"
    ref_nombre: str = Field(default="", max_length=200)
    ref_detalle: str = Field(default="", max_length=2000)
    sigla: str = Field(default="", max_length=20)
    gerencia: str = Field(default="", max_length=150)
    lider: str = Field(default="", max_length=150)
    resp_medicion: str = Field(default="", max_length=150)
    resp_registro: str = Field(default="", max_length=150)
    resp_analisis: str = Field(default="", max_length=150)
    meta: Numero
    limite: Numero
    meta_tope: Numero | None = None
    limite_tope: Numero | None = None
    activo: bool = True

    @field_validator("codigo")
    @classmethod
    def _codigo_en_mayusculas(cls, v):
        return v.strip().upper()

    @field_validator("unidad")
    @classmethod
    def _unidad_sin_espacios(cls, v):
        return v.strip()


class FormulaIn(BaseModel):
    formula: str
    claves: list[str]                   # variables + constantes disponibles
    variables: list[str] | None = None  # solo las variables (para avisar de las que no se usan)


class ProbarIn(BaseModel):
    formula: str
    valores: dict[str, Numero]
    constantes: dict[str, Numero] = {}
    decimales: int = Field(default=2, ge=0, le=6)
    meta: Numero
    limite: Numero
    meta_tope: Numero | None = None
    limite_tope: Numero | None = None
    sentido: Literal["mayor", "menor"]


# ---------------------------------------------------------------- mediciones
class CalcIn(BaseModel):
    indicador_id: int
    valores: dict[str, Numero | None]


class CargaIn(CalcIn):
    periodo: str
    analisis: str = ""
    plan_mejora: str = ""


class RevisionIn(BaseModel):
    accion: Literal["aprobar", "observar"]
    nota: str = ""


class NotaIn(BaseModel):
    texto: str = Field(min_length=3, max_length=2000)


# ---------------------------------------------------------------- ejercicios fiscales
class CierreIn(BaseModel):
    nota: str = Field(default="", max_length=2000)
    aceptar_faltantes: bool = False


class ReaperturaIn(BaseModel):
    nota: str = Field(min_length=5, max_length=2000)


# ---------------------------------------------------------------- importación de fichas históricas
class ImpMedicion(BaseModel):
    periodo: str
    valores: dict[str, Numero]
    analisis: str = Field(default="", max_length=4000)
    plan_mejora: str = Field(default="", max_length=4000)


class ImpIndicador(IndicadorIn):
    area_id: int = 0                      # se asigna al resolver el área por nombre
    area: str = Field(min_length=2, max_length=80)
    hoja: str = ""
    mediciones: list[ImpMedicion] = Field(default_factory=list, max_length=400)


class ImpCatalogo(CatalogoIn):
    pass


class ImpIn(BaseModel):
    archivo: str = ""
    inicio_ejercicio: int | None = None
    indicadores: list[ImpIndicador] = Field(max_length=100)
    catalogos: list[ImpCatalogo] = Field(default_factory=list, max_length=500)
    areas_nuevas: list[str] = Field(default_factory=list, max_length=60)
