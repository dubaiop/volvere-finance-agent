"""Fetch financial news for UAE/MENA, Morocco, and Global markets via DuckDuckGo."""

import logging
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

MARKET_QUERIES = {
    "UAE/MENA": [
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
    ],
    "Morocco": [
        "Bourse de Casablanca CSE stock market today",
        "Morocco economy investment news",
        "Maroc Telecom Attijariwafa bank stock",
        "Morocco MAD dirham exchange rate",
        "Bank Al-Maghrib monetary policy Morocco",
        "Morocco GDP growth investment 2025",
        "OCP Group Maroc phosphate stock news",
        "Morocco real estate infrastructure news",
    ],
    "Global": [
        "S&P 500 NASDAQ stock market news today",
        "Federal Reserve interest rate decision",
        "Bitcoin crypto market news today",
        "Gold silver commodities price news",
        "FTSE 100 European stock market today",
        "China economy stock market news",
        "Oil price OPEC energy market today",
        "Global inflation recession forecast 2025",
    ],
}


def fetch_all_news(max_per_query: int = 4) -> list[dict]:
    """Return deduplicated list of financial news articles across all markets."""
    seen_urls = set()
    articles = []

    for market, queries in MARKET_QUERIES.items():
        for query in queries:
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
                                "market": market,
                            })
            except Exception as e:
                logger.warning(f"DuckDuckGo query failed for '{query}': {e}")

    logger.info(f"Fetched {len(articles)} unique articles across UAE/MENA, Morocco, Global")
    return articles


# Keep backwards-compatible alias
def fetch_uae_news(max_per_query: int = 4) -> list[dict]:
    return fetch_all_news(max_per_query)
