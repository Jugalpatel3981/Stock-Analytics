# Backend

FastAPI service for the Stock Intelligence Platform.

## Commands

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
pytest
ruff check .
```

## Environment

Copy `.env.example` to `.env` and update values for your local machine.

## Database Initialization

With PostgreSQL running and `DATABASE_URL` configured:

```bash
python -m app.scripts.init_db
```

## Auth Endpoints

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/demo`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
