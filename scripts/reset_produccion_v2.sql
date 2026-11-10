-- ============================================================================================================
-- REINICIO LIMPIO PARA LA VERSIÓN 2 (SPE TPV)  ·  DESTRUCTIVO E IRREVERSIBLE
-- Borra TODO el esquema `public` (tablas, datos, bitácora, alembic_version) y lo deja vacío.
-- NO lo ejecute sin antes: (1) hacer y verificar un respaldo (docs/OPERACION.md, «Reinicio a la versión 2»),
-- (2) confirmar que está conectado a la base correcta. Se ejecuta en el SQL Editor de Supabase.
-- Después: redesplegar (las migraciones crean el esquema v2) y crear el primer Desarrollador con
-- SIGT_ADMIN_USER / SIGT_ADMIN_PASSWORD.
-- ============================================================================================================
DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;
GRANT USAGE ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO postgres;
-- Los roles públicos de Supabase no deben tener acceso (la migración v2_0002 lo reafirma):
REVOKE ALL ON SCHEMA public FROM anon, authenticated;
