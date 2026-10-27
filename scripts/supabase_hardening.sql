-- (Las migraciones de Alembic ya intentan aplicar esto; este script es el respaldo manual.)
-- Ejecutar en el SQL Editor de Supabase si la aplicación no pudo aplicarlo sola.
-- 1) Bitácora inalterable a nivel de motor
CREATE OR REPLACE FUNCTION bitacora_inmutable() RETURNS trigger AS $$
BEGIN RAISE EXCEPTION 'La bitácora es inalterable'; END; $$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trg_bitacora_inmutable ON bitacora;
CREATE TRIGGER trg_bitacora_inmutable BEFORE UPDATE OR DELETE ON bitacora
FOR EACH ROW EXECUTE FUNCTION bitacora_inmutable();

-- 2) RLS sin políticas: la API REST pública de Supabase (anon/authenticated) no puede leer ni escribir.
--    La aplicación se conecta con el rol postgres, que ignora RLS.
ALTER TABLE areas ENABLE ROW LEVEL SECURITY;
ALTER TABLE usuarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE indicadores ENABLE ROW LEVEL SECURITY;
ALTER TABLE mediciones ENABLE ROW LEVEL SECURITY;
ALTER TABLE notas_auditoria ENABLE ROW LEVEL SECURITY;
ALTER TABLE bitacora ENABLE ROW LEVEL SECURITY;
ALTER TABLE parametros ENABLE ROW LEVEL SECURITY;
ALTER TABLE catalogos ENABLE ROW LEVEL SECURITY;
ALTER TABLE ejercicios ENABLE ROW LEVEL SECURITY;
ALTER TABLE intentos_fallidos ENABLE ROW LEVEL SECURITY;
