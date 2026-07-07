# Production ML Pipeline

The prediction module now uses a production-style background pipeline instead of training during each user request.

## Runtime Flow

1. The backend scheduler starts with FastAPI.
2. Every configured interval, it discovers tracked symbols from watchlists, portfolio holdings, and default ML symbols.
3. Historical OHLCV data is downloaded from Yahoo Finance via `yfinance`.
4. Data is stored in the canonical `historical_prices` table.
5. The shared feature engineering pipeline generates technical indicators.
6. A candidate XGBoost model is trained and evaluated.
7. The candidate replaces the production model only if it improves MAPE.
8. Prediction requests load the current production model from `backend/models` and never train in the request path.

## Modules

```text
backend/app/ml/
+-- data_collector.py       # Downloads and stores historical market data
+-- feature_engineering.py  # Shared technical indicator pipeline
+-- evaluator.py            # MAE, RMSE, MAPE, direction accuracy
+-- trainer.py              # Candidate training and promotion workflow
+-- predictor.py            # Production-model inference only
+-- registry.py             # Joblib artifacts and production model metadata
+-- scheduler.py            # Background retraining loop
+-- symbols.py              # Tracked symbol discovery
```

## Database Tables

- `historical_prices`: Canonical OHLCV market data.
- `ml_models`: Model artifact metadata and production flag.
- `ml_training_runs`: Internal training logs, metrics, duration, status, and promotion result.

## Environment Variables

```env
ML_SCHEDULER_ENABLED=true
ML_RETRAIN_INTERVAL_DAYS=4
ML_SCHEDULER_INITIAL_DELAY_SECONDS=30
ML_MODELS_DIR=models
ML_DEFAULT_SYMBOLS=AAPL,MSFT,NVDA,TSLA,AMZN,GOOGL,META,JPM
ML_MIN_TRAINING_ROWS=120
```


## On-Demand Training

If a user requests a prediction for a valid ticker that does not have a production model yet, the API returns a `preparing` response and adds the ticker to an in-memory background training queue. The request does not train the model directly. The scheduler drains this queue immediately while the backend is running.

This supports any valid ticker over time without training thousands of unused models upfront.

## Prediction Endpoint

`GET /api/v1/stocks/{ticker}/prediction`

The endpoint returns either a `ready` prediction or a `preparing` response when a valid ticker has just been queued for background training. Ready predictions include:

- predicted closing price
- expected price range
- confidence score
- prediction timestamp

It does not expose model internals such as training rows or evaluation metrics. Those remain stored internally in the database.

## Important Behavior

If a production model does not exist yet for a ticker, the endpoint returns `503`. The background scheduler will prepare models automatically. For local development, keep the backend running long enough for the first scheduler run or temporarily lower `ML_SCHEDULER_INITIAL_DELAY_SECONDS`.

This feature is informational research support only and must not be treated as financial advice.


