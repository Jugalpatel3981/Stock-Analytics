from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings

TAVILY_SEARCH_URL = "https://api.tavily.com/search"


@dataclass(frozen=True)
class TavilySearchResult:
    title: str
    url: str | None
    content: str | None
    source_name: str
    published_at: str | None = None


def _source_name_from_url(url: str | None) -> str:
    if not url:
        return "Web"

    host = urlparse(url).netloc.replace("www.", "")
    return host or "Web"


async def search_market_news(query: str, max_results: int = 5) -> list[TavilySearchResult]:
    settings = get_settings()

    if not settings.tavily_api_key:
        return []

    payload = {
        "query": query,
        "topic": "finance",
        "search_depth": settings.tavily_search_depth,
        "max_results": max_results,
        "include_answer": False,
        "include_raw_content": False,
        "time_range": "week",
    }
    headers = {
        "Authorization": f"Bearer {settings.tavily_api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(TAVILY_SEARCH_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError:
        return []

    results = []
    for item in data.get("results", []):
        title = str(item.get("title") or "").strip()
        url = item.get("url")

        if not title:
            continue

        results.append(
            TavilySearchResult(
                title=title,
                url=str(url) if url else None,
                content=item.get("content"),
                source_name=_source_name_from_url(str(url) if url else None),
                published_at=item.get("published_date") or item.get("published_at"),
            )
        )

    return results
