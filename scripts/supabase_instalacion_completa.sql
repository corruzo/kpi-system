-- ============================================================================================================
-- SPE TPV · INSTALACIÓN COMPLETA DE LA BASE DE DATOS (Supabase / PostgreSQL) · revisión v2_0007
-- GENERADO por scripts/generar_sql_supabase.py: no se edita a mano (una prueba verifica que coincida con los modelos).
--
-- ¡DESTRUCTIVO E IRREVERSIBLE! Borra TODO el esquema `public` (tablas, datos, bitácora) y lo crea de nuevo, vacío.
-- Ejecútelo SOLO en la base correcta, en el SQL Editor de Supabase, de una sola vez.
--
-- Después de ejecutarlo:
--   1. Defina en el despliegue SIGT_ADMIN_USER y SIGT_ADMIN_PASSWORD (10+ caracteres): al arrancar con la base vacía la
--      aplicación crea el primer Desarrollador y siembra los roles de sistema y los parámetros. Elimine la contraseña luego.
--   2. La aplicación ve `alembic_version` = v2_0007: no migra nada.
-- ============================================================================================================

BEGIN;

DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;
GRANT USAGE ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO postgres;

-- ----------------------------------------------------------------------------------------------- tablas
CREATE TABLE intentos_fallidos (
	id SERIAL NOT NULL, 
	llave VARCHAR(64) NOT NULL, 
	fecha TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_intentos_fallidos_fecha ON intentos_fallidos (fecha);
CREATE INDEX ix_intentos_fallidos_llave_fecha ON intentos_fallidos (llave, fecha);

CREATE TABLE parametros (
	clave VARCHAR(40) NOT NULL, 
	valor TEXT NOT NULL, 
	PRIMARY KEY (clave)
);

CREATE TABLE roles (
	id SERIAL NOT NULL, 
	nombre VARCHAR(60) NOT NULL, 
	descripcion TEXT NOT NULL, 
	de_sistema BOOLEAN NOT NULL, 
	clave VARCHAR(20), 
	PRIMARY KEY (id), 
	CONSTRAINT ck_roles_clave CHECK (clave IS NULL OR clave IN ('desarrollador', 'coordinador')), 
	CONSTRAINT ck_roles_de_sistema CHECK (de_sistema = (clave IS NOT NULL)), 
	UNIQUE (nombre), 
	UNIQUE (clave)
);

CREATE TABLE unidades (
	id SERIAL NOT NULL, 
	nombre VARCHAR(80) NOT NULL, 
	nivel VARCHAR(15) NOT NULL, 
	padre_id INTEGER, 
	ruta VARCHAR(80) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_unidades_nivel CHECK (nivel IN ('gerencia', 'departamento', 'jefatura')), 
	CONSTRAINT ck_unidades_raiz CHECK ((nivel = 'gerencia') = (padre_id IS NULL)), 
	CONSTRAINT uq_unidades_padre_nombre UNIQUE (padre_id, nombre), 
	FOREIGN KEY(padre_id) REFERENCES unidades (id), 
	UNIQUE (ruta)
);
CREATE INDEX ix_unidades_padre_id ON unidades (padre_id);
CREATE UNIQUE INDEX uq_unidades_gerencia_nombre ON unidades (nombre) WHERE padre_id IS NULL;

CREATE TABLE rol_permisos (
	rol_id INTEGER NOT NULL, 
	permiso VARCHAR(40) NOT NULL, 
	nivel VARCHAR(10) NOT NULL, 
	PRIMARY KEY (rol_id, permiso), 
	CONSTRAINT ck_rol_permisos_nivel CHECK (nivel IN ('ver', 'modificar')), 
	FOREIGN KEY(rol_id) REFERENCES roles (id) ON DELETE CASCADE
);

CREATE TABLE usuarios (
	id SERIAL NOT NULL, 
	username VARCHAR(50) NOT NULL, 
	nombre VARCHAR(120) NOT NULL, 
	email VARCHAR(120), 
	rol_id INTEGER, 
	ambito_raiz BOOLEAN NOT NULL, 
	password_hash VARCHAR(200) NOT NULL, 
	activo BOOLEAN NOT NULL, 
	sesion_v INTEGER NOT NULL, 
	tour_visto BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (username), 
	FOREIGN KEY(rol_id) REFERENCES roles (id)
);
CREATE INDEX ix_usuarios_rol_id ON usuarios (rol_id);

CREATE TABLE bitacora (
	id SERIAL NOT NULL, 
	fecha TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	usuario_id INTEGER, 
	usuario_nombre VARCHAR(120) NOT NULL, 
	rol VARCHAR(60) NOT NULL, 
	accion VARCHAR(40) NOT NULL, 
	entidad VARCHAR(30) NOT NULL, 
	entidad_id INTEGER, 
	indicador_id INTEGER, 
	nodo_id INTEGER, 
	detalle JSON NOT NULL, 
	prev_hash VARCHAR(64) NOT NULL, 
	hash VARCHAR(64) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id)
);
CREATE INDEX ix_bitacora_accion ON bitacora (accion);
CREATE INDEX ix_bitacora_indicador_id ON bitacora (indicador_id);
CREATE INDEX ix_bitacora_usuario_id ON bitacora (usuario_id);

