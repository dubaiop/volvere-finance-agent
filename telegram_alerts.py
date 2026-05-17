"""Telegram alerts for UAE market signals."""

import logging
import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)

LABEL_EMOJI = {
    "STRONG_BULLISH": "🚀",
    "BULLISH": "📈",
    "NEUTRAL": "➡️",
    "BEARISH": "📉",
    "STRONG_BEARISH": "💥",
}


def _send(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram not configured — skipping alert")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")


def alert_market_signal(headline: str, source: str, url: str,
                         sentiment_label: str, sentiment_score: float,
                         assets: list, reasoning: str, finbert_label: str):
    emoji = LABEL_EMOJI.get(sentiment_label, "📊")
    score_bar = "█" * min(int(abs(sentiment_score) * 10), 10)
    assets_str = ", ".join(assets) if assets else "General Market"

    text = (
        f"{emoji} <b>UAE MARKET SIGNAL — {sentiment_label}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📰 <b>{headline}</b>\n\n"
        f"🔬 <b>FinBERT:</b> {finbert_label.upper()}\n"
        f"📊 <b>Score:</b> {sentiment_score:+.2f} [{score_bar}]\n"
        f"🏢 <b>Assets:</b> {assets_str}\n"
        f"🔍 <b>Source:</b> {source}\n\n"
        f"💡 <b>Analysis:</b>\n{reasoning}\n\n"
        f"🔗 <a href='{url}'>Read full article</a>"
    )
    _send(text)


def alert_scan_summary(total: int, bullish: int, bearish: int, alerts_fired: int):
    text = (
        f"📊 <b>UAE Market Scan Complete</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📰 Articles analyzed: <b>{total}</b>\n"
        f"📈 Bullish signals: <b>{bullish}</b>\n"
        f"📉 Bearish signals: <b>{bearish}</b>\n"
        f"🔔 Alerts fired: <b>{alerts_fired}</b>"
    )
    _send(text)
