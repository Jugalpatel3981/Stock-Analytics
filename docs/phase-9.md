# Phase 9: AI Sentiment Analysis

## Implemented

- HuggingFace sentiment analysis for stock news articles
- Default model: `ProsusAI/finbert`
- Per-article sentiment label:
  - Positive
  - Neutral
  - Negative
- Signed sentiment score:
  - Positive: `0` to `1`
  - Neutral: `0`
  - Negative: `0` to `-1`
- Sentiment badge on each news article
- Sentiment trend chart
- Backend test coverage for the enriched news response

## Backend

The existing news endpoint now includes sentiment data:

```text
GET /api/v1/stocks/news?ticker=NVDA
```

Response additions:

- `articles[].sentiment_label`
- `articles[].sentiment_score`
- `sentiment_trend`
- `sentiment_model`

## HuggingFace Configuration

Optional environment variables:

```text
HUGGINGFACE_API_TOKEN=
HUGGINGFACE_SENTIMENT_MODEL=ProsusAI/finbert
```

If the HuggingFace call is unavailable, the backend returns a neutral fallback so the news page still works during local development.

## Frontend

The `/news` page now shows:

- Sentiment badge per article
- Sentiment score per article
- Sentiment trend chart
- Model name used for analysis

## Trust And Safety

Sentiment is an AI-generated research signal only. It should not be treated as financial advice or as a buy/sell recommendation.

## Testing

```bash
cd backend
pytest
```

```bash
cd frontend
npm run lint
```
