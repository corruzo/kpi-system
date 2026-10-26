# SIGT · Sistema de Indicadores de Gestión — Tripoliven, C.A.

Sistema web local (FastAPI + SQLAlchemy + Alpine.js/Tailwind/Chart.js) para cargar, aprobar y analizar indicadores bajo ISO 9001:2015.

## Arranque
```bash
pip install -r requirements.txt
python run.py            # http://127.0.0.1:8000
pytest                   # pruebas
```
La primera vez se crea `data/sigt.db` (SQLite) con datos de demostración. Contraseña de todos los usuarios demo: `tripoliven2026`
(`j.sistemas`, `j.produccion`, `j.mantenimiento`, …, `gerente`, `admin`). El login tiene botones de acceso rápido por rol.

Variables de entorno: `SIGT_DATABASE_URL` (p. ej. SQL Server `mssql+pyodbc://…`), `SIGT_DEMO=0` (sin datos ni botones demo), `SIGT_SECRET`, `SIGT_HOST`, `SIGT_PORT`, `SIGT_DATA_DIR`.
Tailwind, Alpine y Chart.js se cargan por CDN (el navegador necesita internet; para uso offline descargue los archivos a `app/static/` y cambie los `<script>`).

## Roles
| Rol | Capacidades |
|---|---|
| Jefe de Área | Carga rápida de su área: solo variables base, resultado y semáforo en vivo; análisis y plan de mejora obligatorios (validado también en servidor) si hay Alerta/Crítico; reenvío de cargas devueltas. |
| Gerente / Auditor SGC | Bandeja de aprobación (aprobar / devolver), notas de auditoría, panel Chart.js (tendencia vs meta, semáforos, cumplimiento por área), exportación CSV. |
| Administrador SGC | CRUD de fichas: fórmula validada, variables, unidad, frecuencia, meta y límite crítico, sentido directo o inverso. |

## Reglas clave
- Semáforo «mayor es mejor»: verde ≥ meta, amarillo ≥ límite, rojo < límite; el inverso es simétrico.
- Cada carga guarda la meta/límite vigentes: editar la ficha no altera el histórico.
- Una carga enviada o aprobada no se modifica; solo se reenvía si fue devuelta (versión +1).
- Eliminar un indicador con cargas lo archiva para conservar la trazabilidad.
- Fórmulas con evaluador AST restringido (sin `eval`).
- Bitácora de solo inserción con cadena SHA-256 (`/api/bitacora/verificar`); el ORM bloquea UPDATE/DELETE. Para blindarla en el motor, en SQL Server niegue UPDATE/DELETE sobre `bitacora` al usuario de la aplicación.
