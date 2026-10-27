"""Esquema inicial.

Crea las tablas del sistema. En una base creada antes de Alembic (con `create_all` + la antigua migración aditiva) las
tablas ya existen: no se tocan sus datos y solo se agregan las columnas que falten (como nulables, igual que antes).
En PostgreSQL deja además la bitácora inalterable (trigger) y activa RLS sin políticas.

Revisión: 0001
"""
import logging

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

log = logging.getLogger("alembic.runtime.migration")
TABLAS = ('areas', 'catalogos', 'parametros', 'indicadores', 'usuarios', 'bitacora', 'ejercicios', 'mediciones', 'notas_auditoria')

TRIGGER_BITACORA = """
CREATE OR REPLACE FUNCTION bitacora_inmutable() RETURNS trigger AS $$
BEGIN RAISE EXCEPTION 'La bitácora es inalterable'; END; $$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trg_bitacora_inmutable ON bitacora;
CREATE TRIGGER trg_bitacora_inmutable BEFORE UPDATE OR DELETE ON bitacora
FOR EACH ROW EXECUTE FUNCTION bitacora_inmutable();
"""


def endurecer_postgres(tablas, trigger_bitacora=True) -> None:
    """Bitácora inalterable y RLS sin políticas (la API REST pública de Supabase queda sin acceso).
    Si el rol no tiene permisos no se aborta la migración: se avisa y queda scripts/supabase_hardening.sql."""
    bind = op.get_bind()
    try:
        with bind.begin_nested():
            if trigger_bitacora:
                op.execute(sa.text(TRIGGER_BITACORA))
            for tabla in tablas:
                op.execute(sa.text(f'ALTER TABLE "{tabla}" ENABLE ROW LEVEL SECURITY'))
    except Exception as e:
        log.warning("No se pudo endurecer la base (trigger/RLS): %s. Ejecute scripts/supabase_hardening.sql.", e)


def _crear_o_completar(nombre, *elementos) -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(nombre):
        op.create_table(nombre, *elementos)
        return
    existentes = {c["name"] for c in inspector.get_columns(nombre)}
    for e in elementos:
        if isinstance(e, sa.Column) and e.name not in existentes:
            op.add_column(nombre, sa.Column(e.name, e.type, nullable=True))
            log.warning("Columna %s.%s agregada.", nombre, e.name)


