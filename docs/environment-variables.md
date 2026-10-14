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
DEMO_MODE_ENABLED=true
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile
FINNHUB_API_KEY=
TAVILY_API_KEY=
TAVILY_SEARCH_DEPTH=basic
```

## Frontend Variables

```text
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
API_INTERNAL_BASE_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_MARKET_STREAM_URL=ws://localhost:8000/api/v1/market/stream
```

## Integration Notes

`FINNHUB_API_KEY` enables real-time WebSocket market streaming. Without it, live widgets show a clear configuration error instead of fake prices.

`GROQ_API_KEY` enables Groq for the AI assistant and for news sentiment. Without it, every article is labelled Neutral. If both `GROQ_API_KEY` and `OPENAI_API_KEY` are set, the backend prefers Groq.

`TAVILY_API_KEY` enables AI Assistant V2 web research and source citations. Without it, the assistant still uses existing platform stock, news, and sentiment context.

`DEMO_MODE_ENABLED` turns the one-click demo login on or off.

## Production Notes

Use these production settings:

```text
APP_ENV=production
AUTH_COOKIE_SECURE=true
BACKEND_CORS_ORIGINS=https://your-frontend-domain.com
NEXT_PUBLIC_API_BASE_URL=https://your-backend-domain.com/api/v1
API_INTERNAL_BASE_URL=https://your-backend-domain.com/api/v1
```

Generate a strong `JWT_SECRET_KEY` before deployment. Never commit real secret values.

