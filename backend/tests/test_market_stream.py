from datetime import datetime

from fastapi.testclient import TestClient

from app.core.security import create_access_token, create_stream_token
from app.main import app
from app.market.market_session import get_market_session, session_prices
from app.market.rest_market_service import (
    enrich_with_yahoo_extended_hours,
    enrich_with_yahoo_market_stats,
)
from app.schemas.market import MarketQuote
from app.services.market_stream_service import normalize_symbols

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


def test_market_stream_accepts_stream_token_in_url() -> None:
    token = create_stream_token(subject="123")

    with client.websocket_connect(f"/api/v1/market/stream?symbols=&token={token}") as websocket:
        payload = websocket.receive_json()

    assert payload["message"] == "At least one symbol is required."


def test_market_stream_rejects_regular_access_token_in_url() -> None:
    token = create_access_token(subject="123")

    with client.websocket_connect(f"/api/v1/market/stream?symbols=NVDA&token={token}") as websocket:
        payload = websocket.receive_json()

    assert payload["message"] == "Invalid stream token."


def test_stream_token_cannot_be_used_for_api_requests() -> None:
    token = create_stream_token(subject="123")

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_stream_token_endpoint_requires_authentication() -> None:
    assert client.get("/api/v1/market/stream-token").status_code == 401


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
    regular_price, extended_hours_price = session_prices(
        market_session="AFTER_HOURS",
        current_price=234.11,
        previous_close=232.79,
        has_extended_activity=False,
    )

    assert regular_price == 234.11
    assert extended_hours_price is None


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
            "volume": 52300000,
            "open": 198.12,
            "high": 199.45,
            "low": 192.8,
            "previous_close": 197.58,
        },
    )

    assert enriched_quote.volume == 52300000
    assert enriched_quote.open == 198.12
    assert enriched_quote.high == 199.45
    assert enriched_quote.low == 192.8
    assert enriched_quote.previous_close == 197.58
    assert enriched_quote.source == "Finnhub + Yahoo Finance"


def test_extended_hours_measures_change_against_the_regular_close() -> None:
    quote = MarketQuote(
        symbol="MSFT",
        current_price=521.13,
        change=-12.03,
        change_percent=-2.2573,
        previous_close=533.16,
        regular_price=521.13,
        market_session="AFTER_HOURS",
        extended_hours_status="WAITING",
        timestamp="2026-11-11T21:00:00+00:00",
    )

    enriched = enrich_with_yahoo_extended_hours(
        quote, {"regular_price": 521.13, "post_market_price": 522.05, "previous_close": 533.16}
    )

    assert enriched.current_price == 522.05
    assert enriched.extended_hours_price == 522.05
    assert enriched.regular_price == 521.13
    assert enriched.has_extended_hours_activity is True
    assert enriched.extended_hours_status == "ACTIVE"
    # Up 0.92 from the regular close, even though the stock fell during the day.
    assert round(enriched.change, 2) == 0.92
    assert round(enriched.change_percent, 2) == 0.18


def test_extended_hours_leaves_quote_alone_without_an_extended_price() -> None:
    quote = MarketQuote(
        symbol="AMZN",
        current_price=266.17,
        regular_price=266.17,
        market_session="AFTER_HOURS",
        extended_hours_status="WAITING",
        timestamp="2026-11-11T21:00:00+00:00",
    )

    assert enrich_with_yahoo_extended_hours(quote, {"post_market_price": None}) == quote
    assert enrich_with_yahoo_extended_hours(quote, None) == quote


def test_extended_hours_is_ignored_during_regular_trading() -> None:
    quote = MarketQuote(
        symbol="AMZN",
        current_price=266.17,
        market_session="OPEN",
        timestamp="2026-11-11T16:00:00+00:00",
    )

    assert enrich_with_yahoo_extended_hours(quote, {"post_market_price": 270.0}) == quote


def test_market_stats_keep_figures_the_finnhub_quote_already_has() -> None:
    quote = MarketQuote(
        symbol="NVDA",
        current_price=193.26,
        open=198.0,
        high=199.0,
        low=192.0,
        previous_close=197.0,
        market_session="OPEN",
        timestamp="2026-07-02T19:00:00+00:00",
    )

    enriched_quote = enrich_with_yahoo_market_stats(
        quote, {"volume": 1000, "open": 1.0, "high": 2.0, "low": 0.5, "previous_close": 1.5}
    )

    assert enriched_quote.volume == 1000
    assert (enriched_quote.open, enriched_quote.high, enriched_quote.low) == (198.0, 199.0, 192.0)
    assert enriched_quote.previous_close == 197.0
