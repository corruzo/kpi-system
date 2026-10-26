"""Serialización de escrituras: mantiene íntegra la cadena de hashes de la bitácora dentro de un proceso.
(Entre procesos, en PostgreSQL, lo garantiza un advisory lock en auditoria.registrar.)"""
import threading

candado_escritura = threading.Lock()
