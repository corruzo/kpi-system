"""Esquema base de la versión 2 (SPE TPV): estructura en árbol, roles y permisos, indicadores con responsable y cargadores, metas.

Reemplaza la cadena 0001–0008 de la versión 1 (los datos de esa versión eran de prueba y se descartan).

Revisión: v2_0001
Anterior: (ninguna)
"""
import sqlalchemy as sa
from alembic import op

revision = 'v2_0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('catalogos',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('tipo', sa.String(length=20), nullable=False),
    sa.Column('valor', sa.String(length=300), nullable=False),
    sa.Column('detalle', sa.Text(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tipo', 'valor')
    )
    op.create_table('intentos_fallidos',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('llave', sa.String(length=64), nullable=False),
    sa.Column('fecha', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_intentos_fallidos_fecha'), 'intentos_fallidos', ['fecha'], unique=False)
    op.create_index('ix_intentos_fallidos_llave_fecha', 'intentos_fallidos', ['llave', 'fecha'], unique=False)
    op.create_table('parametros',
    sa.Column('clave', sa.String(length=40), nullable=False),
    sa.Column('valor', sa.Text(), nullable=False),
    sa.PrimaryKeyConstraint('clave')
    )
    op.create_table('roles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nombre', sa.String(length=60), nullable=False),
    sa.Column('descripcion', sa.Text(), nullable=False),
    sa.Column('de_sistema', sa.Boolean(), nullable=False),
    sa.Column('clave', sa.String(length=20), nullable=True),
    sa.CheckConstraint("clave IS NULL OR clave IN ('desarrollador', 'coordinador')", name='ck_roles_clave'),
    sa.CheckConstraint('de_sistema = (clave IS NOT NULL)', name='ck_roles_de_sistema'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('clave'),
    sa.UniqueConstraint('nombre')
    )
    op.create_table('unidades',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nombre', sa.String(length=80), nullable=False),
    sa.Column('nivel', sa.String(length=15), nullable=False),
    sa.Column('padre_id', sa.Integer(), nullable=True),
    sa.Column('ruta', sa.String(length=80), nullable=False),
    sa.CheckConstraint("(nivel = 'gerencia') = (padre_id IS NULL)", name='ck_unidades_raiz'),
    sa.CheckConstraint("nivel IN ('gerencia', 'departamento', 'jefatura')", name='ck_unidades_nivel'),
    sa.ForeignKeyConstraint(['padre_id'], ['unidades.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('padre_id', 'nombre', name='uq_unidades_padre_nombre'),
    sa.UniqueConstraint('ruta')
    )
    op.create_index(op.f('ix_unidades_padre_id'), 'unidades', ['padre_id'], unique=False)
    op.create_index('uq_unidades_gerencia_nombre', 'unidades', ['nombre'], unique=True, sqlite_where=sa.text('padre_id IS NULL'), postgresql_where=sa.text('padre_id IS NULL'))
    op.create_table('rol_permisos',
    sa.Column('rol_id', sa.Integer(), nullable=False),
    sa.Column('permiso', sa.String(length=40), nullable=False),
    sa.Column('nivel', sa.String(length=10), nullable=False),
    sa.CheckConstraint("nivel IN ('ver', 'modificar')", name='ck_rol_permisos_nivel'),
    sa.ForeignKeyConstraint(['rol_id'], ['roles.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('rol_id', 'permiso')
    )
    op.create_table('usuarios',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=50), nullable=False),
    sa.Column('nombre', sa.String(length=120), nullable=False),
    sa.Column('email', sa.String(length=120), nullable=True),
    sa.Column('rol_id', sa.Integer(), nullable=True),
    sa.Column('ambito_raiz', sa.Boolean(), nullable=False),
    sa.Column('password_hash', sa.String(length=200), nullable=False),
    sa.Column('activo', sa.Boolean(), nullable=False),
    sa.Column('sesion_v', sa.Integer(), nullable=False),
    sa.Column('tour_visto', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['rol_id'], ['roles.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('username')
    )
    op.create_index(op.f('ix_usuarios_rol_id'), 'usuarios', ['rol_id'], unique=False)
    op.create_table('bitacora',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('fecha', sa.DateTime(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=True),
    sa.Column('usuario_nombre', sa.String(length=120), nullable=False),
    sa.Column('rol', sa.String(length=60), nullable=False),
    sa.Column('accion', sa.String(length=40), nullable=False),
    sa.Column('entidad', sa.String(length=30), nullable=False),
    sa.Column('entidad_id', sa.Integer(), nullable=True),
    sa.Column('indicador_id', sa.Integer(), nullable=True),
    sa.Column('nodo_id', sa.Integer(), nullable=True),
    sa.Column('detalle', sa.JSON(), nullable=False),
    sa.Column('prev_hash', sa.String(length=64), nullable=False),
    sa.Column('hash', sa.String(length=64), nullable=False),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bitacora_accion'), 'bitacora', ['accion'], unique=False)
    op.create_index(op.f('ix_bitacora_indicador_id'), 'bitacora', ['indicador_id'], unique=False)
    op.create_index(op.f('ix_bitacora_usuario_id'), 'bitacora', ['usuario_id'], unique=False)
    op.create_table('ejercicios',
    sa.Column('anio', sa.Integer(), nullable=False),
    sa.Column('estado', sa.String(length=10), nullable=False),
    sa.Column('cerrado_por_id', sa.Integer(), nullable=True),
    sa.Column('cerrado_en', sa.DateTime(), nullable=True),
    sa.Column('nota', sa.Text(), nullable=False),
    sa.Column('resumen', sa.JSON(), nullable=True),
    sa.Column('reabierto_por_id', sa.Integer(), nullable=True),
    sa.Column('reabierto_en', sa.DateTime(), nullable=True),
    sa.Column('nota_reapertura', sa.Text(), nullable=False),
    sa.Column('creado_por_id', sa.Integer(), nullable=True),
    sa.Column('creado_en', sa.DateTime(), nullable=True),
    sa.CheckConstraint("estado IN ('abierto', 'cerrado')", name='ck_ejercicios_estado'),
    sa.ForeignKeyConstraint(['cerrado_por_id'], ['usuarios.id'], ),
    sa.ForeignKeyConstraint(['creado_por_id'], ['usuarios.id'], ),
    sa.ForeignKeyConstraint(['reabierto_por_id'], ['usuarios.id'], ),
    sa.PrimaryKeyConstraint('anio')
    )
    op.create_index(op.f('ix_ejercicios_cerrado_por_id'), 'ejercicios', ['cerrado_por_id'], unique=False)
    op.create_index(op.f('ix_ejercicios_creado_por_id'), 'ejercicios', ['creado_por_id'], unique=False)
    op.create_index(op.f('ix_ejercicios_reabierto_por_id'), 'ejercicios', ['reabierto_por_id'], unique=False)
    op.create_table('indicadores',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('codigo', sa.String(length=20), nullable=False),
    sa.Column('nombre', sa.String(length=150), nullable=False),
    sa.Column('objetivo', sa.Text(), nullable=False),
    sa.Column('nodo_id', sa.Integer(), nullable=False),
    sa.Column('responsable_id', sa.Integer(), nullable=True),
    sa.Column('unidad', sa.String(length=20), nullable=False),
    sa.Column('frecuencia', sa.String(length=20), nullable=False),
    sa.Column('sentido', sa.String(length=10), nullable=False),
    sa.Column('formula', sa.String(length=300), nullable=False),
    sa.Column('variables', sa.JSON(), nullable=False),
    sa.Column('nivel_optimo', sa.Float(), nullable=False),
    sa.Column('limite', sa.Float(), nullable=False),
    sa.Column('activo', sa.Boolean(), nullable=False),
    sa.Column('creado_en', sa.DateTime(), nullable=False),
    sa.Column('constantes', sa.JSON(), nullable=False),
    sa.Column('decimales', sa.Integer(), nullable=False),
    sa.Column('fuente', sa.Text(), nullable=False),
    sa.Column('notas', sa.Text(), nullable=False),
    sa.Column('seguimiento', sa.String(length=20), nullable=False),
    sa.Column('ref_nombre', sa.String(length=200), nullable=False),
    sa.Column('ref_detalle', sa.Text(), nullable=False),
    sa.Column('sigla', sa.String(length=20), nullable=False),
    sa.Column('gerencia', sa.String(length=150), nullable=False),
    sa.Column('lider', sa.String(length=150), nullable=False),
    sa.Column('resp_medicion', sa.String(length=150), nullable=False),
    sa.Column('resp_registro', sa.String(length=150), nullable=False),
    sa.Column('resp_analisis', sa.String(length=150), nullable=False),
    sa.Column('nivel_optimo_tope', sa.Float(), nullable=True),
    sa.Column('limite_tope', sa.Float(), nullable=True),
    sa.CheckConstraint("frecuencia IN ('mensual', 'bimestral', 'trimestral', 'cuatrimestral', 'semestral', 'anual', 'eventual')", name='ck_indicadores_frecuencia'),
    sa.CheckConstraint("seguimiento IN ('proceso', 'objetivo', 'proveedor')", name='ck_indicadores_seguimiento'),
    sa.CheckConstraint("sentido IN ('mayor', 'menor')", name='ck_indicadores_sentido'),
    sa.CheckConstraint('decimales BETWEEN 0 AND 6', name='ck_indicadores_decimales'),
    sa.ForeignKeyConstraint(['nodo_id'], ['unidades.id'], ),
    sa.ForeignKeyConstraint(['responsable_id'], ['usuarios.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('codigo')
    )
    op.create_index(op.f('ix_indicadores_nodo_id'), 'indicadores', ['nodo_id'], unique=False)
    op.create_index(op.f('ix_indicadores_responsable_id'), 'indicadores', ['responsable_id'], unique=False)
    op.create_table('usuario_unidades',
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('unidad_id', sa.Integer(), nullable=False),
    sa.Column('tipo', sa.String(length=10), nullable=False),
    sa.CheckConstraint("tipo IN ('ambito', 'miembro')", name='ck_usuario_unidades_tipo'),
    sa.ForeignKeyConstraint(['unidad_id'], ['unidades.id'], ),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('usuario_id', 'unidad_id')
    )
    op.create_index(op.f('ix_usuario_unidades_unidad_id'), 'usuario_unidades', ['unidad_id'], unique=False)
    op.create_table('indicador_cargadores',
    sa.Column('indicador_id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['indicador_id'], ['indicadores.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ),
    sa.PrimaryKeyConstraint('indicador_id', 'usuario_id')
    )
    op.create_index(op.f('ix_indicador_cargadores_usuario_id'), 'indicador_cargadores', ['usuario_id'], unique=False)
    op.create_table('mediciones',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('indicador_id', sa.Integer(), nullable=False),
    sa.Column('periodo', sa.String(length=10), nullable=False),
    sa.Column('valores', sa.JSON(), nullable=False),
    sa.Column('resultado', sa.Float(), nullable=False),
    sa.Column('semaforo', sa.String(length=10), nullable=False),
    sa.Column('nivel_optimo', sa.Float(), nullable=False),
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
    sa.Column('formula', sa.Text(), nullable=False),
    sa.Column('constantes', sa.JSON(), nullable=False),
    sa.Column('decimales', sa.Integer(), nullable=False),
    sa.Column('nivel_optimo_tope', sa.Float(), nullable=True),
    sa.Column('limite_tope', sa.Float(), nullable=True),
    sa.Column('meta', sa.Float(), nullable=True),
    sa.Column('ejercicio', sa.Integer(), nullable=False),
    sa.CheckConstraint("estado IN ('enviado', 'aprobado', 'observado')", name='ck_mediciones_estado'),
    sa.CheckConstraint("semaforo IN ('verde', 'amarillo', 'rojo')", name='ck_mediciones_semaforo'),
    sa.CheckConstraint("sentido IN ('mayor', 'menor')", name='ck_mediciones_sentido'),
    sa.ForeignKeyConstraint(['cargado_por_id'], ['usuarios.id'], ),
    sa.ForeignKeyConstraint(['indicador_id'], ['indicadores.id'], ),
    sa.ForeignKeyConstraint(['revisado_por_id'], ['usuarios.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('indicador_id', 'periodo')
    )
    op.create_index(op.f('ix_mediciones_cargado_en'), 'mediciones', ['cargado_en'], unique=False)
    op.create_index(op.f('ix_mediciones_cargado_por_id'), 'mediciones', ['cargado_por_id'], unique=False)
    op.create_index(op.f('ix_mediciones_ejercicio'), 'mediciones', ['ejercicio'], unique=False)
    op.create_index(op.f('ix_mediciones_estado'), 'mediciones', ['estado'], unique=False)
    op.create_index(op.f('ix_mediciones_revisado_por_id'), 'mediciones', ['revisado_por_id'], unique=False)
    op.create_table('metas',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('ejercicio', sa.Integer(), nullable=False),
    sa.Column('indicador_id', sa.Integer(), nullable=False),
    sa.Column('periodo', sa.String(length=10), nullable=False),
    sa.Column('valor', sa.Float(), nullable=False),
    sa.Column('actualizado_por_id', sa.Integer(), nullable=True),
    sa.Column('actualizado_en', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['actualizado_por_id'], ['usuarios.id'], ),
    sa.ForeignKeyConstraint(['ejercicio'], ['ejercicios.anio'], ),
    sa.ForeignKeyConstraint(['indicador_id'], ['indicadores.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('indicador_id', 'periodo')
    )
    op.create_index(op.f('ix_metas_actualizado_por_id'), 'metas', ['actualizado_por_id'], unique=False)
    op.create_index(op.f('ix_metas_ejercicio'), 'metas', ['ejercicio'], unique=False)
    op.create_table('notas_auditoria',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('medicion_id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('texto', sa.Text(), nullable=False),
    sa.Column('fecha', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['medicion_id'], ['mediciones.id'], ),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notas_auditoria_medicion_id'), 'notas_auditoria', ['medicion_id'], unique=False)
    op.create_index(op.f('ix_notas_auditoria_usuario_id'), 'notas_auditoria', ['usuario_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_notas_auditoria_usuario_id'), table_name='notas_auditoria')
    op.drop_index(op.f('ix_notas_auditoria_medicion_id'), table_name='notas_auditoria')
    op.drop_table('notas_auditoria')
    op.drop_index(op.f('ix_metas_ejercicio'), table_name='metas')
    op.drop_index(op.f('ix_metas_actualizado_por_id'), table_name='metas')
    op.drop_table('metas')
    op.drop_index(op.f('ix_mediciones_revisado_por_id'), table_name='mediciones')
    op.drop_index(op.f('ix_mediciones_estado'), table_name='mediciones')
    op.drop_index(op.f('ix_mediciones_ejercicio'), table_name='mediciones')
    op.drop_index(op.f('ix_mediciones_cargado_por_id'), table_name='mediciones')
    op.drop_index(op.f('ix_mediciones_cargado_en'), table_name='mediciones')
    op.drop_table('mediciones')
    op.drop_index(op.f('ix_indicador_cargadores_usuario_id'), table_name='indicador_cargadores')
    op.drop_table('indicador_cargadores')
    op.drop_index(op.f('ix_usuario_unidades_unidad_id'), table_name='usuario_unidades')
    op.drop_table('usuario_unidades')
    op.drop_index(op.f('ix_indicadores_responsable_id'), table_name='indicadores')
    op.drop_index(op.f('ix_indicadores_nodo_id'), table_name='indicadores')
    op.drop_table('indicadores')
    op.drop_index(op.f('ix_ejercicios_reabierto_por_id'), table_name='ejercicios')
    op.drop_index(op.f('ix_ejercicios_creado_por_id'), table_name='ejercicios')
    op.drop_index(op.f('ix_ejercicios_cerrado_por_id'), table_name='ejercicios')
    op.drop_table('ejercicios')
    op.drop_index(op.f('ix_bitacora_usuario_id'), table_name='bitacora')
    op.drop_index(op.f('ix_bitacora_indicador_id'), table_name='bitacora')
    op.drop_index(op.f('ix_bitacora_accion'), table_name='bitacora')
    op.drop_table('bitacora')
    op.drop_index(op.f('ix_usuarios_rol_id'), table_name='usuarios')
    op.drop_table('usuarios')
    op.drop_table('rol_permisos')
    op.drop_index('uq_unidades_gerencia_nombre', table_name='unidades', sqlite_where=sa.text('padre_id IS NULL'), postgresql_where=sa.text('padre_id IS NULL'))
    op.drop_index(op.f('ix_unidades_padre_id'), table_name='unidades')
    op.drop_table('unidades')
    op.drop_table('roles')
    op.drop_table('parametros')
    op.drop_index('ix_intentos_fallidos_llave_fecha', table_name='intentos_fallidos')
    op.drop_index(op.f('ix_intentos_fallidos_fecha'), table_name='intentos_fallidos')
    op.drop_table('intentos_fallidos')
    op.drop_table('catalogos')
