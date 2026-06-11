# Phase 4: Yahoo Finance Stock Data

## Implemented

- Yahoo Finance integration through a backend `yfinance` adapter
- Protected stock search endpoint
- Protected stock detail endpoint
- Frontend stock search page
- Frontend stock detail page
- Dashboard watchlist links to stock detail pages

## Backend API

- `GET /api/v1/stocks/search?query=NVDA`
- `GET /api/v1/stocks/NVDA`

Both endpoints require authentication.

## Stock Detail Fields

- ticker
- company name
- exchange
- currency
- current price
- volume
- market cap
- PE ratio
- sector
- industry
- website
- business summary

## Data Source

Stock data is fetched from Yahoo Finance through the Python `yfinance` package. The integration is isolated in `backend/app/services/stock_service.py` so the provider can be replaced later if needed.

## Testing

```bash
cd backend
pytest
```

```bash
cd frontend
npm run lint
npm run build
```
