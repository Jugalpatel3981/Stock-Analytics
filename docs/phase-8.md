# Phase 8: Stock News Module

## Implemented

- Financial news lookup by stock ticker
- Protected backend news endpoint
- Frontend news page
- Ticker filter form
- News cards showing headline, source, publish date, summary, and source link
- Sidebar navigation entry for News

## Data Source

The module uses Yahoo Finance news through the existing `yfinance` provider layer.

This keeps the current setup simple because no extra API key is required for this phase. A future production phase can add a paid provider such as Finnhub, Polygon, Alpha Vantage, or NewsAPI behind the same service contract.

## Backend API

- `GET /api/v1/stocks/news?ticker=NVDA`
- `GET /api/v1/stocks/news?ticker=NVDA&limit=5`

All endpoints require authentication.

## Frontend

- `/news`

Users can filter headlines by ticker and open the original article source.

## User Trust Note

News content is informational research context, not financial advice. Users should verify headlines and summaries from the original source before making investment decisions.

## Testing

```bash
cd backend
pytest
```

```bash
cd frontend
npm run lint
```
