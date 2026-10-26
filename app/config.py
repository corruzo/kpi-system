"""Configuración por variables de entorno (opcionalmente desde un archivo .env)."""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # python-dotenv es opcional
    pass

PRODUCCION = os.getenv("SIGT_ENV", "development").lower() == "production"
TRUST_PROXY = os.getenv("SIGT_TRUST_PROXY", "0") == "1"   # leer X-Forwarded-For (detrás de Render, Fly, Nginx…)
