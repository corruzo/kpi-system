"""python -m app.crear_admin  — crea un administrador desde la consola."""
import getpass

from .bootstrap import crear_admin, preparar_base

if __name__ == "__main__":
    preparar_base()
    usuario = input("Usuario: ").strip()
    nombre = input("Nombre completo: ").strip()
    clave = getpass.getpass("Contraseña (mín. 10 caracteres): ")
    if len(clave) < 10 or clave != getpass.getpass("Repita la contraseña: "):
        raise SystemExit("Las contraseñas no coinciden o son demasiado cortas.")
    crear_admin(usuario, nombre, clave)
    print("Administrador creado.")
