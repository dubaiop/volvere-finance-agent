import os, sqlite3
from datetime import datetime

DATABASE_URL = os.environ.get("DATABASE_URL", "")

if DATABASE_URL:
    import psycopg2, psycopg2.extras
    def _conn():
        return psycopg2.connect(DATABASE_URL, sslmode="require")
else:
    def _conn():
        c = sqlite3.connect("finance_agent.db")
        c.row_factory = sqlite3.Row
        return c


def init_db():
    if DATABASE_URL:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS market_signals (
                        id SERIAL PRIMARY KEY,
                        url TEXT UNIQUE,
                        headline TEXT,
                        source TEXT,
                        published TEXT,
                        market TEXT DEFAULT 'UAE/MENA',
                        finbert_label TEXT,
                        finbert_score REAL,
                        sentiment_label TEXT,
                        sentiment_score REAL,
                        confidence REAL,
                        assets TEXT,
                        reasoning TEXT,
                        recommendation TEXT DEFAULT 'HOLD',
                        risk_level TEXT DEFAULT 'MEDIUM',
                        stop_loss TEXT,
                        allocation TEXT,
                        advice_summary TEXT,
                        alerted BOOLEAN DEFAULT FALSE,
                        analyzed_at TEXT DEFAULT NOW()
                    )
                """)
                # Migrate existing tables
                for col, definition in [
                    ("market", "TEXT DEFAULT 'UAE/MENA'"),
                    ("recommendation", "TEXT DEFAULT 'HOLD'"),
                    ("risk_level", "TEXT DEFAULT 'MEDIUM'"),
                    ("stop_loss", "TEXT"),
                    ("allocation", "TEXT"),
                    ("advice_summary", "TEXT"),
                ]:
                    try:
                        cur.execute(f"ALTER TABLE market_signals ADD COLUMN IF NOT EXISTS {col} {definition}")
                    except Exception:
                        pass
            conn.commit()
    else:
        with _conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS market_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE,
                    headline TEXT,
                    source TEXT,
                    published TEXT,
                    market TEXT DEFAULT 'UAE/MENA',
                    finbert_label TEXT,
                    finbert_score REAL,
                    sentiment_label TEXT,
                    sentiment_score REAL,
                    confidence REAL,
                    assets TEXT,
                    reasoning TEXT,
                    recommendation TEXT DEFAULT 'HOLD',
                    risk_level TEXT DEFAULT 'MEDIUM',
                    stop_loss TEXT,
                    allocation TEXT,
                    advice_summary TEXT,
                    alerted INTEGER DEFAULT 0,
                    analyzed_at TEXT DEFAULT (datetime('now'))
                )
            """)
            # Migrate existing tables
            for col, definition in [
                ("market", "TEXT DEFAULT 'UAE/MENA'"),
                ("recommendation", "TEXT DEFAULT 'HOLD'"),
                ("risk_level", "TEXT DEFAULT 'MEDIUM'"),
                ("stop_loss", "TEXT"),
                ("allocation", "TEXT"),
                ("advice_summary", "TEXT"),
            ]:
                try:
                    conn.execute(f"ALTER TABLE market_signals ADD COLUMN {col} {definition}")
                except Exception:
                    pass
            conn.commit()


def already_analyzed(url: str) -> bool:
    if DATABASE_URL:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM market_signals WHERE url=%s LIMIT 1", (url,))
                return cur.fetchone() is not None
    else:
        with _conn() as conn:
            return conn.execute("SELECT 1 FROM market_signals WHERE url=? LIMIT 1", (url,)).fetchone() is not None


def save_signal(url, headline, source, published, market,
                finbert_label, finbert_score, sentiment_label, sentiment_score,
                confidence, assets, reasoning, recommendation, risk_level,
                stop_loss, allocation, advice_summary, alerted):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    assets_str = ", ".join(assets) if isinstance(assets, list) else str(assets)
    if DATABASE_URL:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO market_signals
                        (url, headline, source, published, market,
                         finbert_label, finbert_score, sentiment_label, sentiment_score,
                         confidence, assets, reasoning, recommendation, risk_level,
                         stop_loss, allocation, advice_summary, alerted, analyzed_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (url) DO NOTHING
                """, (url, headline, source, published, market,
                      finbert_label, finbert_score, sentiment_label, sentiment_score,
                      confidence, assets_str, reasoning, recommendation, risk_level,
                      stop_loss, allocation, advice_summary, alerted, now))
            conn.commit()
    else:
        with _conn() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO market_signals
                    (url, headline, source, published, market,
                     finbert_label, finbert_score, sentiment_label, sentiment_score,
                     confidence, assets, reasoning, recommendation, risk_level,
                     stop_loss, allocation, advice_summary, alerted, analyzed_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (url, headline, source, published, market,
                  finbert_label, finbert_score, sentiment_label, sentiment_score,
                  confidence, assets_str, reasoning, recommendation, risk_level,
                  stop_loss, allocation, advice_summary, 1 if alerted else 0, now))
            conn.commit()


def get_signals(limit=100, market: str = None) -> list[dict]:
    if DATABASE_URL:
        with _conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                if market and market != "All":
                    cur.execute("SELECT * FROM market_signals WHERE market=%s ORDER BY analyzed_at DESC LIMIT %s", (market, limit))
                else:
                    cur.execute("SELECT * FROM market_signals ORDER BY analyzed_at DESC LIMIT %s", (limit,))
                return [dict(r) for r in cur.fetchall()]
    else:
        with _conn() as conn:
            if market and market != "All":
                rows = conn.execute("SELECT * FROM market_signals WHERE market=? ORDER BY analyzed_at DESC LIMIT ?", (market, limit)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM market_signals ORDER BY analyzed_at DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]


def get_stats() -> dict:
    if DATABASE_URL:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM market_signals")
                total = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM market_signals WHERE sentiment_label IN ('BULLISH','STRONG_BULLISH')")
                bullish = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM market_signals WHERE sentiment_label IN ('BEARISH','STRONG_BEARISH')")
                bearish = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM market_signals WHERE alerted=TRUE")
                alerts = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM market_signals WHERE recommendation='BUY'")
                buys = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM market_signals WHERE recommendation='SELL'")
                sells = cur.fetchone()[0]
    else:
        with _conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM market_signals").fetchone()[0]
            bullish = conn.execute("SELECT COUNT(*) FROM market_signals WHERE sentiment_label IN ('BULLISH','STRONG_BULLISH')").fetchone()[0]
            bearish = conn.execute("SELECT COUNT(*) FROM market_signals WHERE sentiment_label IN ('BEARISH','STRONG_BEARISH')").fetchone()[0]
            alerts = conn.execute("SELECT COUNT(*) FROM market_signals WHERE alerted=1").fetchone()[0]
            buys = conn.execute("SELECT COUNT(*) FROM market_signals WHERE recommendation='BUY'").fetchone()[0]
            sells = conn.execute("SELECT COUNT(*) FROM market_signals WHERE recommendation='SELL'").fetchone()[0]
    return {"total": total, "bullish": bullish, "bearish": bearish,
            "alerts_sent": alerts, "buys": buys, "sells": sells}
