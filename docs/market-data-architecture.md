# Market Data Architecture

The market data layer separates fast price movement from slower daily market statistics.

## Streaming Prices

Finnhub WebSocket is used for low-latency trade updates:

- Current price
- Price change
- Percentage change
- Last price timestamp

The WebSocket stream does not own cumulative daily volume, open, high, low, or previous close.

## REST Market Statistics

Finnhub REST endpoints refresh slower-changing market fields every 30 seconds through the frontend market hook and the backend symbol-aware cache:

- Today's volume
- Day high
- Day low
- Open price
- Previous close
- Regular close / extended-hours context

Daily volume is sourced from Finnhub candle data instead of WebSocket trade size.

## Market Session

Market session detection is centralized in `backend/app/market/market_session.py` and uses US market hours in the `America/New_York` timezone:

- `PRE_MARKET`: 4:00 AM to 9:30 AM ET
- `OPEN`: 9:30 AM to 4:00 PM ET
- `AFTER_HOURS`: 4:00 PM to 8:00 PM ET
- `CLOSED`: all other times, weekends included

The frontend displays timestamps in Pacific Time with a `PT` suffix.

## Backend Modules

- `market_formatter.py`: symbol and primitive value normalization
- `market_session.py`: session detection and session-specific price rules
- `rest_market_service.py`: Finnhub REST quote/candle fetches and Yahoo extended-hours fallback
- `websocket_service.py`: Finnhub WebSocket subscriptions and price ticks
- `market_scheduler.py`: lightweight 30-second REST snapshot cache

`app/services/market_stream_service.py` remains as a compatibility facade for existing routes and tests.

## Frontend Flow

`frontend/src/lib/market-stream.ts` uses two independent effects:

1. A WebSocket effect for price ticks.
2. A REST scheduler effect for daily statistics every 30 seconds.

This prevents REST refreshes from reconnecting the socket and prevents WebSocket ticks from overwriting daily volume.
