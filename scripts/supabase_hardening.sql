-- ============================================================================================================
-- SPE TPV · ENDURECIMIENTO DE LA BASE (Supabase / PostgreSQL) · idempotente
-- GENERADO por scripts/generar_sql_supabase.py: no se edita a mano.
-- La migración v2_0002 ya intenta aplicar esto al desplegar; este script es el respaldo manual si no pudo hacerlo.
-- Ejecutar en el SQL Editor de Supabase. No borra ni modifica datos.
-- ============================================================================================================
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
