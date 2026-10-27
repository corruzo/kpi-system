"""Modelo de datos del SGC • TRIPOLIVEN."""
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, event
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def ahora() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None, microsecond=0)


class Area(Base):
    __tablename__ = "areas"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), unique=True)


class Parametro(Base):
    """Configuración del sistema (clave/valor): empresa, código del formato, inicio del ejercicio fiscal…"""
    __tablename__ = "parametros"
    clave: Mapped[str] = mapped_column(String(40), primary_key=True)
    valor: Mapped[str] = mapped_column(Text, default="")


class Ejercicio(Base):
    """Ejercicio fiscal cerrado (o reabierto). Los ejercicios sin fila se consideran abiertos."""
    __tablename__ = "ejercicios"
    anio: Mapped[int] = mapped_column(Integer, primary_key=True)             # año en que termina
    estado: Mapped[str] = mapped_column(String(10), default="cerrado")      # cerrado | abierto
    cerrado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    cerrado_en: Mapped[datetime | None] = mapped_column(DateTime)
    nota: Mapped[str | None] = mapped_column(Text, default="")
    resumen: Mapped[dict | None] = mapped_column(JSON)                      # foto de los resultados al cerrar
    reabierto_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    reabierto_en: Mapped[datetime | None] = mapped_column(DateTime)
    nota_reapertura: Mapped[str | None] = mapped_column(Text, default="")
    cerrado_por: Mapped["Usuario | None"] = relationship(foreign_keys=[cerrado_por_id])


