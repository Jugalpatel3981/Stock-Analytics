# Phase 11: Stock Prediction Module

## Implemented

- XGBoost prediction service
- Next trading day closing price prediction
- Feature engineering from:
  - Historical close prices
  - Volume
  - 5-day moving average
  - 10-day moving average
  - 20-day moving average
  - Daily return
  - Intraday range percentage
- Confidence score
- Historical holdout accuracy
- Protected backend prediction API
- Dashboard prediction widget
- Backend route test coverage with mocked prediction service

## Backend API

```text
GET /api/v1/stocks/{ticker}/prediction
```

Example:

```text
GET /api/v1/stocks/NVDA/prediction
```

All prediction endpoints require authentication.

## Model

- Model: XGBoost Regressor
- Target: next trading day closing price
- Data source: Yahoo Finance via `yfinance`
- Training window: two years of daily historical data
- Split: chronological 80/20 train/test holdout

## Output

- `predicted_close`
- `latest_close`
- `confidence_score`
- `historical_accuracy`
- `training_rows`
- `feature_summary`

## Frontend

The dashboard includes a stock prediction widget where users can enter a ticker and generate an XGBoost next-close estimate.

## Important Limitation

This prediction is an experimental ML research signal. It does not guarantee future price movement and must not be treated as financial advice or a buy/sell recommendation.

## Setup

Reinstall backend dependencies or rebuild Docker because Phase 11 adds ML dependencies:

- `xgboost`
- `numpy`
- `pandas`
- `scikit-learn`

```bash
cd backend
pip install -r requirements.txt
```

With Docker:

```bash
docker compose up --build
```

## Testing

```bash
cd backend
pytest
```

```bash
cd frontend
npm run lint
```
