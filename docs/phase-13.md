# Phase 13 - Real-Time Market Streaming and AI Assistant V2

## Objective

Enhance the existing platform without replacing current modules.

- Add real-time stock updates to the existing dashboard, stocks, watchlists, and portfolio views.
- Upgrade the existing AI assistant into an evidence-based market intelligence layer.

## Backend

- Added a Finnhub WebSocket proxy endpoint at `WS /api/v1/market/stream?symbols=NVDA,AAPL`.
- Added a Finnhub REST quote snapshot endpoint at `GET /api/v1/market/quotes?symbols=NVDA,AAPL`.
- Added US equity session detection for pre-market, open, after-hours, and closed states.
- Protected the stream with the existing JWT auth cookie.
- Added Tavily Search integration for AI assistant web research.
- Extended assistant message storage with source citations.
- Assistant responses now use retrieved stock data, news, sentiment, web research, and prior session context.

## Frontend

- Added reusable live market stream hook and live quote components.
- Live widgets now load a Finnhub REST quote snapshot first, refresh snapshots every 15 seconds, then apply WebSocket ticks for faster real-time updates when available.
- Live badges now switch between `PRE-MARKET`, `LIVE`, `AFTER HOURS`, and `CLOSED`, including next-open timing when relevant.
- After-hours cards show `After Hours Price` only when Finnhub provides extended-hours activity; otherwise they show regular close and `No After-Hours Activity`.
- WebSocket trade volume is displayed as latest trade size only when a tick is received; quote cards no longer show misleading `Vol 0`.
- Integrated live prices, volume, movement indicators, LIVE badge, and last-updated timestamps into existing pages.
- Dashboard market overview now uses watchlist symbols when available and supports a saved custom symbol set.
- Enhanced the existing assistant UI with cited sources and confidence scores.

## Required Environment Variables

```text
FINNHUB_API_KEY=
TAVILY_API_KEY=
TAVILY_SEARCH_DEPTH=basic
GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile
NEXT_PUBLIC_MARKET_STREAM_URL=ws://localhost:8000/api/v1/market/stream
```

`GROQ_API_KEY` or `OPENAI_API_KEY` is required for production-quality assistant answers. If both are configured, the backend prefers Groq. Without a Tavily key, the assistant continues using internal stock, news, and sentiment context.

## Testing

Backend:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

Frontend:

```powershell
npm run lint:frontend
```

Manual verification:

1. Start Docker Desktop.
2. Add `FINNHUB_API_KEY`, `TAVILY_API_KEY`, and either `GROQ_API_KEY` or `OPENAI_API_KEY` to `.env`.
3. Run `docker compose up --build`.
4. Log in.
5. Check `/dashboard`, `/stocks`, `/watchlists`, and `/portfolio` for live badges and timestamps.
6. Ask the assistant a ticker-specific question and inspect the Sources section.

## Trust and Compliance Notes

Assistant answers must be treated as informational research support only. The system shows sources, confidence, and uncertainty so users can verify evidence before making any investing decision.

