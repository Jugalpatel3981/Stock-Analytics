from datetime import datetime

from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.main import app
from app.market.rest_market_service import _stats_from_candle_payload, enrich_with_yahoo_market_stats
from app.schemas.market import MarketQuote
from app.services.market_stream_service import (
    _enrich_with_yahoo_extended_hours,
    _session_prices,
    get_market_session,
    normalize_symbols,
)


client = TestClient(app)


def test_normalize_symbols_trims_uppercases_and_limits() -> None:
    symbols = ",".join([f"stock{i}" for i in range(30)])

    normalized_symbols = normalize_symbols(f" nvda, AAPL ,, {symbols}")

    assert normalized_symbols[:2] == ["NVDA", "AAPL"]
    assert "" not in normalized_symbols
    assert len(normalized_symbols) == 25


def test_market_stream_requires_authentication() -> None:
    with client.websocket_connect("/api/v1/market/stream?symbols=NVDA") as websocket:
        payload = websocket.receive_json()

    assert payload["type"] == "error"
    assert payload["message"] == "Authentication is required for live market streaming."


def test_market_stream_requires_symbols_after_authentication() -> None:
    token = create_access_token(subject="123")

    with client.websocket_connect(
        "/api/v1/market/stream?symbols=",
        headers={"cookie": f"access_token={token}"},
    ) as websocket:
        payload = websocket.receive_json()

    assert payload["type"] == "error"
    assert payload["message"] == "At least one symbol is required."


def test_market_session_detects_regular_market_open() -> None:
    session, next_open = get_market_session(datetime.fromisoformat("2026-06-12T14:00:00+00:00"))

    assert session == "OPEN"
    assert next_open is None


def test_market_session_detects_after_hours_and_next_open() -> None:
    session, next_open = get_market_session(datetime.fromisoformat("2026-06-12T21:30:00+00:00"))

    assert session == "AFTER_HOURS"
    assert next_open == "2026-06-15T09:30:00-04:00"


def test_market_session_detects_weekend_closed() -> None:
    session, next_open = get_market_session(datetime.fromisoformat("2026-06-13T17:00:00+00:00"))

    assert session == "CLOSED"
    assert next_open == "2026-06-15T09:30:00-04:00"


def test_after_hours_without_extended_activity_uses_current_price_as_regular_close() -> None:
    regular_price, extended_hours_price = _session_prices(
        market_session="AFTER_HOURS",
        current_price=234.11,
        previous_close=232.79,
        has_extended_hours_activity=False,
    )

    assert regular_price == 234.11
    assert extended_hours_price is None

def test_yahoo_extended_hours_fallback_enriches_after_hours_quote() -> None:
    quote = MarketQuote(
        symbol="MSFT",
        current_price=390.34,
        previous_close=388.00,
        regular_price=390.34,
        market_session="AFTER_HOURS",
        next_market_open="2026-06-15T09:30:00-04:00",
        timestamp="2026-06-12T20:00:00+00:00",
    )

    enriched_quote = _enrich_with_yahoo_extended_hours(
        quote,
        {
            "symbol": "MSFT",
            "regularMarketPrice": 390.34,
            "postMarketPrice": 391.1,
            "postMarketChange": 0.76,
            "postMarketChangePercent": 0.1947,
            "postMarketTime": 1781299800,
        },
    )

    assert enriched_quote.current_price == 391.1
    assert enriched_quote.extended_hours_price == 391.1
    assert enriched_quote.regular_price == 390.34
    assert enriched_quote.has_extended_hours_activity is True
    assert enriched_quote.extended_hours_status == "ACTIVE"
    assert enriched_quote.extended_hours_source == "Yahoo Finance"
    assert enriched_quote.source == "Finnhub + Yahoo Finance"


def test_yahoo_extended_hours_fallback_keeps_waiting_quote_without_extended_price() -> None:
    quote = MarketQuote(
        symbol="AMZN",
        current_price=241.51,
        regular_price=241.51,
        market_session="AFTER_HOURS",
        next_market_open="2026-06-15T09:30:00-04:00",
        timestamp="2026-06-12T20:00:00+00:00",
    )

    enriched_quote = _enrich_with_yahoo_extended_hours(
        quote,
        {
            "symbol": "AMZN",
            "regularMarketPrice": 241.51,
        },
    )

    assert enriched_quote.current_price == 241.51
    assert enriched_quote.extended_hours_price is None
    assert enriched_quote.has_extended_hours_activity is False
    assert enriched_quote.extended_hours_status == "WAITING"

def test_market_stats_sums_intraday_volume_and_ohlc() -> None:
    stats = _stats_from_candle_payload(
        {
            "s": "ok",
            "o": [100.0, 101.0, 102.0],
            "h": [103.0, 104.5, 103.5],
            "l": [99.0, 100.5, 101.5],
            "v": [1000, 2500, 3000],
        }
    )

    assert stats["open"] == 100.0
    assert stats["high"] == 104.5
    assert stats["low"] == 99.0
    assert stats["volume"] == 6500

def test_yahoo_market_stats_fallback_fills_volume_and_day_stats() -> None:
    quote = MarketQuote(
        symbol="NVDA",
        current_price=193.26,
        change=-4.32,
        change_percent=-2.19,
        market_session="OPEN",
        timestamp="2026-07-02T19:00:00+00:00",
    )

    enriched_quote = enrich_with_yahoo_market_stats(
        quote,
        {
            "symbol": "NVDA",
            "regularMarketVolume": 52300000,
            "regularMarketOpen": 198.12,
            "regularMarketDayHigh": 199.45,
            "regularMarketDayLow": 192.8,
            "regularMarketPreviousClose": 197.58,
        },
    )

    assert enriched_quote.volume == 52300000
    assert enriched_quote.open == 198.12
    assert enriched_quote.high == 199.45
    assert enriched_quote.low == 192.8
    assert enriched_quote.previous_close == 197.58
    assert enriched_quote.source == "Finnhub + Yahoo Finance"
