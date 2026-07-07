from typing import Any


def to_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def to_int(value: Any) -> int | None:
    if value is None:
        return None

    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def normalize_symbols(symbols: str) -> list[str]:
    return [
        symbol.strip().upper()
        for symbol in symbols.split(",")
        if symbol.strip()
    ][:25]
