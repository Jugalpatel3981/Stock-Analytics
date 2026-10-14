"""News sentiment classification using the Groq LLM API.

All headlines for a request are classified in a single call, and results are
cached in memory by text so each article is only analysed once per process.
"""

import hashlib
import json
from collections import OrderedDict
from dataclasses import dataclass

import httpx

from app.core.config import get_settings

GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"
MAX_INPUT_CHARS = 600
CACHE_SIZE = 2000

SYSTEM_PROMPT = (
    "You are a financial news sentiment classifier. For each numbered news item, decide "
    "whether it is Positive, Neutral, or Negative for the company's stock price, and give "
    "your confidence between 0 and 1. Respond only with JSON of the form "
    '{"results": [{"index": 0, "label": "Positive", "confidence": 0.9}]}, '
    "with exactly one result per item."
)


@dataclass(frozen=True)
class SentimentResult:
    label: str
    score: float


NEUTRAL = SentimentResult(label="Neutral", score=0.0)

_cache: OrderedDict[str, SentimentResult] = OrderedDict()


def _cache_key(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _remember(key: str, result: SentimentResult) -> None:
    _cache[key] = result
    _cache.move_to_end(key)
    while len(_cache) > CACHE_SIZE:
        _cache.popitem(last=False)


def _normalize_label(label: str) -> str:
    normalized_label = label.strip().lower()

    if "positive" in normalized_label:
        return "Positive"

    if "negative" in normalized_label:
        return "Negative"

    return "Neutral"


def _signed_score(label: str, confidence: float) -> float:
    confidence = max(0.0, min(1.0, confidence))

    if label == "Positive":
        return round(confidence, 4)

    if label == "Negative":
        return round(-confidence, 4)

    return 0.0


def _parse_results(content: str, expected: int) -> dict[int, SentimentResult]:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return {}

    items = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return {}

    parsed: dict[int, SentimentResult] = {}
    for item in items:
        if not isinstance(item, dict):
            continue

        try:
            index = int(item.get("index"))
            confidence = float(item.get("confidence", 0))
        except (TypeError, ValueError):
            continue

        if 0 <= index < expected:
            label = _normalize_label(str(item.get("label", "")))
            parsed[index] = SentimentResult(label=label, score=_signed_score(label, confidence))

    return parsed


async def _classify_with_groq(texts: list[str]) -> dict[int, SentimentResult]:
    settings = get_settings()
    numbered_items = "\n".join(f"{index}. {text}" for index, text in enumerate(texts))

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                GROQ_CHAT_COMPLETIONS_URL,
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                json={
                    "model": settings.groq_model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": numbered_items},
                    ],
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
        return {}

    return _parse_results(content, len(texts))


def sentiment_model_name() -> str:
    settings = get_settings()
    if not settings.groq_api_key:
        return "Not configured (set GROQ_API_KEY)"

    return f"{settings.groq_model} via Groq"


async def analyze_sentiments(texts: list[str]) -> list[SentimentResult]:
    """Classify many texts at once. Falls back to Neutral when Groq is unavailable."""
    clean_texts = [text.strip()[:MAX_INPUT_CHARS] for text in texts]
    keys = [_cache_key(text) for text in clean_texts]
    results: list[SentimentResult | None] = [
        _cache.get(key) if text else NEUTRAL for key, text in zip(keys, clean_texts, strict=True)
    ]

    pending = [index for index, result in enumerate(results) if result is None]
    if pending and get_settings().groq_api_key:
        classified = await _classify_with_groq([clean_texts[index] for index in pending])
        for position, index in enumerate(pending):
            result = classified.get(position)
            if result is not None:
                _remember(keys[index], result)
                results[index] = result

    return [result or NEUTRAL for result in results]


async def analyze_sentiment(text: str) -> SentimentResult:
    return (await analyze_sentiments([text]))[0]
