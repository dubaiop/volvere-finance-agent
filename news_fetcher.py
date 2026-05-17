"""Fetch financial news for UAE, Kuwait, Europe, Japan, and Global markets via DuckDuckGo."""

import logging
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

MARKET_QUERIES = {
    "UAE": [
        "UAE stock market DFM ADX news today",
        "Dubai Financial Market news",
        "Abu Dhabi Securities Exchange ADX today",
        "UAE economy GDP investment news",
        "UAE real estate investment fund",
        "UAE central bank CBUAE policy",
        "Dubai economy business news today",
        "UAE banking sector news today",
    ],
    "Kuwait": [
        "Kuwait Stock Exchange KSE news today",
        "Kuwait economy investment news",
        "Kuwait Central Bank monetary policy",
        "Boursa Kuwait market news today",
        "Kuwait dinar KWD investment news",
        "Kuwait oil fund sovereign wealth",
        "Kuwait GDP growth business news",
    ],
    "Europe": [
        "FTSE 100 London stock market news today",
        "DAX Frankfurt stock market Germany news",
        "CAC 40 Paris stock market France news",
        "European Central Bank ECB interest rate",
        "Euro Stoxx 50 European stocks today",
        "European economy GDP inflation news",
        "Euronext stock exchange news today",
    ],
    "Japan": [
        "Nikkei 225 Tokyo stock market news today",
        "Japan economy Bank of Japan policy",
        "TSE Tokyo Stock Exchange news today",
        "Japanese yen JPY exchange rate news",
        "Japan GDP growth investment news",
        "Sony Toyota Softbank stock market Japan",
        "Japan inflation interest rate news today",
    ],
    "Global": [
        "S&P 500 NASDAQ stock market news today",
        "Federal Reserve interest rate decision",
        "Bitcoin crypto market news today",
        "Gold silver commodities price news",
        "Oil price OPEC energy market today",
        "Global inflation recession forecast 2025",
        "US dollar DXY currency market news",
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

    logger.info(f"Fetched {len(articles)} unique articles across UAE, Kuwait, Europe, Japan, Global")
    return articles


def fetch_uae_news(max_per_query: int = 4) -> list[dict]:
    return fetch_all_news(max_per_query)