class IntentoFallido(Base):
    """Un intento fallido (de ingreso o de confirmación de reinicio). Los contadores del limitador de intentos viven aquí,
    no en memoria, para que el bloqueo valga entre todos los procesos. `llave` es un SHA-256: no guarda IP ni usuarios."""
    __tablename__ = "intentos_fallidos"
    __table_args__ = (Index("ix_intentos_fallidos_llave_fecha", "llave", "fecha"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    llave: Mapped[str] = mapped_column(String(64))
    fecha: Mapped[datetime] = mapped_column(DateTime, index=True, default=ahora)


class Catalogo(Base):
    """Listas de apoyo de la ficha: gerencias, procesos (con su objetivo), objetivos organizacionales, cargos."""
    __tablename__ = "catalogos"
    __table_args__ = (UniqueConstraint("tipo", "valor"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String(20))      # gerencia | proceso | objetivo | cargo
    valor: Mapped[str] = mapped_column(String(300))
    detalle: Mapped[str] = mapped_column(Text, default="")


class Usuario(Base):
    __tablename__ = "usuarios"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    nombre: Mapped[str] = mapped_column(String(120))
    rol: Mapped[str] = mapped_column(String(20))  # jefe | gerente | admin
    area_id: Mapped[int | None] = mapped_column(ForeignKey("areas.id"))
    password_hash: Mapped[str] = mapped_column(String(200))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    sesion_v: Mapped[int] = mapped_column(Integer, default=0)  # sube al cambiar la clave: invalida sesiones
    tour_visto: Mapped[bool | None] = mapped_column(Boolean, default=False)  # guía de bienvenida ya vista/omitida
    area: Mapped[Area | None] = relationship()


class Indicador(Base):
    """Ficha técnica del indicador."""
    __tablename__ = "indicadores"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True)
    nombre: Mapped[str] = mapped_column(String(150))
    objetivo: Mapped[str] = mapped_column(Text, default="")
    area_id: Mapped[int] = mapped_column(ForeignKey("areas.id"))
    unidad: Mapped[str] = mapped_column(String(20))        # %, días, TM, USD, cantidad
    frecuencia: Mapped[str] = mapped_column(String(20))    # mensual | trimestral | semestral
    sentido: Mapped[str] = mapped_column(String(10))       # mayor | menor  (mayor/menor es mejor)
    formula: Mapped[str] = mapped_column(String(300))
    variables: Mapped[list] = mapped_column(JSON)          # [{"clave":..., "etiqueta":...}]
    meta: Mapped[float] = mapped_column(Float)             # límite de zona verde
    limite: Mapped[float] = mapped_column(Float)           # límite de zona amarilla (más allá = rojo)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=ahora)
    # --- ficha técnica ampliada (columnas añadidas por migración automática) ---
    constantes: Mapped[list | None] = mapped_column(JSON, default=list)       # [{"clave","etiqueta","valor"}]
    decimales: Mapped[int | None] = mapped_column(Integer, default=2)
    fuente: Mapped[str | None] = mapped_column(Text, default="")              # origen de los datos
    notas: Mapped[str | None] = mapped_column(Text, default="")               # método de cálculo / observaciones
    # --- datos de la ficha técnica del SGC ---
    seguimiento: Mapped[str | None] = mapped_column(String(20), default="proceso")  # proceso | objetivo | proveedor
    ref_nombre: Mapped[str | None] = mapped_column(String(200), default="")   # proceso u objetivo organizacional
    ref_detalle: Mapped[str | None] = mapped_column(Text, default="")         # objetivo del proceso / específico / bien o servicio
    sigla: Mapped[str | None] = mapped_column(String(20), default="")
    gerencia: Mapped[str | None] = mapped_column(String(150), default="")
    lider: Mapped[str | None] = mapped_column(String(150), default="")        # líder de proceso (cargo)
    resp_medicion: Mapped[str | None] = mapped_column(String(150), default="")
    resp_registro: Mapped[str | None] = mapped_column(String(150), default="")
    resp_analisis: Mapped[str | None] = mapped_column(String(150), default="")
    meta_tope: Mapped[float | None] = mapped_column(Float)                    # otro extremo de la zona verde
    limite_tope: Mapped[float | None] = mapped_column(Float)                  # otro extremo de la zona amarilla
    area: Mapped[Area] = relationship()

    @property
    def precision(self) -> int:
        """Decimales con que se muestra y redondea el resultado (por defecto 2)."""
        return 2 if self.decimales is None else self.decimales


class Medicion(Base):
    """Carga de un indicador para un período. Guarda una foto de la ficha vigente al cargar."""
    __tablename__ = "mediciones"
    __table_args__ = (UniqueConstraint("indicador_id", "periodo"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    indicador_id: Mapped[int] = mapped_column(ForeignKey("indicadores.id"))
    periodo: Mapped[str] = mapped_column(String(10))
    valores: Mapped[dict] = mapped_column(JSON)
    resultado: Mapped[float] = mapped_column(Float)
    semaforo: Mapped[str] = mapped_column(String(10))      # verde | amarillo | rojo
    meta: Mapped[float] = mapped_column(Float)
    limite: Mapped[float] = mapped_column(Float)
    sentido: Mapped[str] = mapped_column(String(10))
    estado: Mapped[str] = mapped_column(String(12))        # enviado | aprobado | observado
    analisis: Mapped[str] = mapped_column(Text, default="")
    plan_mejora: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    cargado_por_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    cargado_en: Mapped[datetime] = mapped_column(DateTime)
    revisado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    revisado_en: Mapped[datetime | None] = mapped_column(DateTime)
    nota_revision: Mapped[str] = mapped_column(Text, default="")
    # Foto del método de cálculo vigente al cargar (reproducibilidad del histórico)
    formula: Mapped[str | None] = mapped_column(Text)
    constantes: Mapped[list | None] = mapped_column(JSON)
    decimales: Mapped[int | None] = mapped_column(Integer)
    meta_tope: Mapped[float | None] = mapped_column(Float)
    limite_tope: Mapped[float | None] = mapped_column(Float)
    ejercicio: Mapped[int | None] = mapped_column(Integer)   # año en que termina el ejercicio fiscal del período
    indicador: Mapped[Indicador] = relationship()
    cargado_por: Mapped[Usuario] = relationship(foreign_keys=[cargado_por_id])
    revisado_por: Mapped[Usuario | None] = relationship(foreign_keys=[revisado_por_id])
    notas: Mapped[list["NotaAuditoria"]] = relationship(
        back_populates="medicion", order_by="NotaAuditoria.id")

    @property
    def precision(self) -> int:
        return self.decimales if self.decimales is not None else self.indicador.precision

    @property
    def formula_aplicada(self) -> str:
        """Fórmula vigente cuando se cargó (cargas antiguas sin foto usan la actual)."""
        return self.formula or self.indicador.formula

    @property
    def constantes_aplicadas(self) -> list:
        return self.constantes if self.constantes is not None else (self.indicador.constantes or [])


class NotaAuditoria(Base):
    __tablename__ = "notas_auditoria"
    id: Mapped[int] = mapped_column(primary_key=True)
    medicion_id: Mapped[int] = mapped_column(ForeignKey("mediciones.id"))
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    texto: Mapped[str] = mapped_column(Text)
    fecha: Mapped[datetime] = mapped_column(DateTime, default=ahora)
    medicion: Mapped[Medicion] = relationship(back_populates="notas")
    usuario: Mapped[Usuario] = relationship()


class Bitacora(Base):
    """Registro inalterable (solo inserción) con cadena de hashes SHA-256."""
    __tablename__ = "bitacora"
    id: Mapped[int] = mapped_column(primary_key=True)
    fecha: Mapped[datetime] = mapped_column(DateTime)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    usuario_nombre: Mapped[str] = mapped_column(String(120))
    rol: Mapped[str] = mapped_column(String(20))
    accion: Mapped[str] = mapped_column(String(40))
    entidad: Mapped[str] = mapped_column(String(30))
    entidad_id: Mapped[int | None] = mapped_column(Integer)
    indicador_id: Mapped[int | None] = mapped_column(Integer)
    area_id: Mapped[int | None] = mapped_column(Integer)
    detalle: Mapped[dict] = mapped_column(JSON)
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64))


@event.listens_for(Bitacora, "before_update")
def _no_update(*_):
    raise RuntimeError("La bitácora es inalterable: no se permiten modificaciones.")


@event.listens_for(Bitacora, "before_delete")
def _no_delete(*_):
    raise RuntimeError("La bitácora es inalterable: no se permiten eliminaciones.")
