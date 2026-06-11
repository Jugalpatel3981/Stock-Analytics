# Environment Variables

This document lists the main environment variables needed for local development and future deployment.

## Root Docker Compose Variables

```text
COMPOSE_PROJECT_NAME=ai-stock-intelligence-platform
POSTGRES_DB=stock_intelligence
POSTGRES_USER=stock_user
POSTGRES_PASSWORD=stock_password
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
BACKEND_PORT=8000
FRONTEND_PORT=3000
```

## Backend Variables

```text
APP_NAME=AI Stock Intelligence Platform API
APP_ENV=development
API_V1_PREFIX=/api/v1
BACKEND_CORS_ORIGINS=http://localhost:3000
DATABASE_URL=postgresql+asyncpg://stock_user:stock_password@localhost:5432/stock_intelligence
JWT_SECRET_KEY=replace-with-a-long-random-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
AUTH_COOKIE_NAME=access_token
AUTH_COOKIE_SECURE=false
AUTO_CREATE_TABLES=true
HUGGINGFACE_API_TOKEN=
HUGGINGFACE_SENTIMENT_MODEL=ProsusAI/finbert
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
```

## Frontend Variables

```text
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
API_INTERNAL_BASE_URL=http://localhost:8000/api/v1
```

## Production Notes

Use these production settings:

```text
APP_ENV=production
AUTH_COOKIE_SECURE=true
AUTO_CREATE_TABLES=false
BACKEND_CORS_ORIGINS=https://your-frontend-domain.com
NEXT_PUBLIC_API_BASE_URL=https://your-backend-domain.com/api/v1
API_INTERNAL_BASE_URL=https://your-backend-domain.com/api/v1
```

Generate a strong `JWT_SECRET_KEY` before deployment. Never commit real secret values.
