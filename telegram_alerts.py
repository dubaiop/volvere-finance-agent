"""Telegram alerts for multi-market financial signals with investment advice."""

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

REC_EMOJI = {"BUY": "🟢", "HOLD": "🟡", "SELL": "🔴"}
RISK_EMOJI = {"LOW": "🔵", "MEDIUM": "🟠", "HIGH": "🔴"}

MARKET_FLAG = {
    "UAE": "🇦🇪",
    "Kuwait": "🇰🇼",
    "Europe": "🇪🇺",
    "Japan": "🇯🇵",
    "Global": "🌍",
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
                         market: str, sentiment_label: str, sentiment_score: float,
                         assets: list, reasoning: str, finbert_label: str,
                         recommendation: str = "HOLD", risk_level: str = "MEDIUM",
                         stop_loss: str = "N/A", allocation: str = "",
                         advice_summary: str = ""):
    emoji = LABEL_EMOJI.get(sentiment_label, "📊")
    rec_emoji = REC_EMOJI.get(recommendation, "🟡")
    risk_emoji = RISK_EMOJI.get(risk_level, "🟠")
    flag = MARKET_FLAG.get(market, "🌍")
    score_bar = "█" * min(int(abs(sentiment_score) * 10), 10)
    assets_str = ", ".join(assets) if assets else "General Market"

    text = (
        f"{emoji} <b>MARKET SIGNAL — {sentiment_label}</b> {flag} {market}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📰 <b>{headline}</b>\n\n"
        f"🔬 <b>FinBERT:</b> {finbert_label.upper()}\n"
        f"📊 <b>Score:</b> {sentiment_score:+.2f} [{score_bar}]\n"
        f"🏢 <b>Assets:</b> {assets_str}\n"
        f"🔍 <b>Source:</b> {source}\n\n"
        f"💡 <b>Analysis:</b>\n{reasoning}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>INVESTMENT ADVICE</b>\n"
        f"{rec_emoji} <b>Action:</b> {recommendation}\n"
        f"{risk_emoji} <b>Risk:</b> {risk_level}\n"
        f"🛡 <b>Stop-Loss:</b> {stop_loss}\n"
        f"💼 <b>Allocation:</b> {allocation}\n\n"
        f"✏️ <i>{advice_summary}</i>\n\n"
        f"🔗 <a href='{url}'>Read full article</a>"
    )
    _send(text)


def alert_volume_spike(spiked: list):
    """Alert when unusual volume detected on watchlist assets."""
    lines = ["⚡ <b>VOLUME SPIKE DETECTED</b>\n━━━━━━━━━━━━━━━━━━━━"]
    for ticker, name, q in spiked:
        direction = "📈" if q["change_pct"] >= 0 else "📉"
        lines.append(
            f"\n{direction} <b>{name}</b> (<code>{ticker}</code>)\n"
            f"💰 Price: <b>${q['price']:,.4f}</b> ({q['change_pct']:+.2f}%)\n"
            f"📊 Volume: <b>{q['volume_ratio']:.1f}x</b> above average\n"
            f"⚠️ High activity — consider reviewing position"
        )
    lines.append("\n💡 Check your Financial Intelligence dashboard for latest signals.")
    _send("\n".join(lines))


def alert_take_profit(asset_name: str, ticker: str, entry: float, current: float,
                      change_pct: float, level: int = 1):
    emoji = "🎯" if level == 1 else "🚀"
    label = f"+{change_pct:.1f}% — {'Take partial profit' if level == 1 else 'STRONG PROFIT — Consider full exit'}"
    text = (
        f"{emoji} <b>TAKE PROFIT ALERT</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💼 <b>{asset_name}</b> (<code>{ticker}</code>)\n\n"
        f"📥 Entry price: <b>${entry:,.4f}</b>\n"
        f"📤 Current price: <b>${current:,.4f}</b>\n"
        f"📈 Gain: <b style='color:green'>{label}</b>\n\n"
        f"✅ Your BUY signal is profitable. Consider taking profit now."
    )
    _send(text)


def alert_stop_loss(asset_name: str, ticker: str, entry: float, current: float,
                    change_pct: float):
    text = (
        f"🛡 <b>STOP-LOSS WARNING</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💼 <b>{asset_name}</b> (<code>{ticker}</code>)\n\n"
        f"📥 Entry price: <b>${entry:,.4f}</b>\n"
        f"📤 Current price: <b>${current:,.4f}</b>\n"
        f"📉 Loss: <b>{change_pct:.1f}%</b>\n\n"
        f"⚠️ Stop-loss level reached. Consider exiting to protect capital."
    )
    _send(text)


def alert_scan_summary(total: int, bullish: int, bearish: int, alerts_fired: int):
    text = (
        f"📊 <b>Multi-Market Scan Complete</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🇦🇪 UAE · 🇰🇼 Kuwait · 🇪🇺 Europe · 🇯🇵 Japan · 🌍 Global\n"
        f"📰 Articles analyzed: <b>{total}</b>\n"
        f"📈 Bullish signals: <b>{bullish}</b>\n"
        f"📉 Bearish signals: <b>{bearish}</b>\n"
        f"🔔 Alerts fired: <b>{alerts_fired}</b>"
    )
    _send(text)
