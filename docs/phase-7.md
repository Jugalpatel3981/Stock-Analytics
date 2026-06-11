# Phase 7: Portfolio Management

## Implemented

- User-owned portfolio holdings
- Add holdings with symbol, quantity, buy price, and buy date
- Remove holdings
- Current value calculation using Yahoo Finance prices
- Gain/loss and percentage return calculation
- Portfolio growth chart using historical closing prices
- Protected backend APIs
- Professional dark-mode portfolio UI

## Database

### `portfolio_holdings`

- `id`
- `user_id`
- `symbol`
- `quantity`
- `buy_price`
- `buy_date`
- `created_at`

Each holding belongs to an authenticated user.

## Backend API

- `GET /api/v1/portfolio/holdings`
- `POST /api/v1/portfolio/holdings`
- `DELETE /api/v1/portfolio/holdings/{holding_id}`
- `GET /api/v1/portfolio/growth`

All endpoints require authentication.

## Calculations

- Cost basis = `quantity * buy_price`
- Current value = `quantity * current_price`
- Gain/loss = `current_value - cost_basis`
- Percentage return = `(gain_loss / cost_basis) * 100`

The growth chart uses one year of historical closing prices for each holding and starts counting each holding from its buy date.

## Frontend

- `/portfolio`

The page includes summary cards, an add holding form, a portfolio growth chart, and a holdings table with delete actions.

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