CREATE TABLE ejercicios (
	anio SERIAL NOT NULL, 
	estado VARCHAR(10) NOT NULL, 
	cerrado_por_id INTEGER, 
	cerrado_en TIMESTAMP WITHOUT TIME ZONE, 
	nota TEXT NOT NULL, 
	resumen JSON, 
	reabierto_por_id INTEGER, 
	reabierto_en TIMESTAMP WITHOUT TIME ZONE, 
	nota_reapertura TEXT NOT NULL, 
	creado_por_id INTEGER, 
	creado_en TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (anio), 
	CONSTRAINT ck_ejercicios_estado CHECK (estado IN ('abierto', 'cerrado')), 
	FOREIGN KEY(cerrado_por_id) REFERENCES usuarios (id), 
	FOREIGN KEY(reabierto_por_id) REFERENCES usuarios (id), 
	FOREIGN KEY(creado_por_id) REFERENCES usuarios (id)
);
CREATE INDEX ix_ejercicios_cerrado_por_id ON ejercicios (cerrado_por_id);
CREATE INDEX ix_ejercicios_creado_por_id ON ejercicios (creado_por_id);
CREATE INDEX ix_ejercicios_reabierto_por_id ON ejercicios (reabierto_por_id);

CREATE TABLE indicadores (
	id SERIAL NOT NULL, 
	codigo VARCHAR(20) NOT NULL, 
	nombre VARCHAR(150) NOT NULL, 
	objetivo TEXT NOT NULL, 
	nodo_id INTEGER NOT NULL, 
	responsable_id INTEGER, 
	suplente_id INTEGER, 
	unidad VARCHAR(20) NOT NULL, 
	frecuencia VARCHAR(20) NOT NULL, 
	sentido VARCHAR(10) NOT NULL, 
	formula VARCHAR(300) NOT NULL, 
	variables JSON NOT NULL, 
	nivel_optimo FLOAT NOT NULL, 
	limite FLOAT NOT NULL, 
	activo BOOLEAN NOT NULL, 
	archivado_en TIMESTAMP WITHOUT TIME ZONE, 
	creado_en TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	constantes JSON NOT NULL, 
	decimales INTEGER NOT NULL, 
	fuente TEXT NOT NULL, 
	notas TEXT NOT NULL, 
	seguimiento VARCHAR(20) NOT NULL, 
	ref_nombre VARCHAR(200) NOT NULL, 
	ref_detalle TEXT NOT NULL, 
	sigla VARCHAR(20) NOT NULL, 
	gerencia VARCHAR(150) NOT NULL, 
	lider VARCHAR(150) NOT NULL, 
	resp_medicion VARCHAR(150) NOT NULL, 
	resp_registro VARCHAR(150) NOT NULL, 
	resp_analisis VARCHAR(150) NOT NULL, 
	nivel_optimo_tope FLOAT, 
	limite_tope FLOAT, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_indicadores_sentido CHECK (sentido IN ('mayor', 'menor')), 
	CONSTRAINT ck_indicadores_seguimiento CHECK (seguimiento IN ('proceso', 'objetivo', 'proveedor')), 
	CONSTRAINT ck_indicadores_decimales CHECK (decimales BETWEEN 0 AND 6), 
	CONSTRAINT ck_indicadores_suplente CHECK (suplente_id IS NULL OR suplente_id <> responsable_id), 
	CONSTRAINT ck_indicadores_frecuencia CHECK (frecuencia IN ('mensual', 'bimestral', 'trimestral', 'cuatrimestral', 'semestral', 'anual', 'eventual')), 
	UNIQUE (codigo), 
	FOREIGN KEY(nodo_id) REFERENCES unidades (id), 
	FOREIGN KEY(responsable_id) REFERENCES usuarios (id), 
	FOREIGN KEY(suplente_id) REFERENCES usuarios (id)
);
CREATE INDEX ix_indicadores_nodo_id ON indicadores (nodo_id);
CREATE INDEX ix_indicadores_responsable_id ON indicadores (responsable_id);
CREATE INDEX ix_indicadores_suplente_id ON indicadores (suplente_id);

