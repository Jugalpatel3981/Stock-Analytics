# Railway Deployment Guide

This guide is for a future deployment. Do not deploy until you are ready to publish the project.

## Recommended Railway Role

Use Railway for:

- FastAPI backend
- PostgreSQL database
- Optional frontend deployment if you want one platform for everything

Official docs:

- Railway deployments: https://docs.railway.com/deployments
- Railway variables: https://docs.railway.com/variables

## Repository Files

This project includes Railway config templates:

- `railway.backend.toml`
- `railway.frontend.toml`

Use them as references when creating Railway services. If Railway asks for one config file per service, copy the relevant file into that service configuration or configure the same settings in the Railway dashboard.

## Backend Service

Create a Railway service from the GitHub repository.

Recommended settings:

- Root directory: repository root
- Dockerfile path: `backend/Dockerfile`
- Healthcheck path: `/health`

Required variables:

```text
APP_ENV=production
API_V1_PREFIX=/api/v1
BACKEND_CORS_ORIGINS=https://your-frontend-domain.com
DATABASE_URL=${{Postgres.DATABASE_URL}}
JWT_SECRET_KEY=replace-with-long-random-secret
ACCESS_TOKEN_EXPIRE_MINUTES=60
AUTH_COOKIE_NAME=access_token
AUTH_COOKIE_SECURE=true
AUTO_CREATE_TABLES=false
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
```

Railway variables are available to services as runtime environment variables.

## PostgreSQL Service

Add a Railway PostgreSQL database to the same project.

Then connect the backend `DATABASE_URL` to the PostgreSQL service variable. Railway supports referencing variables from another service, for example:

```text
DATABASE_URL=${{Postgres.DATABASE_URL}}
```

## Frontend On Railway

If deploying the frontend on Railway instead of Vercel:

- Dockerfile path: `frontend/Dockerfile`
- Healthcheck path: `/`

Required variables:

```text
NEXT_PUBLIC_API_BASE_URL=https://your-backend-domain.com/api/v1
API_INTERNAL_BASE_URL=https://your-backend-domain.com/api/v1
```

## Database Initialization

For this project phase, database tables are created through SQLAlchemy metadata when `AUTO_CREATE_TABLES=true`.

For production, keep:

```text
AUTO_CREATE_TABLES=false
```

Before first production launch, run the initialization command once in a controlled environment:

```bash
python -m app.scripts.init_db
```

A future phase should add Alembic migrations before serious production use.

## Deployment Checklist

1. Create PostgreSQL service.
2. Create backend service.
3. Add backend variables.
4. Run database initialization once.
5. Verify backend `/health`.
6. Create frontend service or deploy frontend to Vercel.
7. Set frontend API variables.
8. Update backend CORS with frontend domain.
9. Test authentication cookies over HTTPS.
10. Test stocks, portfolio, news, assistant, and predictions.
