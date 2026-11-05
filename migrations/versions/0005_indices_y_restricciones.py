"""Índices en las columnas que más se filtran y restricciones CHECK en los campos de estado.

- Índices: llaves foráneas (PostgreSQL no las indexa solo) y columnas de filtro/orden de mediciones y bitácora.
- CHECK: rol, sentido, frecuencia, estado de cargas y de ejercicios, semáforo. Antes cualquier texto cabía en esas columnas.
  Si alguna base trae datos que no cumplen una regla, esa restricción se OMITE con un aviso en el registro (el despliegue no
  se cae): corrija los datos y vuelva a ejecutar la migración.

Revisión: 0005
Anterior: 0004
"""
import logging

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

log = logging.getLogger("alembic.runtime.migration")

INDICES = [
    ("ix_usuarios_area_id", "usuarios", ["area_id"]),
    ("ix_indicadores_area_id", "indicadores", ["area_id"]),
    ("ix_mediciones_estado", "mediciones", ["estado"]),
    ("ix_mediciones_cargado_en", "mediciones", ["cargado_en"]),
    ("ix_mediciones_ejercicio", "mediciones", ["ejercicio"]),
    ("ix_notas_auditoria_medicion_id", "notas_auditoria", ["medicion_id"]),
    ("ix_bitacora_accion", "bitacora", ["accion"]),
    ("ix_bitacora_indicador_id", "bitacora", ["indicador_id"]),
]
FRECUENCIAS = "'mensual', 'bimestral', 'trimestral', 'cuatrimestral', 'semestral', 'anual', 'eventual'"
# (tabla, nombre, condición)
CHECKS = [
    ("ejercicios", "ck_ejercicios_estado", "estado IN ('abierto', 'cerrado')"),
    ("usuarios", "ck_usuarios_rol", "rol IN ('jefe', 'gerente', 'admin')"),
    ("indicadores", "ck_indicadores_sentido", "sentido IN ('mayor', 'menor')"),
    ("indicadores", "ck_indicadores_frecuencia", f"frecuencia IN ({FRECUENCIAS})"),
    ("mediciones", "ck_mediciones_estado", "estado IN ('enviado', 'aprobado', 'observado')"),
    ("mediciones", "ck_mediciones_semaforo", "semaforo IN ('verde', 'amarillo', 'rojo')"),
    ("mediciones", "ck_mediciones_sentido", "sentido IN ('mayor', 'menor')"),
]


def _violaciones(tabla: str, condicion: str) -> int:
    return op.get_bind().execute(sa.text(f"SELECT COUNT(*) FROM {tabla} WHERE NOT ({condicion})")).scalar() or 0  # noqa: S608


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for nombre, tabla, columnas in INDICES:
        if nombre not in {i["name"] for i in inspector.get_indexes(tabla)}:
            op.create_index(nombre, tabla, columnas)
    for tabla, nombre, condicion in CHECKS:
        malas = _violaciones(tabla, condicion)
        if malas:
            log.warning("Restricción %s omitida: %s fila(s) de %s no cumplen «%s». Corríjalas y reejecute la migración.",
                        nombre, malas, tabla, condicion)
            continue
        with op.batch_alter_table(tabla) as lote:      # «batch»: SQLite no admite ALTER ... ADD CONSTRAINT
            lote.create_check_constraint(nombre, condicion)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for tabla, nombre, _ in reversed(CHECKS):
        if nombre in {c["name"] for c in inspector.get_check_constraints(tabla)}:
            with op.batch_alter_table(tabla) as lote:
                lote.drop_constraint(nombre, type_="check")
    for nombre, tabla, _ in reversed(INDICES):
        if nombre in {i["name"] for i in inspector.get_indexes(tabla)}:
            op.drop_index(nombre, table_name=tabla)
