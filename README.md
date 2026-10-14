# Brava · API

API de Brava, gimnasio de fuerza para mujeres: reservas de clases, entrenamiento personal, rutinas, tienda, pagos y bajas, con cuatro roles (`member`, `trainer`, `admin`, `superadmin`).

**Stack:** Python 3.11+, FastAPI, SQLite, SQLAlchemy 2, Alembic, Pydantic 2, pytest. La documentación interactiva está en [`/docs`](http://localhost:8000/docs) (Swagger).

## Arrancar en local

```bash
python3 -m venv .venv
source .venv/bin/activate          # con fish: source .venv/bin/activate.fish
pip install -r requirements-dev.txt
cp .env.example .env               # y pon un SECRET_KEY de verdad:
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
alembic upgrade head               # crea las tablas (la API ya no las crea al arrancar)
python -m scripts.seed             # opcional: datos de prueba (solo con ENVIRONMENT=local)
uvicorn app.main:app --reload      # http://localhost:8000/docs
pytest                             # tests
```
## Migraciones de base de datos

El esquema se gestiona con [Alembic](https://alembic.sqlalchemy.org/). **Cualquier cambio de modelo lleva su migración.**

```bash
alembic upgrade head                                     # aplica las migraciones pendientes
alembic revision --autogenerate -m "short description"   # genera una migración tras cambiar un modelo
alembic check                                            # falla si hay cambios de modelo sin migración
alembic downgrade -1                                     # deshace la última migración
```

Cuando cambies un modelo:

1. Edita el modelo en `app/models/`.
2. Genera la migración y **revísala** en `migrations/versions/`: autogenerate no lo detecta todo (por ejemplo, renombrados o índices parciales).
3. Aplícala con `alembic upgrade head`.
4. Haz commit del modelo y de su migración juntos.

Empezar de cero (se pierden los datos locales):

```bash
rm brava.db && alembic upgrade head && python -m scripts.seed
```

Los tests no usan Alembic (BD en memoria con `create_all`), pero `tests/integration/test_migrations.py` comprueba que las migraciones producen el mismo esquema que los modelos.

## Estructura (MVC)

```
app/
  main.py            # crea la app, CORS, errores y monta los routers en /api/v1
  core/              # configuración, BD, seguridad (JWT, bcrypt), caché, rate limit, logging, errores
  models/            # Model: tablas SQLAlchemy (ver docs/er.md)
  schemas/           # View: esquemas Pydantic de entrada y salida
  routers/           # Controller: endpoints finos que llaman a los servicios
  services/          # Reglas de negocio (RN-xx), sin nada de HTTP
migrations/          # migraciones de Alembic (una por cambio de esquema)
tests/
  conftest.py        # BD SQLite en memoria y cliente de pruebas
  unit/              # tests de servicios y reglas de negocio
  integration/       # tests de endpoints: permisos, IDOR, errores
scripts/seed.py      # datos de prueba
docs/                # diagrama ER, reglas de negocio, mapa de endpoints y permisos
```

Cada archivo empieza con un comentario que dice qué va dentro y en qué historia (`TODO(HU-12)`). Lo que ya funciona es la base: configuración, base de datos, manejo de errores, CORS y `/health`.

## Límite de intentos (login y registro)

`POST /auth/login` y `POST /auth/register` usan un limitador **en memoria** (`app/core/rate_limit.py`, HU-34): marcas de tiempo por clave (email+IP en login, IP en registro). Los umbrales van en `.env` (`AUTH_LOGIN_*`, `AUTH_REGISTER_*`). Si se supera el límite, la API responde **429** con cabecera `Retry-After`.

**Solo vale con un proceso.** Varios workers de Uvicorn (o varias réplicas) no comparten el contador; cada uno tiene el suyo. Para producción multi-proceso haría falta un almacén compartido (p. ej. Redis).

## Cómo trabajamos

Todo está en [`AGENTS.md`](AGENTS.md): la IA como mentora, idioma, DRY y SOLID, MVC, seguridad, ramas, Conventional Commits y Definition of Done. Las tareas están en el GitHub Project **Brava** de la organización.

Antes de abrir una PR:

```bash
alembic check
pytest
pip-audit -r requirements.txt
```