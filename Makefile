# Tareas habituales del proyecto.  `make ayuda` las lista.
.DEFAULT_GOAL := ayuda
PY ?= python

ayuda:  ## Lista de tareas
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-12s %s\n", $$1, $$2}'

instalar:  ## Instala dependencias de desarrollo
	$(PY) -m pip install -r requirements-dev.txt && npm install

lint:  ## Revisión estática (ruff)
	ruff check .

formato:  ## Corrige lo que ruff puede corregir solo
	ruff check . --fix

prueba:  ## Pruebas (SQLite; con SIGT_DATABASE_URL corre contra PostgreSQL)
	$(PY) -m pytest -q

migraciones:  ## Migra una base temporal desde cero y verifica que no hay diferencias con los modelos
	SIGT_DATA_DIR=$$(mktemp -d) sh -c 'alembic upgrade head && alembic check'

css:  ## Recompila el CSS (obligatorio tras cambiar clases Tailwind)
	npm run build:css

auditar:  ## Busca vulnerabilidades conocidas en las dependencias
	pip-audit -r requirements.txt --strict

verificar: lint prueba migraciones css  ## Todo lo que corre el CI
	git diff --exit-code app/static/tailwind.css

arrancar:  ## Servidor local (SQLite en data/)
	$(PY) run.py

respaldo:  ## Respaldo cifrado (pide la frase de paso o usa SIGT_BACKUP_KEY)
	$(PY) -m app.respaldar crear

.PHONY: ayuda instalar lint formato prueba migraciones css auditar verificar arrancar respaldo