CREATE TABLE usuario_unidades (
	usuario_id INTEGER NOT NULL, 
	unidad_id INTEGER NOT NULL, 
	tipo VARCHAR(10) NOT NULL, 
	PRIMARY KEY (usuario_id, unidad_id), 
	CONSTRAINT ck_usuario_unidades_tipo CHECK (tipo IN ('ambito', 'miembro')), 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE, 
	FOREIGN KEY(unidad_id) REFERENCES unidades (id)
);
CREATE INDEX ix_usuario_unidades_unidad_id ON usuario_unidades (unidad_id);

CREATE TABLE mediciones (
	id SERIAL NOT NULL, 
	indicador_id INTEGER NOT NULL, 
	periodo VARCHAR(10) NOT NULL, 
	valores JSON NOT NULL, 
	resultado FLOAT NOT NULL, 
	semaforo VARCHAR(10) NOT NULL, 
	nivel_optimo FLOAT NOT NULL, 
	limite FLOAT NOT NULL, 
	sentido VARCHAR(10) NOT NULL, 
	estado VARCHAR(12) NOT NULL, 
	analisis TEXT NOT NULL, 
	plan_mejora TEXT NOT NULL, 
	version INTEGER NOT NULL, 
	cargado_por_id INTEGER NOT NULL, 
	cargado_en TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	revisado_por_id INTEGER, 
	revisado_en TIMESTAMP WITHOUT TIME ZONE, 
	nota_revision TEXT NOT NULL, 
	formula TEXT NOT NULL, 
	constantes JSON NOT NULL, 
	decimales INTEGER NOT NULL, 
	nivel_optimo_tope FLOAT, 
	limite_tope FLOAT, 
	meta FLOAT, 
	ejercicio INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (indicador_id, periodo), 
	CONSTRAINT ck_mediciones_estado CHECK (estado IN ('enviado', 'aprobado', 'observado')), 
	CONSTRAINT ck_mediciones_semaforo CHECK (semaforo IN ('verde', 'amarillo', 'rojo')), 
	CONSTRAINT ck_mediciones_sentido CHECK (sentido IN ('mayor', 'menor')), 
	FOREIGN KEY(indicador_id) REFERENCES indicadores (id), 
	FOREIGN KEY(cargado_por_id) REFERENCES usuarios (id), 
	FOREIGN KEY(revisado_por_id) REFERENCES usuarios (id)
);
CREATE INDEX ix_mediciones_cargado_en ON mediciones (cargado_en);
CREATE INDEX ix_mediciones_cargado_por_id ON mediciones (cargado_por_id);
CREATE INDEX ix_mediciones_ejercicio ON mediciones (ejercicio);
CREATE INDEX ix_mediciones_estado ON mediciones (estado);
CREATE INDEX ix_mediciones_revisado_por_id ON mediciones (revisado_por_id);

CREATE TABLE metas (
	id SERIAL NOT NULL, 
	ejercicio INTEGER NOT NULL, 
	indicador_id INTEGER NOT NULL, 
	periodo VARCHAR(10) NOT NULL, 
	valor FLOAT NOT NULL, 
	actualizado_por_id INTEGER, 
	actualizado_en TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (indicador_id, periodo), 
	FOREIGN KEY(ejercicio) REFERENCES ejercicios (anio), 
	FOREIGN KEY(indicador_id) REFERENCES indicadores (id), 
	FOREIGN KEY(actualizado_por_id) REFERENCES usuarios (id)
);
CREATE INDEX ix_metas_actualizado_por_id ON metas (actualizado_por_id);
CREATE INDEX ix_metas_ejercicio ON metas (ejercicio);

CREATE TABLE notificaciones (
	id SERIAL NOT NULL, 
	usuario_id INTEGER NOT NULL, 
	tipo VARCHAR(10) NOT NULL, 
	titulo VARCHAR(160) NOT NULL, 
	texto TEXT NOT NULL, 
	indicador_id INTEGER, 
	periodo VARCHAR(10), 
	creada_en TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	leida_en TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_notificaciones_tipo CHECK (tipo IN ('aprobada', 'devuelta', 'reabierta')), 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE, 
	FOREIGN KEY(indicador_id) REFERENCES indicadores (id)
);
CREATE INDEX ix_notificaciones_creada_en ON notificaciones (creada_en);
CREATE INDEX ix_notificaciones_indicador_id ON notificaciones (indicador_id);
CREATE INDEX ix_notificaciones_usuario_id ON notificaciones (usuario_id);

