from __future__ import annotations

import asyncio

from app.services.stock_service import normalize_ticker

_training_queue: asyncio.Queue[str] | None = None
_queued_symbols: set[str] = set()


def get_training_queue() -> asyncio.Queue[str]:
    global _training_queue
    if _training_queue is None:
        _training_queue = asyncio.Queue()
    return _training_queue


def enqueue_training_symbol(ticker: str) -> bool:
    normalized_ticker = normalize_ticker(ticker)
    if normalized_ticker in _queued_symbols:
        return False

    _queued_symbols.add(normalized_ticker)
    get_training_queue().put_nowait(normalized_ticker)
    return True


def mark_training_symbol_complete(ticker: str) -> None:
    _queued_symbols.discard(normalize_ticker(ticker))


def is_training_symbol_queued(ticker: str) -> bool:
    return normalize_ticker(ticker) in _queued_symbols
