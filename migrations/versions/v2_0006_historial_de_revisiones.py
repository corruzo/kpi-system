"""Historial de revisiones: cada aprobación, devolución (con su motivo) y reapertura de una carga queda guardada.

Hasta ahora `mediciones.nota_revision` guardaba solo la ÚLTIMA revisión: una segunda devolución o la aprobación pisaba el motivo
anterior, y el historial completo solo estaba en la bitácora (que ve el Desarrollador). La tabla `revisiones` lo conserva y lo
muestra a quien carga y a quien revisa.

Datos existentes: se reconstruyen desde la bitácora (APROBACION, OBSERVACION y REAPERTURA con su nota, usuario y fecha). Las cargas
con revisión que la bitácora no tenga (p. ej. las importadas desde Excel) reciben una revisión con sus datos actuales.

Revisión: v2_0006
Anterior: v2_0005
"""
import json
import logging

import sqlalchemy as sa
from alembic import op

revision = "v2_0006"
down_revision = "v2_0005"
branch_labels = None
depends_on = None

log = logging.getLogger("alembic.runtime.migration")
ACCION = {"APROBACION": "aprobada", "OBSERVACION": "devuelta", "REAPERTURA": "reabierta"}


def upgrade() -> None:
    op.create_table(
        "revisiones",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("medicion_id", sa.Integer(), nullable=False),
        sa.Column("accion", sa.String(length=10), nullable=False),
        sa.Column("nota", sa.Text(), nullable=False),
        sa.Column("por_id", sa.Integer(), nullable=False),
        sa.Column("en", sa.DateTime(), nullable=False),
        sa.CheckConstraint("accion IN ('aprobada', 'devuelta', 'reabierta')", name="ck_revisiones_accion"),
        sa.ForeignKeyConstraint(["medicion_id"], ["mediciones.id"]),
        sa.ForeignKeyConstraint(["por_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_revisiones_medicion_id"), "revisiones", ["medicion_id"])
    op.create_index(op.f("ix_revisiones_por_id"), "revisiones", ["por_id"])
    bind = op.get_bind()
    mediciones = {i for (i,) in bind.execute(sa.text("SELECT id FROM mediciones"))}
    usuarios = {i for (i,) in bind.execute(sa.text("SELECT id FROM usuarios"))}
    con_historial: set[int] = set()
    filas = bind.execute(sa.text(
        "SELECT entidad_id, accion, usuario_id, fecha, detalle FROM bitacora "
        "WHERE entidad = 'medicion' AND accion IN ('APROBACION', 'OBSERVACION', 'REAPERTURA') ORDER BY id")).all()
    nuevas = []
    for medicion_id, accion, usuario_id, fecha, detalle in filas:
        if medicion_id not in mediciones or usuario_id not in usuarios:
            continue
        if isinstance(detalle, str):
            detalle = json.loads(detalle)
        nuevas.append({"m": medicion_id, "a": ACCION[accion], "n": (detalle or {}).get("nota", "") or "", "u": usuario_id, "e": fecha})
        con_historial.add(medicion_id)
    for m, accion_actual, nota, por, en in bind.execute(sa.text(
            "SELECT id, estado, nota_revision, revisado_por_id, revisado_en FROM mediciones "
            "WHERE revisado_por_id IS NOT NULL AND estado IN ('aprobado', 'observado')")).all():
        if m not in con_historial and por in usuarios:
            nuevas.append({"m": m, "a": "aprobada" if accion_actual == "aprobado" else "devuelta", "n": nota or "", "u": por, "e": en})
    insertar = sa.text("INSERT INTO revisiones (medicion_id, accion, nota, por_id, en) VALUES (:m, :a, :n, :u, :e)")
    for fila in nuevas:
        bind.execute(insertar, fila)
    if bind.dialect.name == "postgresql":   # igual que el resto de tablas (v2_0002): sin acceso por la API pública de Supabase
        try:
            with bind.begin_nested():
                op.execute(sa.text('ALTER TABLE public."revisiones" ENABLE ROW LEVEL SECURITY'))
        except Exception as e:
            log.warning("No se pudo activar RLS en revisiones: %s. Actívelo a mano: ALTER TABLE public.<tabla> ENABLE ROW LEVEL SECURITY.", e)


def downgrade() -> None:
    op.drop_table("revisiones")
