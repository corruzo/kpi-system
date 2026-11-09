"""Modelo de datos del SGC • TRIPOLIVEN."""
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
)
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
    __table_args__ = (CheckConstraint("estado IN ('abierto', 'cerrado')", name="ck_ejercicios_estado"),)
    anio: Mapped[int] = mapped_column(Integer, primary_key=True)             # año en que termina
    estado: Mapped[str] = mapped_column(String(10), default="cerrado")      # cerrado | abierto
    cerrado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), index=True)
    cerrado_en: Mapped[datetime | None] = mapped_column(DateTime)
    nota: Mapped[str | None] = mapped_column(Text, default="")
    resumen: Mapped[dict | None] = mapped_column(JSON)                      # foto de los resultados al cerrar
    reabierto_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), index=True)
    reabierto_en: Mapped[datetime | None] = mapped_column(DateTime)
    nota_reapertura: Mapped[str | None] = mapped_column(Text, default="")
    creado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), index=True)
    creado_en: Mapped[datetime | None] = mapped_column(DateTime)
    cerrado_por: Mapped["Usuario | None"] = relationship(foreign_keys=[cerrado_por_id])


class Presupuesto(Base):
    """Lo que se presupuesta para un indicador en un período de su frecuencia (paso 3 del flujo anual).
    Al cargar el dato real, el presupuesto vigente se copia a la medición y se compara con el resultado."""
    __tablename__ = "presupuestos"
    __table_args__ = (UniqueConstraint("indicador_id", "periodo"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    ejercicio: Mapped[int] = mapped_column(ForeignKey("ejercicios.anio"), index=True)
    indicador_id: Mapped[int] = mapped_column(ForeignKey("indicadores.id"))
    periodo: Mapped[str] = mapped_column(String(10))
    valor: Mapped[float] = mapped_column(Float)
    actualizado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), index=True)
    actualizado_en: Mapped[datetime | None] = mapped_column(DateTime)


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
    __table_args__ = (CheckConstraint("rol IN ('jefe', 'gerente', 'admin')", name="ck_usuarios_rol"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    nombre: Mapped[str] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(120))   # opcional: destino de los recordatorios de carga
    rol: Mapped[str] = mapped_column(String(20))  # jefe | gerente | admin
    area_id: Mapped[int | None] = mapped_column(ForeignKey("areas.id"), index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    sesion_v: Mapped[int] = mapped_column(Integer, default=0)  # sube al cambiar la clave: invalida sesiones
    tour_visto: Mapped[bool | None] = mapped_column(Boolean, default=False)  # guía de bienvenida ya vista/omitida
    area: Mapped[Area | None] = relationship(lazy="joined")   # se muestra siempre junto al usuario: un solo SELECT


class Indicador(Base):
    """Ficha técnica del indicador."""
    __tablename__ = "indicadores"
    __table_args__ = (
        CheckConstraint("sentido IN ('mayor', 'menor')", name="ck_indicadores_sentido"),
        CheckConstraint("frecuencia IN ('mensual', 'bimestral', 'trimestral', 'cuatrimestral', 'semestral', 'anual', 'eventual')",
                        name="ck_indicadores_frecuencia"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True)
    nombre: Mapped[str] = mapped_column(String(150))
    objetivo: Mapped[str] = mapped_column(Text, default="")
    area_id: Mapped[int] = mapped_column(ForeignKey("areas.id"), index=True)
    encargado_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), index=True)  # único usuario con rol de encargado que lo ve y carga
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
    area: Mapped[Area] = relationship(lazy="joined")

    @property
    def precision(self) -> int:
        """Decimales con que se muestra y redondea el resultado (por defecto 2)."""
        return 2 if self.decimales is None else self.decimales


class Medicion(Base):
    """Carga de un indicador para un período. Guarda una foto de la ficha vigente al cargar."""
    __tablename__ = "mediciones"
    __table_args__ = (
        UniqueConstraint("indicador_id", "periodo"),
        CheckConstraint("estado IN ('enviado', 'aprobado', 'observado')", name="ck_mediciones_estado"),
        CheckConstraint("semaforo IN ('verde', 'amarillo', 'rojo')", name="ck_mediciones_semaforo"),
        CheckConstraint("sentido IN ('mayor', 'menor')", name="ck_mediciones_sentido"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    indicador_id: Mapped[int] = mapped_column(ForeignKey("indicadores.id"))
    periodo: Mapped[str] = mapped_column(String(10))
    valores: Mapped[dict] = mapped_column(JSON)
    resultado: Mapped[float] = mapped_column(Float)
    semaforo: Mapped[str] = mapped_column(String(10))      # verde | amarillo | rojo
    meta: Mapped[float] = mapped_column(Float)
    limite: Mapped[float] = mapped_column(Float)
    sentido: Mapped[str] = mapped_column(String(10))
    estado: Mapped[str] = mapped_column(String(12), index=True)   # enviado | aprobado | observado
    analisis: Mapped[str] = mapped_column(Text, default="")
    plan_mejora: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    cargado_por_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    cargado_en: Mapped[datetime] = mapped_column(DateTime, index=True)
    revisado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), index=True)
    revisado_en: Mapped[datetime | None] = mapped_column(DateTime)
    nota_revision: Mapped[str] = mapped_column(Text, default="")
    # Foto del método de cálculo vigente al cargar (reproducibilidad del histórico)
    formula: Mapped[str | None] = mapped_column(Text)
    constantes: Mapped[list | None] = mapped_column(JSON)
    decimales: Mapped[int | None] = mapped_column(Integer)
    meta_tope: Mapped[float | None] = mapped_column(Float)
    limite_tope: Mapped[float | None] = mapped_column(Float)
    presupuesto: Mapped[float | None] = mapped_column(Float)  # lo presupuestado para el período, copiado al cargar
    ejercicio: Mapped[int | None] = mapped_column(Integer, index=True)   # año en que termina el ejercicio fiscal del período
    # Toda carga se muestra con su indicador, quién la cargó y revisó y sus notas: se traen en la misma consulta (o en una
    # sola adicional para las notas) en vez de una consulta por fila (problema N+1: 500 cargas = 2.000 consultas).
    indicador: Mapped[Indicador] = relationship(lazy="joined")
    cargado_por: Mapped[Usuario] = relationship(foreign_keys=[cargado_por_id], lazy="joined")
    revisado_por: Mapped[Usuario | None] = relationship(foreign_keys=[revisado_por_id], lazy="joined")
    notas: Mapped[list["NotaAuditoria"]] = relationship(
        back_populates="medicion", order_by="NotaAuditoria.id", lazy="selectin")

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
    medicion_id: Mapped[int] = mapped_column(ForeignKey("mediciones.id"), index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    texto: Mapped[str] = mapped_column(Text)
    fecha: Mapped[datetime] = mapped_column(DateTime, default=ahora)
    medicion: Mapped[Medicion] = relationship(back_populates="notas")
    usuario: Mapped[Usuario] = relationship(lazy="joined")


class Bitacora(Base):
    """Registro inalterable (solo inserción) con cadena de hashes SHA-256."""
    __tablename__ = "bitacora"
    id: Mapped[int] = mapped_column(primary_key=True)
    fecha: Mapped[datetime] = mapped_column(DateTime)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), index=True)
    usuario_nombre: Mapped[str] = mapped_column(String(120))
    rol: Mapped[str] = mapped_column(String(20))
    accion: Mapped[str] = mapped_column(String(40), index=True)
    entidad: Mapped[str] = mapped_column(String(30))
    entidad_id: Mapped[int | None] = mapped_column(Integer)
    indicador_id: Mapped[int | None] = mapped_column(Integer, index=True)
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
