"""Fetch UAE/MENA financial news via DuckDuckGo."""

import logging
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

UAE_QUERIES = [
    "UAE stock market DFM ADX news today",
    "Dubai Financial Market news",
    "Abu Dhabi Securities Exchange ADX today",
    "UAE economy GDP investment news",
    "Saudi Arabia TASI stock market",
    "MENA finance banking news today",
    "UAE real estate investment fund",
    "Gulf oil energy market news",
    "UAE central bank CBUAE policy",
    "Dubai economy business news today",
]


def fetch_uae_news(max_per_query: int = 4) -> list[dict]:
    """Return deduplicated list of UAE financial news articles."""
    seen_urls = set()
    articles = []

    for query in UAE_QUERIES:
        try:
            with DDGS() as ddgs:
                for r in ddgs.news(query, max_results=max_per_query):
                    url = r.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        articles.append({
                            "url": url,
                            "headline": r.get("title", ""),
                            "body": r.get("body", ""),
                            "source": r.get("source", ""),
                            "published": r.get("date", ""),
                        })
        except Exception as e:
            logger.warning(f"DuckDuckGo query failed for '{query}': {e}")

    logger.info(f"Fetched {len(articles)} unique UAE news articles")
    return articles
