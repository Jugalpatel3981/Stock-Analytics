# Environment Variables

This document lists the environment variables for local development and deployment. See
[deployment.md](deployment.md) for the hosted setup.

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
APP_NAME=Stock Intelligence Platform API
APP_ENV=development
API_V1_PREFIX=/api/v1
BACKEND_CORS_ORIGINS=http://localhost:3000
DATABASE_URL=postgresql+asyncpg://stock_user:stock_password@localhost:5432/stock_intelligence
JWT_SECRET_KEY=replace-with-a-long-random-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
AUTH_COOKIE_NAME=access_token
AUTH_COOKIE_SECURE=false
DEMO_MODE_ENABLED=true
FINNHUB_API_KEY=
```

## Frontend Variables

```text
BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_MARKET_STREAM_URL=ws://localhost:8000/api/v1/market/stream
```

`BACKEND_URL` is the backend's origin. Browser requests to `/api/v1/*` are rewritten to it by
`next.config.ts`, and server components call it directly. It is read at **build** time for
the rewrite, so set it before building.

`NEXT_PUBLIC_MARKET_STREAM_URL` is the backend's WebSocket URL. The browser connects to it
directly, authenticated with a short-lived token from `GET /api/v1/market/stream-token`.

## Integration Notes

`FINNHUB_API_KEY` enables real-time WebSocket market streaming. Without it, live widgets show a clear configuration error instead of fake prices.

`DEMO_MODE_ENABLED` turns the one-click demo login on or off.

## Production Notes

Use these production settings:

```text
# Backend
APP_ENV=production
AUTH_COOKIE_SECURE=true
JWT_SECRET_KEY=<at least 32 random characters>
BACKEND_CORS_ORIGINS=https://your-frontend-domain.com

# Frontend
BACKEND_URL=https://your-backend-domain.com
NEXT_PUBLIC_MARKET_STREAM_URL=wss://your-backend-domain.com/api/v1/market/stream
```

In production the backend refuses to start with a placeholder `JWT_SECRET_KEY` or with
`AUTH_COOKIE_SECURE=false`. Never commit real secret values.

