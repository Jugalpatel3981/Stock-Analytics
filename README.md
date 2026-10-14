# AI Stock Intelligence Platform

AI Stock Intelligence Platform is a full-stack portfolio project for stock research, portfolio tracking, market news, AI sentiment analysis, AI-assisted financial research, and experimental price prediction.

It is built as a production-minded monorepo with a Next.js frontend, FastAPI backend, PostgreSQL database, Docker support, CI checks, and deployment preparation for Vercel and Railway.

> This platform provides informational research support only. It does not provide financial advice, buy/sell recommendations, guarantees, or price targets.

## Features

- JWT authentication with HttpOnly cookie sessions
- Professional dark finance dashboard
- Stock search and stock detail pages
- Yahoo Finance company data and historical prices
- Recharts price visualization
- Watchlists
- Portfolio holdings, gain/loss, and growth chart
- Finnhub WebSocket-powered live prices for dashboard, stocks, watchlists, and portfolio
- Stock news filtered by ticker
- LLM-powered news sentiment analysis (Groq), batched and cached
- OpenAI-powered financial assistant with saved chat history, follow-up support, web research, and source citations
- XGBoost next-day close prediction module
- Dockerized frontend, backend, and PostgreSQL
- GitHub Actions CI
- Deployment guides for Vercel and Railway

## Tech Stack

| Layer | Technology |
| --- | --- |
| Frontend | Next.js 15, TypeScript, Tailwind CSS, ShadCN UI conventions |
| Backend | FastAPI, Python 3.12, Pydantic Settings |
| Database | PostgreSQL, SQLAlchemy async |
| AI | OpenAI/Grok Responses APIs, Groq LLM sentiment, Tavily Search |
| Market Data | Yahoo Finance, Finnhub WebSocket |
| ML | XGBoost, pandas, numpy, scikit-learn |
| Charts | Recharts |
| Infrastructure | Docker, Docker Compose |
| CI | GitHub Actions |

## Repository Structure

```text
.
|-- backend/                 # FastAPI application
|   |-- app/
|   |   |-- api/             # API routers and dependencies
|   |   |-- core/            # Settings and database infrastructure
|   |   |-- models/          # SQLAlchemy models
|   |   |-- schemas/         # Pydantic schemas
|   |   |-- scripts/         # Utility scripts
|   |   `-- services/        # Business logic and integrations
|   `-- tests/               # Backend tests
|-- docs/                    # Phase docs and deployment guides
|-- frontend/                # Next.js application
|   `-- src/
|       |-- app/             # App Router pages
|       |-- components/      # Reusable UI and feature components
|       `-- lib/             # API client and utilities
|-- docker-compose.yml       # Local development stack
|-- docker-compose.prod.yml  # Future production Compose template
`-- .github/workflows/       # CI workflow
```

## Prerequisites

- Node.js 22+
- Python 3.12+
- Docker Desktop
- Git

## Quick Start With Docker

1. Copy environment defaults:

```powershell
Copy-Item .env.example .env
```

2. Start the stack:

```powershell
docker compose up --build
```

3. Open the app:

```text
http://localhost:3000
```

Useful URLs:

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- Backend docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

## Local Development Without Docker

Backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:

```powershell
npm install
npm run dev:frontend
```

Database initialization:

```powershell
cd backend
python -m app.scripts.init_db
```

## Environment Variables

Copy the examples before local development:

```powershell
Copy-Item .env.example .env
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env.local
```

Detailed environment documentation:

- [Environment Variables](docs/environment-variables.md)
- Production template: `.env.production.example`

Optional AI variables:

```text
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile
TAVILY_API_KEY=
TAVILY_SEARCH_DEPTH=basic
FINNHUB_API_KEY=
NEXT_PUBLIC_MARKET_STREAM_URL=ws://localhost:8000/api/v1/market/stream
```

## Testing

Backend:

```powershell
cd backend
pytest
```

Frontend:

```powershell
npm run lint:frontend
```

Docker build checks are included in GitHub Actions.

## Main Routes

| Route | Purpose |
| --- | --- |
| `/login` | User login |
| `/register` | User registration |
| `/dashboard` | Finance dashboard |
| `/stocks` | Stock search |
| `/stocks/[ticker]` | Stock detail and price chart |
| `/watchlists` | Watchlist management |
| `/portfolio` | Portfolio holdings and growth |
| `/news` | Stock news and sentiment |
| `/assistant` | AI financial assistant |

## API Overview

| Area | Endpoint Examples |
| --- | --- |
| Auth | `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me` |
| Stocks | `GET /api/v1/stocks/search?query=NVDA`, `GET /api/v1/stocks/NVDA` |
| History | `GET /api/v1/stocks/NVDA/history?range=1mo` |
| News | `GET /api/v1/stocks/news?ticker=NVDA` |
| Prediction | `GET /api/v1/stocks/NVDA/prediction` |
| Market Snapshot | `GET /api/v1/market/quotes?symbols=NVDA,AAPL` |
| Live Market Stream | `WS /api/v1/market/stream?symbols=NVDA,AAPL` |
| Watchlists | `GET /api/v1/watchlists`, `POST /api/v1/watchlists` |
| Portfolio | `GET /api/v1/portfolio/holdings`, `GET /api/v1/portfolio/growth` |
| Assistant | `GET /api/v1/chat/sessions`, `POST /api/v1/chat/sessions/{id}/messages` |

## Deployment Preparation

No deployment has been performed yet. The repository is prepared for future deployment.

Guides:

- [Vercel Deployment Guide](docs/deployment-vercel.md)
- [Railway Deployment Guide](docs/deployment-railway.md)

Deployment-related files:

- `backend/Dockerfile`
- `frontend/Dockerfile`
- `docker-compose.yml`
- `docker-compose.prod.yml`
- `.env.production.example`
- `railway.backend.toml`
- `railway.frontend.toml`
- `.github/workflows/ci.yml`

## Production Notes

Before deploying for real:

- Set strong secrets.
- Use HTTPS URLs.
- Set `AUTH_COOKIE_SECURE=true`.
- Set `AUTO_CREATE_TABLES=false`.
- Add the frontend domain to `BACKEND_CORS_ORIGINS`.
- Configure a managed PostgreSQL database.
- Run database initialization or migrations once.
- Verify the Groq (or OpenAI) key if using AI features.

## Documentation

Phase documentation is available in `docs/`:

- `docs/phase-1.md`
- `docs/phase-3.md` through `docs/phase-13.md`

## License

Portfolio project. Add a license before public production release if needed.

