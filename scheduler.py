"""Runs UAE market intelligence scan every 4 hours."""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import pytz

logger = logging.getLogger(__name__)
TZ = pytz.timezone("Asia/Dubai")


def run_market_scan():
    logger.info("Starting UAE market intelligence scan...")
    try:
        from news_fetcher import fetch_uae_news
        from sentiment import analyze_article
        from database import already_analyzed, save_signal
        from telegram_alerts import alert_market_signal, alert_scan_summary

        articles = fetch_uae_news(max_per_query=4)
        analyzed = 0
        bullish_count = 0
        bearish_count = 0
        alerts_fired = 0

        for article in articles:
            url = article["url"]
            if not url or already_analyzed(url):
                continue

            headline = article["headline"]
            body = article.get("body", "")
            if not headline:
                continue

            result = analyze_article(headline, body)
            analyzed += 1

            label = result["sentiment_label"]
            if "BULLISH" in label:
                bullish_count += 1
            elif "BEARISH" in label:
                bearish_count += 1

            alerted = result["alert_worthy"]
            if alerted:
                alert_market_signal(
                    headline=headline,
                    source=article.get("source", "Unknown"),
                    url=url,
                    sentiment_label=label,
                    sentiment_score=result["sentiment_score"],
                    assets=result["assets"],
                    reasoning=result["reasoning"],
                    finbert_label=result["finbert_label"],
                )
                alerts_fired += 1

            save_signal(
                url=url,
                headline=headline,
                source=article.get("source", ""),
                published=article.get("published", ""),
                finbert_label=result["finbert_label"],
                finbert_score=result["finbert_score"],
                sentiment_label=label,
                sentiment_score=result["sentiment_score"],
                confidence=result["confidence"],
                assets=result["assets"],
                reasoning=result["reasoning"],
                alerted=alerted,
            )

        logger.info(f"Scan done — {analyzed} new articles, {alerts_fired} alerts fired")

        if analyzed > 0:
            alert_scan_summary(analyzed, bullish_count, bearish_count, alerts_fired)

    except Exception as e:
        logger.error(f"Market scan error: {e}", exc_info=True)


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone=TZ)
    # Full scan every 4 hours
    scheduler.add_job(run_market_scan, IntervalTrigger(hours=4), id="market_scan", replace_existing=True)
    # Morning briefing at 8am Dubai
    scheduler.add_job(run_market_scan, CronTrigger(hour=8, minute=0, timezone=TZ), id="morning_briefing", replace_existing=True)
    scheduler.start()
    logger.info("Finance scheduler started — scan every 4h + 8am Dubai briefing")
    return scheduler
