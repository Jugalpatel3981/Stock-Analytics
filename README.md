<div align="center">

# Stock Intelligence Platform

**Live prices, stock research and portfolio analytics in one dashboard.**

[![CI](https://github.com/Jugalpatel3981/ai-stock-intelligence-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/Jugalpatel3981/ai-stock-intelligence-platform/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-15-000000?logo=nextdotjs&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

<!-- LIVE-DEMO-LINK: added after deployment -->

![Landing page](screenshots/landing.png)

</div>

## Overview

A full-stack web app for researching US stocks and analysing a portfolio. Search a company,
follow it with real-time prices, compare stocks side by side, and see how your portfolio
performs against the S&P 500 with the risk figures to explain it.

> For informational and educational purposes only. Not financial advice.

## Features

| | Feature | How it works |
| --- | --- | --- |
| 📈 | **Real-time prices** | The backend proxies Finnhub's WebSocket to the browser and labels pre-market, regular and after-hours sessions. |
| 📊 | **Portfolio analytics** | Return against the S&P 500, volatility, Sharpe ratio, beta, max drawdown, allocation by stock and sector, and concentration warnings. |
| ⚖️ | **Stock comparison** | Up to five stocks on one indexed chart, with side-by-side risk figures and a correlation heatmap. |
| 💼 | **Portfolio and watchlists** | Live gain/loss, a growth chart, CSV import and export, and multiple watchlists. |
| 🔐 | **Secure accounts** | bcrypt passwords and JWT sessions in HttpOnly cookies, plus a one-click demo account. |
| 🔎 | **Stock research** | Search by company name, price history, company profile, analyst ratings, 52-week range and the next earnings date. |
| 📰 | **News** | Recent headlines filtered by ticker. |
| ⚙️ | **Production engineering** | Alembic migrations, caching, rate limiting, Docker and CI. |

## Architecture

```mermaid
flowchart LR
    UI[Next.js frontend] -->|REST + HttpOnly cookie| API[FastAPI backend]
    UI <-->|live ticks| WS[WebSocket proxy]
    WS <--> Finnhub[[Finnhub]]
    API --> Yahoo[[Yahoo Finance]]
    API --> DB[(PostgreSQL)]
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full design: auth and the market
data flow.

## Tech stack

| Layer | Technologies |
| --- | --- |
| Frontend | Next.js 15 (App Router), React, TypeScript, Tailwind CSS, shadcn/ui, Recharts |
| Backend | FastAPI, Python 3.12, SQLAlchemy 2 (async), Pydantic, WebSockets |
| Data and analysis | PostgreSQL, pandas, NumPy, yfinance |
| Market data | Finnhub WebSocket and REST, Yahoo Finance |
| DevOps | Docker, Docker Compose, Alembic, GitHub Actions, Render, Vercel, Neon |

## How the analytics are calculated

All figures use daily closing prices and are price returns, without dividends.

| Measure | Calculation |
| --- | --- |
| Return against the S&P 500 | Each purchase is compared with putting the same money into SPY on the same date. |
| Volatility | Standard deviation of daily returns, multiplied by √252 to give a yearly figure. |
| Sharpe ratio | (Average daily return × 252 − a 4% risk-free rate) ÷ volatility. |
| Beta | Covariance of portfolio and SPY daily returns ÷ variance of SPY daily returns. |
| Max drawdown | The largest fall from a running peak to a later low. |
| Correlation | Pearson correlation of daily returns between each pair of stocks. |

Risk figures describe today's holdings as if they had been held for the past year. The
calculations are pure functions in `backend/app/analytics/metrics.py`, with tests that use
hand-checked numbers.

## Getting started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- A free API key:

| Key | Used for | Required? |
| --- | --- | --- |
| `FINNHUB_API_KEY` ([finnhub.io](https://finnhub.io)) | Real-time prices, stock search and news | Recommended |

The app still runs without the key: live prices show a clear "not configured" message,
and search only finds exact ticker symbols.

### Run with Docker

```bash
git clone https://github.com/Jugalpatel3981/ai-stock-intelligence-platform.git
cd ai-stock-intelligence-platform
cp .env.example .env        # Windows PowerShell: Copy-Item .env.example .env
# Add your Finnhub API key to .env
docker compose up --build
```

Open **http://localhost:3000** and click **Try the live demo**.

| Service | URL |
| --- | --- |
| Frontend | http://localhost:3000 |
| API docs (Swagger) | http://localhost:8000/docs |
| Health check | http://localhost:8000/health |

### Deploy

[docs/deployment.md](docs/deployment.md) describes a free-tier setup on Vercel, Render and Neon.

<details>
<summary><b>Run without Docker</b></summary>

You need Python 3.12+, Node.js 22+ and a local PostgreSQL database.

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env               # set DATABASE_URL and your Finnhub key
python -m app.scripts.init_db
uvicorn app.main:app --reload

# Frontend (in a second terminal, from the repository root)
npm install
npm run dev:frontend
```

</details>

## Testing

```bash
# From the backend directory
pytest                     # tests
ruff check .               # lint

# From the repository root
npm run lint:frontend      # ESLint
npm run typecheck:frontend # TypeScript
```

CI runs all of these, plus a production frontend build and Docker image builds, on every push.

## Project structure

```text
.
├── backend/
│   ├── app/
│   │   ├── analytics/    # Risk and return calculations
│   │   ├── api/          # FastAPI routers and dependencies
│   │   ├── core/         # Settings, database, security
│   │   ├── market/       # Finnhub streaming, market sessions, quote cache
│   │   ├── models/       # SQLAlchemy tables
│   │   ├── schemas/      # Pydantic models
│   │   └── services/     # Business logic and integrations
│   └── tests/
├── frontend/src/
│   ├── app/              # Next.js routes
│   ├── components/       # UI and feature components
│   └── lib/              # API client and helpers
├── docs/                 # Architecture, deployment, environment variables
└── .github/workflows/    # CI
```

## API overview

Interactive docs are available at `/docs` when the backend is running.

| Area | Endpoints |
| --- | --- |
| Auth | `POST /auth/register`, `POST /auth/login`, `POST /auth/demo`, `GET /auth/me` |
| Stocks | `GET /stocks/search`, `GET /stocks/{ticker}`, `GET /stocks/{ticker}/history`, `GET /stocks/{ticker}/insights` |
| Compare | `GET /stocks/compare?symbols=AAPL,MSFT&range=1y` |
| News | `GET /stocks/news?ticker=NVDA` |
| Market | `GET /market/quotes?symbols=NVDA,AAPL`, `WS /market/stream?symbols=NVDA,AAPL` |
| Watchlists | `GET /watchlists`, `POST /watchlists`, `PATCH /watchlists/{id}`, `DELETE /watchlists/{id}`, `POST /watchlists/{id}/stocks` |
| Portfolio | `GET /portfolio/holdings`, `POST /portfolio/holdings`, `PATCH /portfolio/holdings/{id}`, `GET /portfolio/growth` |
| Analytics | `GET /portfolio/analytics` |
| CSV | `GET /portfolio/holdings/export`, `POST /portfolio/holdings/import` |

All paths are prefixed with `/api/v1`.

## License

[MIT](LICENSE)
