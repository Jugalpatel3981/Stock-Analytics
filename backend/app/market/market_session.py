from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.schemas.market import ExtendedHoursStatus, MarketSession

MARKET_TIMEZONE = ZoneInfo("America/New_York")
PRE_MARKET_START = time(4, 0)
REGULAR_MARKET_START = time(9, 30)
REGULAR_MARKET_CLOSE = time(16, 0)
AFTER_HOURS_CLOSE = time(20, 0)


def _is_weekday(value: date) -> bool:
    return value.weekday() < 5


def _next_weekday(value: date) -> date:
    next_day = value + timedelta(days=1)
    while not _is_weekday(next_day):
        next_day += timedelta(days=1)

    return next_day


def _market_datetime(day: date, value: time) -> datetime:
    return datetime.combine(day, value, tzinfo=MARKET_TIMEZONE)


def get_market_session(now: datetime | None = None) -> tuple[MarketSession, str | None]:
    eastern_now = (now or datetime.now(UTC)).astimezone(MARKET_TIMEZONE)
    current_day = eastern_now.date()
    current_time = eastern_now.time()

    if _is_weekday(current_day):
        if PRE_MARKET_START <= current_time < REGULAR_MARKET_START:
            return "PRE_MARKET", _market_datetime(current_day, REGULAR_MARKET_START).isoformat()

        if REGULAR_MARKET_START <= current_time < REGULAR_MARKET_CLOSE:
            return "OPEN", None

        if REGULAR_MARKET_CLOSE <= current_time < AFTER_HOURS_CLOSE:
            next_open_day = _next_weekday(current_day)
            return "AFTER_HOURS", _market_datetime(next_open_day, REGULAR_MARKET_START).isoformat()

        if current_time < PRE_MARKET_START:
            return "CLOSED", _market_datetime(current_day, REGULAR_MARKET_START).isoformat()

    next_open_day = _next_weekday(current_day)
    return "CLOSED", _market_datetime(next_open_day, REGULAR_MARKET_START).isoformat()


def has_extended_hours_activity(
    market_session: MarketSession,
    quote_timestamp: datetime,
    now: datetime | None = None,
) -> bool:
    eastern_quote_time = quote_timestamp.astimezone(MARKET_TIMEZONE)
    eastern_now = (now or datetime.now(UTC)).astimezone(MARKET_TIMEZONE)

    if eastern_quote_time.date() != eastern_now.date():
        return False

    if market_session == "PRE_MARKET":
        return PRE_MARKET_START <= eastern_quote_time.time() < REGULAR_MARKET_START

    if market_session == "AFTER_HOURS":
        return REGULAR_MARKET_CLOSE < eastern_quote_time.time() < AFTER_HOURS_CLOSE

    return False


def session_prices(
    market_session: MarketSession,
    current_price: float,
    previous_close: float | None,
    has_extended_activity: bool,
) -> tuple[float | None, float | None]:
    if market_session == "PRE_MARKET":
        return previous_close, current_price if has_extended_activity else None

    if market_session == "AFTER_HOURS":
        if has_extended_activity:
            return previous_close, current_price

        return current_price, None

    if market_session == "CLOSED":
        return current_price, None

    return current_price, None


def extended_hours_status(
    market_session: MarketSession,
    has_extended_activity: bool,
) -> ExtendedHoursStatus:
    if has_extended_activity:
        return "ACTIVE"

    if market_session in ("PRE_MARKET", "AFTER_HOURS"):
        return "WAITING"

    return "NONE"