def upgrade() -> None:
    _crear_o_completar('areas',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nombre', sa.String(length=80), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('nombre')
    )
    _crear_o_completar('catalogos',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('tipo', sa.String(length=20), nullable=False),
    sa.Column('valor', sa.String(length=300), nullable=False),
    sa.Column('detalle', sa.Text(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tipo', 'valor')
    )
    _crear_o_completar('parametros',
    sa.Column('clave', sa.String(length=40), nullable=False),
    sa.Column('valor', sa.Text(), nullable=False),
    sa.PrimaryKeyConstraint('clave')
    )
    _crear_o_completar('indicadores',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('codigo', sa.String(length=20), nullable=False),
    sa.Column('nombre', sa.String(length=150), nullable=False),
    sa.Column('objetivo', sa.Text(), nullable=False),
    sa.Column('area_id', sa.Integer(), nullable=False),
    sa.Column('unidad', sa.String(length=20), nullable=False),
    sa.Column('frecuencia', sa.String(length=20), nullable=False),
    sa.Column('sentido', sa.String(length=10), nullable=False),
    sa.Column('formula', sa.String(length=300), nullable=False),
    sa.Column('variables', sa.JSON(), nullable=False),
    sa.Column('meta', sa.Float(), nullable=False),
    sa.Column('limite', sa.Float(), nullable=False),
    sa.Column('activo', sa.Boolean(), nullable=False),
    sa.Column('creado_en', sa.DateTime(), nullable=False),
    sa.Column('constantes', sa.JSON(), nullable=True),
    sa.Column('decimales', sa.Integer(), nullable=True),
    sa.Column('fuente', sa.Text(), nullable=True),
    sa.Column('notas', sa.Text(), nullable=True),
    sa.Column('seguimiento', sa.String(length=20), nullable=True),
    sa.Column('ref_nombre', sa.String(length=200), nullable=True),
    sa.Column('ref_detalle', sa.Text(), nullable=True),
    sa.Column('sigla', sa.String(length=20), nullable=True),
    sa.Column('gerencia', sa.String(length=150), nullable=True),
    sa.Column('lider', sa.String(length=150), nullable=True),
    sa.Column('resp_medicion', sa.String(length=150), nullable=True),
    sa.Column('resp_registro', sa.String(length=150), nullable=True),
    sa.Column('resp_analisis', sa.String(length=150), nullable=True),
    sa.Column('meta_tope', sa.Float(), nullable=True),
    sa.Column('limite_tope', sa.Float(), nullable=True),
    sa.ForeignKeyConstraint(['area_id'], ['areas.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('codigo')
    )
    _crear_o_completar('usuarios',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=50), nullable=False),
    sa.Column('nombre', sa.String(length=120), nullable=False),
    sa.Column('rol', sa.String(length=20), nullable=False),
    sa.Column('area_id', sa.Integer(), nullable=True),
    sa.Column('password_hash', sa.String(length=200), nullable=False),
    sa.Column('activo', sa.Boolean(), nullable=False),
    sa.Column('sesion_v', sa.Integer(), nullable=False),
    sa.Column('tour_visto', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['area_id'], ['areas.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('username')
    )
    _crear_o_completar('bitacora',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('fecha', sa.DateTime(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=True),
    sa.Column('usuario_nombre', sa.String(length=120), nullable=False),
    sa.Column('rol', sa.String(length=20), nullable=False),
    sa.Column('accion', sa.String(length=40), nullable=False),
    sa.Column('entidad', sa.String(length=30), nullable=False),
    sa.Column('entidad_id', sa.Integer(), nullable=True),
    sa.Column('indicador_id', sa.Integer(), nullable=True),
    sa.Column('area_id', sa.Integer(), nullable=True),
    sa.Column('detalle', sa.JSON(), nullable=False),
    sa.Column('prev_hash', sa.String(length=64), nullable=False),
    sa.Column('hash', sa.String(length=64), nullable=False),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    _crear_o_completar('ejercicios',
    sa.Column('anio', sa.Integer(), nullable=False),
    sa.Column('estado', sa.String(length=10), nullable=False),
    sa.Column('cerrado_por_id', sa.Integer(), nullable=True),
    sa.Column('cerrado_en', sa.DateTime(), nullable=True),
    sa.Column('nota', sa.Text(), nullable=True),
    sa.Column('resumen', sa.JSON(), nullable=True),
    sa.Column('reabierto_por_id', sa.Integer(), nullable=True),
    sa.Column('reabierto_en', sa.DateTime(), nullable=True),
    sa.Column('nota_reapertura', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['cerrado_por_id'], ['usuarios.id'], ),
    sa.ForeignKeyConstraint(['reabierto_por_id'], ['usuarios.id'], ),
    sa.PrimaryKeyConstraint('anio')
    )
    _crear_o_completar('mediciones',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('indicador_id', sa.Integer(), nullable=False),
    sa.Column('periodo', sa.String(length=10), nullable=False),
    sa.Column('valores', sa.JSON(), nullable=False),
    sa.Column('resultado', sa.Float(), nullable=False),
    sa.Column('semaforo', sa.String(length=10), nullable=False),
    sa.Column('meta', sa.Float(), nullable=False),
    sa.Column('limite', sa.Float(), nullable=False),
    sa.Column('sentido', sa.String(length=10), nullable=False),
    sa.Column('estado', sa.String(length=12), nullable=False),
    sa.Column('analisis', sa.Text(), nullable=False),
    sa.Column('plan_mejora', sa.Text(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('cargado_por_id', sa.Integer(), nullable=False),
    sa.Column('cargado_en', sa.DateTime(), nullable=False),
    sa.Column('revisado_por_id', sa.Integer(), nullable=True),
    sa.Column('revisado_en', sa.DateTime(), nullable=True),
    sa.Column('nota_revision', sa.Text(), nullable=False),
    sa.Column('formula', sa.Text(), nullable=True),
    sa.Column('constantes', sa.JSON(), nullable=True),
    sa.Column('decimales', sa.Integer(), nullable=True),
    sa.Column('meta_tope', sa.Float(), nullable=True),
    sa.Column('limite_tope', sa.Float(), nullable=True),
    sa.Column('ejercicio', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['cargado_por_id'], ['usuarios.id'], ),
    sa.ForeignKeyConstraint(['indicador_id'], ['indicadores.id'], ),
    sa.ForeignKeyConstraint(['revisado_por_id'], ['usuarios.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('indicador_id', 'periodo')
    )
    _crear_o_completar('notas_auditoria',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('medicion_id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('texto', sa.Text(), nullable=False),
    sa.Column('fecha', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['medicion_id'], ['mediciones.id'], ),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    if op.get_bind().dialect.name == "postgresql":
        endurecer_postgres(TABLAS)


def downgrade() -> None:
    op.drop_table('notas_auditoria')
    op.drop_table('mediciones')
    op.drop_table('ejercicios')
    op.drop_table('bitacora')
    op.drop_table('usuarios')
    op.drop_table('indicadores')
    op.drop_table('parametros')
    op.drop_table('catalogos')
    op.drop_table('areas')