CREATE TABLE periodos_justificados (
	id SERIAL NOT NULL, 
	indicador_id INTEGER NOT NULL, 
	periodo VARCHAR(10) NOT NULL, 
	ejercicio INTEGER NOT NULL, 
	tipo VARCHAR(20) NOT NULL, 
	motivo TEXT NOT NULL, 
	por_id INTEGER NOT NULL, 
	en TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (indicador_id, periodo), 
	CONSTRAINT ck_periodos_justificados_tipo CHECK (tipo IN ('parada_planta', 'inicio_medicion', 'no_aplica')), 
	FOREIGN KEY(indicador_id) REFERENCES indicadores (id) ON DELETE CASCADE, 
	FOREIGN KEY(por_id) REFERENCES usuarios (id)
);
CREATE INDEX ix_periodos_justificados_ejercicio ON periodos_justificados (ejercicio);
CREATE INDEX ix_periodos_justificados_por_id ON periodos_justificados (por_id);

CREATE TABLE notas_auditoria (
	id SERIAL NOT NULL, 
	medicion_id INTEGER NOT NULL, 
	usuario_id INTEGER NOT NULL, 
	texto TEXT NOT NULL, 
	fecha TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(medicion_id) REFERENCES mediciones (id), 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id)
);
CREATE INDEX ix_notas_auditoria_medicion_id ON notas_auditoria (medicion_id);
CREATE INDEX ix_notas_auditoria_usuario_id ON notas_auditoria (usuario_id);

CREATE TABLE revisiones (
	id SERIAL NOT NULL, 
	medicion_id INTEGER NOT NULL, 
	accion VARCHAR(10) NOT NULL, 
	nota TEXT NOT NULL, 
	por_id INTEGER NOT NULL, 
	en TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_revisiones_accion CHECK (accion IN ('aprobada', 'devuelta', 'reabierta')), 
	FOREIGN KEY(medicion_id) REFERENCES mediciones (id), 
	FOREIGN KEY(por_id) REFERENCES usuarios (id)
);
CREATE INDEX ix_revisiones_medicion_id ON revisiones (medicion_id);
CREATE INDEX ix_revisiones_por_id ON revisiones (por_id);

-- ------------------------------------------------------------------------------------- control de versión (Alembic)
CREATE TABLE alembic_version (
	version_num VARCHAR(32) NOT NULL,
	CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);
INSERT INTO alembic_version (version_num) VALUES ('v2_0007');

-- -------------------------------------------------------------------------------- endurecimiento (migración v2_0002)
-- Bitácora inalterable a nivel de motor:
CREATE OR REPLACE FUNCTION public.bitacora_inmutable() RETURNS trigger AS $$
BEGIN RAISE EXCEPTION 'La bitácora es inalterable'; END; $$ LANGUAGE plpgsql SET search_path = '';
DROP TRIGGER IF EXISTS trg_bitacora_inmutable ON public.bitacora;
CREATE TRIGGER trg_bitacora_inmutable BEFORE UPDATE OR DELETE ON public.bitacora
FOR EACH ROW EXECUTE FUNCTION public.bitacora_inmutable();

-- RLS sin políticas en todas las tablas: la API pública de Supabase (anon/authenticated) no lee ni escribe.
-- La aplicación se conecta con el rol postgres, que ignora RLS.
ALTER TABLE public."intentos_fallidos" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."parametros" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."roles" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."unidades" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."rol_permisos" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."usuarios" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."bitacora" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."ejercicios" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."indicadores" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."usuario_unidades" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."mediciones" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."metas" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."notificaciones" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."periodos_justificados" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."notas_auditoria" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."revisiones" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."alembic_version" ENABLE ROW LEVEL SECURITY;

-- Sin permisos para los roles públicos de Supabase (solo si existen):
DO $$
BEGIN
	IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname IN ('anon', 'authenticated')) THEN
		EXECUTE 'REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated';
		EXECUTE 'REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated';
		EXECUTE 'ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM anon, authenticated';
		EXECUTE 'ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM anon, authenticated';
	END IF;
END $$;

COMMIT;
