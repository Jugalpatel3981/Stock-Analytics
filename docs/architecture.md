# Architecture Overview

## Goals

The AI Stock Intelligence Platform is structured as a modular SaaS monorepo. The foundation favors incremental delivery, clear service boundaries, and production-ready conventions without adding premature complexity.

## High-Level Components

- `frontend`: Next.js app-router application for the investor dashboard experience.
- `backend`: FastAPI application exposing versioned APIs under `/api/v1`.
- `postgres`: PostgreSQL database for users, portfolios, securities, market snapshots, and AI analysis outputs in future phases.

## Backend Boundaries

The backend uses a layered structure:

- `api`: HTTP routes, request dependencies, and versioned router composition.
- `core`: configuration, database session management, and infrastructure.
- `models`: SQLAlchemy ORM model base and future persistence models.
- `schemas`: Pydantic response and request contracts.
- `services`: business logic isolated from HTTP transport.

This keeps route handlers thin and leaves room for testing domain logic independently.

## Authentication

Authentication is implemented in the backend under `/api/v1/auth`. JWT access tokens are issued after register/login and stored in an HttpOnly cookie. The frontend never stores tokens in `localStorage`.

Reusable auth concerns are split by responsibility:

- `core/security.py`: password hashing and JWT encode/decode.
- `api/deps.py`: current-user dependency for protected routes.
- `services/user_service.py`: user lookup, creation, and password verification.
- `models/user.py`: SQLAlchemy `users` table model.

## Frontend Boundaries

The frontend uses:

- `app`: route segments, layouts, and global CSS.
- `components`: reusable UI and application components.
- `lib`: API clients, environment helpers, and shared utilities.

ShadCN UI is represented through local UI primitives so components can be owned and customized in the repository.

## Environment Strategy

Environment examples are committed, but real `.env` files are ignored. Docker Compose can load root `.env` values, while each app also has a local example file for non-Docker development.

## Future Architecture Notes

Recommended later additions:

- Alembic migrations once the first persisted domain models are introduced.
- Background workers for data ingestion and AI analysis jobs.
- Authentication and authorization before user-specific portfolio data.
- Observability with structured logging, request IDs, and health/readiness checks.
