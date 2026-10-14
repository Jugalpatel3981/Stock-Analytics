from dataclasses import dataclass

import httpx

from app.core.config import get_settings


@dataclass(frozen=True)
class SentimentResult:
    label: str
    score: float


def _normalize_label(label: str) -> str:
    normalized_label = label.strip().lower()

    if "positive" in normalized_label:
        return "Positive"

    if "negative" in normalized_label:
        return "Negative"

    return "Neutral"


def _signed_score(label: str, confidence: float) -> float:
    if label == "Positive":
        return round(confidence, 4)

    if label == "Negative":
        return round(-confidence, 4)

    return 0.0


def _fallback_result() -> SentimentResult:
    return SentimentResult(label="Neutral", score=0.0)


async def analyze_sentiment(text: str) -> SentimentResult:
    settings = get_settings()
    clean_text = text.strip()

    if not clean_text:
        return _fallback_result()

    headers = {}
    if settings.huggingface_api_token:
        headers["Authorization"] = f"Bearer {settings.huggingface_api_token}"

    url = f"https://api-inference.huggingface.co/models/{settings.huggingface_sentiment_model}"

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                url,
                headers=headers,
                json={"inputs": clean_text[:1500], "options": {"wait_for_model": True}},
            )
            response.raise_for_status()
    except httpx.HTTPError:
        return _fallback_result()

    payload = response.json()
    predictions = (
        payload[0]
        if isinstance(payload, list) and payload and isinstance(payload[0], list)
        else payload
    )

    if not isinstance(predictions, list) or not predictions:
        return _fallback_result()

    top_prediction = max(
        predictions, key=lambda item: float(item.get("score", 0)) if isinstance(item, dict) else 0
    )

    if not isinstance(top_prediction, dict):
        return _fallback_result()

    label = _normalize_label(str(top_prediction.get("label", "")))
    confidence = float(top_prediction.get("score", 0))

    return SentimentResult(label=label, score=_signed_score(label, confidence))
