import pytest

from app.core.config import get_settings
from app.services import sentiment_service


@pytest.fixture(autouse=True)
def clear_sentiment_cache():
    sentiment_service._cache.clear()
    yield
    sentiment_service._cache.clear()


@pytest.fixture
def groq_key(monkeypatch):
    monkeypatch.setattr(get_settings(), "groq_api_key", "test-key")


def test_parse_results_maps_labels_to_signed_scores() -> None:
    content = (
        '{"results": ['
        '{"index": 0, "label": "Positive", "confidence": 0.9},'
        '{"index": 1, "label": "negative", "confidence": 0.75},'
        '{"index": 2, "label": "Mixed", "confidence": 0.5},'
        '{"index": 7, "label": "Positive", "confidence": 1}'
        "]}"
    )

    results = sentiment_service._parse_results(content, expected=3)

    assert results[0] == sentiment_service.SentimentResult("Positive", 0.9)
    assert results[1] == sentiment_service.SentimentResult("Negative", -0.75)
    assert results[2] == sentiment_service.SentimentResult("Neutral", 0.0)
    assert 7 not in results


def test_parse_results_ignores_invalid_json() -> None:
    assert sentiment_service._parse_results("not json", expected=2) == {}


async def test_analyze_sentiments_batches_and_caches(monkeypatch, groq_key) -> None:
    calls: list[list[str]] = []

    async def fake_classify(texts: list[str]):
        calls.append(texts)
        return {
            index: sentiment_service.SentimentResult("Positive", 0.8) for index in range(len(texts))
        }

    monkeypatch.setattr(sentiment_service, "_classify_with_groq", fake_classify)

    first = await sentiment_service.analyze_sentiments(["Beat earnings", "Raised guidance"])
    second = await sentiment_service.analyze_sentiments(["Beat earnings", "New product launch"])

    assert [result.label for result in first] == ["Positive", "Positive"]
    assert [result.label for result in second] == ["Positive", "Positive"]
    assert calls == [["Beat earnings", "Raised guidance"], ["New product launch"]]


async def test_analyze_sentiments_falls_back_to_neutral_without_key(monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "groq_api_key", None)

    results = await sentiment_service.analyze_sentiments(["Shares plunge", ""])

    assert results == [sentiment_service.NEUTRAL, sentiment_service.NEUTRAL]


async def test_failed_classification_is_not_cached(monkeypatch, groq_key) -> None:
    async def failing_classify(_texts: list[str]):
        return {}

    monkeypatch.setattr(sentiment_service, "_classify_with_groq", failing_classify)

    results = await sentiment_service.analyze_sentiments(["Shares plunge"])

    assert results == [sentiment_service.NEUTRAL]
    assert sentiment_service._cache == {}
