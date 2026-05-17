"""
Volume spike detection + profit/stop-loss tracking.
Runs every 30 min via APScheduler.
"""

import logging
import os
import yfinance as yf
from database import get_active_entries, mark_profit_alerted, mark_stop_alerted, add_price_entry
from telegram_alerts import alert_volume_spike, alert_take_profit, alert_stop_loss

logger = logging.getLogger(__name__)

# Default watchlist — ticker: display name
DEFAULT_WATCHLIST = {
    "BTC-USD": "Bitcoin",
    "ETH-USD": "Ethereum",
    "GC=F": "Gold",
    "CL=F": "Crude Oil WTI",
    "SPY": "S&P 500",
    "QQQ": "NASDAQ 100",
    "FM": "Frontier Markets (UAE+Morocco)",
    "EURUSD=X": "EUR/USD",
}

# Map asset names from news to Yahoo Finance tickers
ASSET_TICKER_MAP = {
    "bitcoin": "BTC-USD",
    "btc": "BTC-USD",
    "ethereum": "ETH-USD",
    "eth": "ETH-USD",
    "gold": "GC=F",
    "oil": "CL=F",
    "crude oil": "CL=F",
    "s&p 500": "SPY",
    "spx": "SPY",
    "nasdaq": "QQQ",
    "dfm": "FM",
    "adx": "FM",
    "eur/usd": "EURUSD=X",
}

VOLUME_SPIKE_RATIO = float(os.environ.get("VOLUME_SPIKE_RATIO", "1.8"))
PROFIT_PCT_1 = float(os.environ.get("PROFIT_PCT_1", "5.0"))   # first take-profit alert
PROFIT_PCT_2 = float(os.environ.get("PROFIT_PCT_2", "10.0"))  # strong profit alert
STOP_PCT = float(os.environ.get("STOP_PCT", "3.0"))           # stop-loss warning


def _get_quote(ticker: str) -> dict | None:
    """Fetch current price and volume for a ticker."""
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="25d", interval="1d")
        if hist.empty or len(hist) < 5:
            return None
        current = hist.iloc[-1]
        avg_volume = hist["Volume"].iloc[:-1].mean()
        current_price = float(current["Close"])
        current_volume = float(current["Volume"])
        return {
            "price": current_price,
            "volume": current_volume,
            "avg_volume": avg_volume,
            "volume_ratio": round(current_volume / avg_volume, 2) if avg_volume > 0 else 0,
            "change_pct": round((current_price / float(hist.iloc[-2]["Close"]) - 1) * 100, 2),
        }
    except Exception as e:
        logger.warning(f"yfinance error for {ticker}: {e}")
        return None


def check_volume_spikes():
    """Check all watchlist tickers for unusual volume. Send Telegram alert when spike detected."""
    extra = os.environ.get("EXTRA_TICKERS", "")
    watchlist = dict(DEFAULT_WATCHLIST)
    if extra:
        for item in extra.split(","):
            item = item.strip()
            if ":" in item:
                ticker, name = item.split(":", 1)
                watchlist[ticker.strip()] = name.strip()
            elif item:
                watchlist[item] = item

    spiked = []
    for ticker, name in watchlist.items():
        q = _get_quote(ticker)
        if not q:
            continue
        ratio = q["volume_ratio"]
        if ratio >= VOLUME_SPIKE_RATIO:
            spiked.append((ticker, name, q))
            logger.info(f"Volume spike: {name} ({ticker}) ratio={ratio:.1f}x price={q['price']:.4f}")

    if spiked:
        alert_volume_spike(spiked)
    else:
        logger.info("Volume check complete — no spikes detected")


def check_profit_targets():
    """Check all active BUY entries for profit or stop-loss conditions."""
    entries = get_active_entries()
    if not entries:
        return

    for entry in entries:
        ticker = entry.get("ticker")
        entry_price = entry.get("entry_price")
        entry_id = entry.get("id")
        asset_name = entry.get("asset_name", ticker)
        profit_alerted_5 = entry.get("profit_alerted_5", 0)
        profit_alerted_10 = entry.get("profit_alerted_10", 0)
        stop_alerted = entry.get("stop_alerted", 0)

        if not ticker or not entry_price:
            continue

        q = _get_quote(ticker)
        if not q:
            continue

        current = q["price"]
        change_pct = ((current - entry_price) / entry_price) * 100

        # Take profit +10%
        if change_pct >= PROFIT_PCT_2 and not profit_alerted_10:
            alert_take_profit(asset_name, ticker, entry_price, current, change_pct, level=2)
            mark_profit_alerted(entry_id, level=2)

        # Take profit +5%
        elif change_pct >= PROFIT_PCT_1 and not profit_alerted_5:
            alert_take_profit(asset_name, ticker, entry_price, current, change_pct, level=1)
            mark_profit_alerted(entry_id, level=1)

        # Stop-loss -3%
        elif change_pct <= -STOP_PCT and not stop_alerted:
            alert_stop_loss(asset_name, ticker, entry_price, current, change_pct)
            mark_stop_alerted(entry_id)


def assets_to_tickers(assets: list[str]) -> list[str]:
    """Convert asset names from news analysis to Yahoo Finance tickers."""
    tickers = []
    for asset in assets:
        ticker = ASSET_TICKER_MAP.get(asset.lower())
        if ticker and ticker not in tickers:
            tickers.append(ticker)
    return tickers
