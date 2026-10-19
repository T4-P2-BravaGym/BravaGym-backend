# Brava · Backend

Brava is a full-stack application for a women's strength-training gym, built as a team bootcamp project. It brings class bookings, memberships, training routines and shop orders into one place, with separate access for members, trainers, administrators and superadministrators.

This repository contains the API. The [frontend repository](https://github.com/T4-P2-BravaGym/BravaGym-frontend/tree/dev) contains the React application and its setup instructions. The application interface is in Spanish.

## Features

- Registration, login, session renewal, logout and password recovery.
- Membership plans, subscriptions, class bookings, waiting lists and personal training.
- Trainer profiles and photos, exercises and member routines.
- Products, orders, discount codes and payment records.
- Administration of users, plans, products, payments and membership cancellations.

Payments on the integrated demo use a simulated flow. Password-recovery messages are written to a private local `outbox/` directory rather than sent by email.

## Tech stack

| Technology | Version / requirement |
| --- | --- |
| Python | 3.12 (CI version) |
| FastAPI | >=0.143.2, <1.0 |
| SQLAlchemy | >=2.1.4, <2.2 |
| Pydantic | >=2.14.1, <3 |
| Alembic | >=1.20.0, <2 |
| Database | SQLite |
| Tests | pytest, pytest-cov |

Python dependencies use the ranges in [requirements.txt](requirements.txt) and [requirements-dev.txt](requirements-dev.txt); they are not an exact version lock.

## Run locally

Requirements: Git and Python 3.12. These commands use a macOS/Linux shell; on Windows, activate the virtual environment with `.venv\Scripts\Activate.ps1` in PowerShell.

```bash
git clone --branch dev https://github.com/T4-P2-BravaGym/BravaGym-backend.git
cd BravaGym-backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copy the generated value into `SECRET_KEY` in `.env`, replacing `change-me`. Keep the local defaults below; all settings are listed in [.env.example](.env.example).

```dotenv
ENVIRONMENT=local
DATABASE_URL=sqlite:///./brava.db
CORS_ORIGINS=["http://localhost:5173"]
FRONTEND_URL=http://localhost:5173
```

Then create the database, load the demo data and start the API:

```bash
alembic upgrade head
python -m scripts.seed
uvicorn app.main:app --reload
```

Run the seed only on an empty local database. For an existing installation, keep your `.env` and data, and apply pending migrations with `alembic upgrade head`. Keep the SQLite database and `media/` directory together to preserve uploaded photos.

## Usage

Open [Swagger](http://localhost:8000/docs), select **Authorize**, and enter a demo email as `username` with password `BravaDemo2026!`. Try `GET /api/v1/users/me` after signing in. The password is the seed default unless `SEED_PASSWORD` was set.

| Role | Demo email |
| --- | --- |
| Member | `lucia@example.com` |
| Trainer | `ana@example.com` |
| Administrator | `admin@example.com` |
| Superadministrator | `superadmin@example.com` |

[Health](http://localhost:8000/health) returns `{"status":"ok"}` when the server is running. [ReDoc](http://localhost:8000/redoc) and [OpenAPI JSON](http://localhost:8000/openapi.json) describe the API. Start the frontend separately using its [README](https://github.com/T4-P2-BravaGym/BravaGym-frontend/blob/dev/README.md); use `localhost` for both servers so session cookies work consistently.

## Project structure

```text
app/
  main.py         # Application entry point
  core/           # Configuration, database and security
  models/         # SQLAlchemy database models
  schemas/        # Request and response validation
  routers/        # HTTP endpoints
  services/       # Business rules and database queries
migrations/       # Alembic schema migrations
scripts/seed.py   # Local demo data
tests/            # Unit and integration tests
collections/      # Bruno API requests
docs/             # API reference, data model and business rules
specs/            # Feature specifications
```

## Checks

With the virtual environment activated, run:

```bash
pytest --cov=app --cov-fail-under=80
ruff check app tests
ruff format --check app tests
alembic check
pip-audit -r requirements.txt
```

Apply migrations before `alembic check`; it checks the database configured in `.env`. Tests use their own databases.

## Documentation

- [API and permissions](docs/api.md), [business rules](docs/business-rules.md) and [data model](docs/er.md).
- [Bruno collection and runner guide](docs/api-testing.md).
- [Session contract](specs/HU-33-refresh-logout.md) and [password-recovery contract](specs/HU-35-password-reset.md).
- [Feature specifications](specs/) and [AI-use log](docs/ai-log.md).

## Authors and support

Built by the Brava team: Beste Özaydın, Damaris Castro, Esra Kesken, Mariana and Viviana Andrango. See the [contributors](https://github.com/T4-P2-BravaGym/BravaGym-backend/graphs/contributors).

Report bugs or ask questions through [GitHub Issues](https://github.com/T4-P2-BravaGym/BravaGym-backend/issues).
