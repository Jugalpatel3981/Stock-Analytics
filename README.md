# AI Stock Intelligence Platform

A production-minded monorepo for a long-term portfolio SaaS project that combines market data, portfolio intelligence, and AI-assisted stock research.

## Tech Stack

- Frontend: Next.js 15, TypeScript, Tailwind CSS, ShadCN UI conventions
- Backend: FastAPI, Python, Pydantic Settings, SQLAlchemy async
- Database: PostgreSQL
- Infrastructure: Docker and Docker Compose

## Repository Structure

```text
.
├── backend/                 # FastAPI application
│   ├── app/
│   │   ├── api/             # API routers and route dependencies
│   │   ├── core/            # Settings, database, shared infrastructure
│   │   ├── models/          # SQLAlchemy model base and future domain models
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   └── services/        # Business logic services
│   └── tests/               # Backend tests
├── docs/                    # Architecture and phase documentation
├── frontend/                # Next.js application
│   └── src/
│       ├── app/             # App router pages and global styles
│       ├── components/      # Reusable app and UI components
│       └── lib/             # Shared utilities and API clients
└── docker-compose.yml       # Local full-stack orchestration
```

## Prerequisites

- Node.js 20+
- Python 3.12+
- Docker Desktop
- PostgreSQL client tools, optional for local database inspection

## Environment Setup

Copy the example files before running locally:

```bash
cp .env.example .env
cp frontend/.env.example frontend/.env.local
cp backend/.env.example backend/.env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
Copy-Item frontend/.env.example frontend/.env.local
Copy-Item backend/.env.example backend/.env
```

## Run With Docker

```bash
docker compose up --build
```

Services:

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Backend docs: http://localhost:8000/docs
- PostgreSQL: localhost:5432

## Run Locally Without Docker

Start PostgreSQL locally or via Docker:

```bash
docker compose up postgres
```

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Windows PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

You can also use root workspace scripts after installing frontend dependencies:

```bash
npm run dev:frontend
npm run dev:backend
```

## Validation

Backend tests:

```bash
cd backend
pytest
```

Frontend lint:

```bash
cd frontend
npm run lint
```

Docker health check:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/health
```

## Authentication

Phase 2 adds JWT authentication stored in an HttpOnly cookie. Browser JavaScript does not store the token directly.

Auth endpoints:

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `GET /api/v1/auth/protected`

For Docker development, `AUTO_CREATE_TABLES=true` creates the `users` table when the backend starts. For local development without Docker, start PostgreSQL, confirm `DATABASE_URL`, then run:

```bash
cd backend
python -m app.scripts.init_db
```

Frontend auth routes:

- `/login`
- `/register`
- `/dashboard`

In Docker, the frontend uses `API_INTERNAL_BASE_URL=http://backend:8000/api/v1` for server-side requests between containers. Browser requests continue to use `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1`.

## Phase 1 Scope

This phase establishes the production-ready monorepo foundation:

- Next.js frontend scaffold with Tailwind and ShadCN-compatible UI primitives
- FastAPI backend scaffold with typed environment settings
- Async PostgreSQL connection wiring
- Docker Compose for frontend, backend, and database
- Documentation for architecture, setup, and validation

Future phases can add authentication, stock data ingestion, portfolio models, AI analysis workflows, background jobs, and deployment automation.
