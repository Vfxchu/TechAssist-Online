"""
Web search service — tries Tavily first, falls back to Serper (Google).
Used by the Claude service to fetch live IT documentation during the suggest phase.
"""
import logging
import requests
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_IT_DOMAINS = [
    "microsoft.com", "learn.microsoft.com", "support.microsoft.com",
    "support.apple.com", "support.google.com",
    "stackoverflow.com", "superuser.com", "askubuntu.com",
]


def search_web(query: str) -> list[dict]:
    """Return a list of {title, url, content} dicts for the given query."""
    if not settings.search_api_key:
        logger.warning("SEARCH_API_KEY not configured — web search unavailable.")
        return []

    results = _tavily_search(query)
    if results:
        return results
    return _serper_search(query)


def _tavily_search(query: str) -> list[dict]:
    try:
        resp = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": settings.search_api_key,
                "query": query,
                "search_depth": "advanced",
                "include_answer": True,
                "include_domains": _IT_DOMAINS,
                "max_results": 5,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        results: list[dict] = []
        if data.get("answer"):
            results.append({"title": "Direct Answer", "url": "", "content": data["answer"]})
        for r in data.get("results", [])[:4]:
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": (r.get("content") or "")[:700],
            })
        return results
    except Exception as exc:
        logger.error("Tavily search failed: %s", exc)
        return []


def _serper_search(query: str) -> list[dict]:
    try:
        site_filter = " OR ".join(f"site:{d}" for d in _IT_DOMAINS[:5])
        resp = requests.post(
            "https://google.serper.dev/search",
            headers={
                "X-API-KEY": settings.search_api_key,
                "Content-Type": "application/json",
            },
            json={"q": f"{query} ({site_filter})", "num": 5},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        results: list[dict] = []
        if data.get("answerBox", {}).get("answer"):
            results.append({
                "title": "Quick Answer",
                "url": "",
                "content": data["answerBox"]["answer"],
            })
        for r in data.get("organic", [])[:4]:
            results.append({
                "title": r.get("title", ""),
                "url": r.get("link", ""),
                "content": r.get("snippet", ""),
            })
        return results
    except Exception as exc:
        logger.error("Serper search failed: %s", exc)
        return []
