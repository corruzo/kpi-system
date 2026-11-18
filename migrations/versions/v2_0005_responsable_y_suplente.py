"""Responsable principal y suplente: reemplaza la lista libre de cargadores por exactamente dos personas.

Cada indicador queda con `responsable_id` (principal) y `suplente_id` (corresponsable); los dos cargan datos y ninguno edita la ficha.

Datos existentes: el suplente es el primer cargador (por id) que no sea el responsable; si el indicador no tenía responsable,
el primer cargador pasa a serlo. Los cargadores que no caben (más de dos personas) se descartan y cada caso queda en la bitácora.

Revisión: v2_0005
Anterior: v2_0004
"""
import logging

import sqlalchemy as sa
from alembic import op
from sqlalchemy.orm import Session

revision = "v2_0005"
down_revision = "v2_0004"
branch_labels = None
depends_on = None

log = logging.getLogger("alembic.runtime.migration")


def upgrade() -> None:
    bind = op.get_bind()
    # 1) Se lee ANTES de tocar `indicadores`: en SQLite una reconstrucción de la tabla (batch) borraría en cascada los cargadores.
    filas = bind.execute(sa.text(
        "SELECT c.indicador_id, c.usuario_id, i.responsable_id, i.codigo FROM indicador_cargadores c "
        "JOIN indicadores i ON i.id = c.indicador_id ORDER BY c.indicador_id, c.usuario_id")).all()
    # 2) La columna se agrega sin reconstruir la tabla (SQLite: ALTER ... ADD COLUMN; la regla «suplente ≠ responsable» la valida
    #    el servicio y, en PostgreSQL, además una restricción de la base).
    if bind.dialect.name == "sqlite":
        op.execute(sa.text("ALTER TABLE indicadores ADD COLUMN suplente_id INTEGER REFERENCES usuarios (id)"))
    else:
        op.add_column("indicadores", sa.Column("suplente_id", sa.Integer(), nullable=True))
        op.create_foreign_key("fk_indicadores_suplente_id_usuarios", "indicadores", "usuarios", ["suplente_id"], ["id"])
        op.create_check_constraint("ck_indicadores_suplente", "indicadores", "suplente_id IS NULL OR suplente_id <> responsable_id")
    op.create_index("ix_indicadores_suplente_id", "indicadores", ["suplente_id"])
    # 3) Datos: responsable + primer otro cargador como suplente
    por_indicador: dict[int, dict] = {}
    for indicador_id, usuario_id, responsable_id, codigo in filas:
        d = por_indicador.setdefault(indicador_id, {"codigo": codigo, "responsable": responsable_id, "cargadores": []})
        d["cargadores"].append(usuario_id)
    descartes = []
    for indicador_id, d in por_indicador.items():
        otros = [x for x in d["cargadores"] if x != d["responsable"]]
        responsable = d["responsable"]
        if responsable is None and otros:
            responsable, otros = otros[0], otros[1:]
        suplente, sobran = (otros[0] if otros else None), otros[1:]
        bind.execute(sa.text("UPDATE indicadores SET responsable_id = :r, suplente_id = :s WHERE id = :i"),
                     {"r": responsable, "s": suplente, "i": indicador_id})
        if sobran:
            descartes.append({"indicador_id": indicador_id, "codigo": d["codigo"], "descartados": sobran, "responsable": responsable, "suplente": suplente})
    if descartes:
        _registrar_descartes(bind, descartes)
    op.drop_table("indicador_cargadores")


def _registrar_descartes(bind, descartes: list[dict]) -> None:
    """Deja en la bitácora, por indicador, a quiénes dejaron de cargar al pasar al modelo responsable + suplente."""
    from app.models import Indicador
    from app.servicios import auditoria
    with Session(bind=bind) as db:
        nombres = dict(bind.execute(sa.text("SELECT id, nombre FROM usuarios")).all())
        for d in descartes:
            ind = db.get(Indicador, d["indicador_id"])
            auditoria.registrar(db, None, "INDICADOR_ASIGNADO", "indicador", d["indicador_id"],
                                {"codigo": d["codigo"], "origen": "migración v2_0005 (responsable + suplente)",
                                 "dejan_de_cargar": [nombres.get(x, str(x)) for x in d["descartados"]],
                                 "responsable": nombres.get(d["responsable"]), "suplente": nombres.get(d["suplente"])}, ind)
        db.flush()
    log.warning("v2_0005: %s indicador(es) tenían más de dos cargadores; los sobrantes se descartaron (ver bitácora).", len(descartes))


def downgrade() -> None:
    bind = op.get_bind()
    pares = bind.execute(sa.text("SELECT id, responsable_id, suplente_id FROM indicadores")).all()   # antes de reconstruir la tabla
    with op.batch_alter_table("indicadores") as lote:
        if bind.dialect.name != "sqlite":
            lote.drop_constraint("ck_indicadores_suplente", type_="check")
            lote.drop_constraint("fk_indicadores_suplente_id_usuarios", type_="foreignkey")
        lote.drop_index("ix_indicadores_suplente_id")
        lote.drop_column("suplente_id")
    op.create_table(
        "indicador_cargadores",
        sa.Column("indicador_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["indicador_id"], ["indicadores.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("indicador_id", "usuario_id"),
    )
    op.create_index("ix_indicador_cargadores_usuario_id", "indicador_cargadores", ["usuario_id"])
    for indicador_id, responsable_id, suplente_id in pares:
        for usuario_id in dict.fromkeys(x for x in (responsable_id, suplente_id) if x is not None):
            bind.execute(sa.text("INSERT INTO indicador_cargadores (indicador_id, usuario_id) VALUES (:i, :u)"), {"i": indicador_id, "u": usuario_id})
