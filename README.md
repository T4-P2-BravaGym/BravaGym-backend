# Brava · API

API de Brava, gimnasio de fuerza para mujeres: reservas de clases, entrenamiento personal, rutinas, tienda, pagos y bajas, con cuatro roles (`member`, `trainer`, `admin`, `superadmin`).

**Stack:** Python 3.11+, FastAPI, SQLite, SQLAlchemy 2, Pydantic 2, pytest. La documentación interactiva está en [`/docs`](http://localhost:8000/docs) (Swagger).

## Arrancar en local

```bash
python3 -m venv .venv
source .venv/bin/activate          # con fish: source .venv/bin/activate.fish
pip install -r requirements-dev.txt
cp .env.example .env               # y pon un SECRET_KEY de verdad:
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
uvicorn app.main:app --reload      # http://localhost:8000/docs
pytest                             # tests
```

## Estructura (MVC)

```
app/
  main.py            # crea la app, CORS, errores y monta los routers en /api/v1
  core/              # configuración, base de datos, seguridad (JWT, bcrypt), logging, errores
  models/            # Model: tablas SQLAlchemy (ver docs/er.md)
  schemas/           # View: esquemas Pydantic de entrada y salida
  routers/           # Controller: endpoints finos que llaman a los servicios
  services/          # Reglas de negocio (RN-xx), sin nada de HTTP
tests/
  conftest.py        # BD SQLite en memoria y cliente de pruebas
  unit/              # tests de servicios y reglas de negocio
  integration/       # tests de endpoints: permisos, IDOR, errores
scripts/seed.py      # datos de prueba
docs/                # diagrama ER, reglas de negocio, mapa de endpoints y permisos
```

Cada archivo empieza con un comentario que dice qué va dentro y en qué historia (`TODO(HU-12)`). Lo que ya funciona es la base: configuración, base de datos, manejo de errores, CORS y `/health`.

## Cómo trabajamos

Todo está en [`AGENTS.md`](AGENTS.md): la IA como mentora, idioma, DRY y SOLID, MVC, seguridad, ramas, Conventional Commits y Definition of Done. Las tareas están en el GitHub Project **Brava** de la organización.

Antes de abrir una PR:

```bash
pytest
pip-audit -r requirements.txt
```
