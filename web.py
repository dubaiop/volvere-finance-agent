"""Multi-Market Financial Intelligence Agent — FastAPI dashboard."""

import threading
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from config import PORT
from database import init_db, get_signals, get_stats, get_active_entries

app = FastAPI(title="Financial Intelligence Agent", version="2.0.0")
_scheduler = None


@app.on_event("startup")
async def startup():
    global _scheduler
    init_db()
    from scheduler import start_scheduler
    _scheduler = start_scheduler()


@app.on_event("shutdown")
async def shutdown():
    if _scheduler:
        _scheduler.shutdown()


LABEL_COLOR = {
    "STRONG_BULLISH": "#10b981",
    "BULLISH": "#34d399",
    "NEUTRAL": "#8080a8",
    "BEARISH": "#f87171",
    "STRONG_BEARISH": "#ef4444",
}
LABEL_EMOJI = {
    "STRONG_BULLISH": "🚀",
    "BULLISH": "📈",
    "NEUTRAL": "➡️",
    "BEARISH": "📉",
    "STRONG_BEARISH": "💥",
}
REC_COLOR = {"BUY": "#10b981", "HOLD": "#f59e0b", "SELL": "#ef4444"}
RISK_COLOR = {"LOW": "#34d399", "MEDIUM": "#f59e0b", "HIGH": "#ef4444"}
MARKET_FLAG = {"UAE/MENA": "🇦🇪", "Morocco": "🇲🇦", "Global": "🌍"}

# Asset → platform URL (opens directly to trade/chart page)
ASSET_LINKS = {
    # UAE
    "DFM": "https://www.dfm.ae/the-exchange/market-information/market-summary",
    "ADX": "https://www.adx.ae/English/Pages/MarketSummary.aspx",
    "AED": "https://www.xe.com/currencyconverter/convert/?Amount=1&From=AED&To=USD",
    "UAE Banking": "https://www.dfm.ae/the-exchange/listed-securities/equities",
    "UAE Real Estate": "https://www.dfm.ae/the-exchange/listed-securities/equities",
    "TASI": "https://www.saudiexchange.sa/wps/portal/saudiexchange/home",
    # Morocco
    "CSE": "https://www.casablanca-bourse.com/bourseweb/Liste-valeurs.aspx?Cat=2",
    "MAD": "https://www.xe.com/currencyconverter/convert/?Amount=1&From=MAD&To=USD",
    "Attijariwafa": "https://www.casablanca-bourse.com/bourseweb/Fiche-valeur.aspx?s=ATW",
    "OCP": "https://www.casablanca-bourse.com/bourseweb/Fiche-valeur.aspx?s=OCP",
    "Maroc Telecom": "https://www.casablanca-bourse.com/bourseweb/Fiche-valeur.aspx?s=IAM",
    # Crypto → Binance
    "Bitcoin": "https://www.binance.com/en/trade/BTC_USDT",
    "BTC": "https://www.binance.com/en/trade/BTC_USDT",
    "Ethereum": "https://www.binance.com/en/trade/ETH_USDT",
    "ETH": "https://www.binance.com/en/trade/ETH_USDT",
    # Global → TradingView
    "Gold": "https://www.tradingview.com/symbols/XAUUSD/",
    "Oil": "https://www.tradingview.com/symbols/USOIL/",
    "Crude Oil": "https://www.tradingview.com/symbols/USOIL/",
    "S&P 500": "https://www.tradingview.com/symbols/SPY/",
    "SPX": "https://www.tradingview.com/symbols/SPY/",
    "NASDAQ": "https://www.tradingview.com/symbols/QQQ/",
    "EUR/USD": "https://www.tradingview.com/symbols/EURUSD/",
    "USD": "https://www.tradingview.com/symbols/EURUSD/",
}

# Ticker → platform URL for positions table
TICKER_LINKS = {
    "BTC-USD": "https://www.binance.com/en/trade/BTC_USDT",
    "ETH-USD": "https://www.binance.com/en/trade/ETH_USDT",
    "GC=F": "https://www.tradingview.com/symbols/XAUUSD/",
    "CL=F": "https://www.tradingview.com/symbols/USOIL/",
    "SPY": "https://www.tradingview.com/symbols/SPY/",
    "QQQ": "https://www.tradingview.com/symbols/QQQ/",
    "FM": "https://finance.yahoo.com/quote/FM/",
    "EURUSD=X": "https://www.tradingview.com/symbols/EURUSD/",
}


def _asset_links_html(assets_str: str) -> str:
    """Convert comma-separated assets string into clickable links."""
    if not assets_str or assets_str == "—":
        return "—"
    parts = []
    for asset in assets_str.split(", "):
        asset = asset.strip()
        url = ASSET_LINKS.get(asset)
        if url:
            parts.append(f'<a href="{url}" target="_blank" style="color:var(--a2);text-decoration:none;border-bottom:1px dotted var(--a2)" title="Open {asset} on trading platform">{asset}</a>')
        else:
            parts.append(f'<span style="color:var(--m2)">{asset}</span>')
    return ", ".join(parts)


@app.get("/", response_class=HTMLResponse)
def dashboard(market: str = "All"):
    stats = get_stats()
    signals = get_signals(limit=100, market=market if market != "All" else None)
    entries = get_active_entries()
    today = datetime.now().strftime("%A, %B %d")

    signal_rows = ""
    for s in signals:
        label = s.get("sentiment_label", "NEUTRAL")
        score = s.get("sentiment_score", 0)
        color = LABEL_COLOR.get(label, "#8080a8")
        emoji = LABEL_EMOJI.get(label, "➡️")
        mkt = s.get("market", "Global")
        flag = MARKET_FLAG.get(mkt, "🌍")
        rec = s.get("recommendation", "HOLD") or "HOLD"
        risk = s.get("risk_level", "MEDIUM") or "MEDIUM"
        rec_color = REC_COLOR.get(rec, "#f59e0b")
        risk_color = RISK_COLOR.get(risk, "#f59e0b")
        finbert = s.get("finbert_label", "—")
        assets = _asset_links_html(s.get("assets", "—"))
        advice = (s.get("advice_summary") or "")[:120]
        stop_loss = s.get("stop_loss", "") or ""
        allocation = s.get("allocation", "") or ""
        alerted = "🔔" if s.get("alerted") else ""
        headline = (s.get("headline") or "")[:80]
        source = s.get("source", "")
        url = s.get("url", "#")
        analyzed = (s.get("analyzed_at") or "")[:16]
        tooltip = f"💡 {advice} | 🛡 Stop: {stop_loss} | 💼 {allocation}".replace('"', "'")
        signal_rows += f"""
        <tr title="{tooltip}">
          <td><span style="font-size:13px">{flag}</span> <a href="{url}" target="_blank" style="color:var(--text);text-decoration:none">{headline}{'...' if len(s.get('headline',''))>80 else ''}</a></td>
          <td style="color:{color};font-weight:700;white-space:nowrap">{emoji} {label}</td>
          <td style="color:{color};text-align:center">{score:+.2f}</td>
          <td style="color:{rec_color};font-weight:700;text-align:center">{rec}</td>
          <td style="color:{risk_color};text-align:center;font-size:11px">{risk}</td>
          <td style="color:var(--m2);font-size:11px">{finbert.upper()}</td>
          <td style="font-size:11px;max-width:200px">{assets}</td>
          <td style="color:var(--m2);font-size:11px">{source}</td>
          <td style="color:var(--m);font-size:11px;white-space:nowrap">{analyzed}</td>
          <td style="text-align:center">{alerted}</td>
        </tr>"""

    total = stats.get("total", 0)
    bullish = stats.get("bullish", 0)
    bearish = stats.get("bearish", 0)
    alerts = stats.get("alerts_sent", 0)
    buys = stats.get("buys", 0)
    sells = stats.get("sells", 0)
    bull_pct = round(bullish / total * 100) if total else 0
    bear_pct = round(bearish / total * 100) if total else 0

    # Active positions section
    position_rows = ""
    for e in entries:
        ticker = e.get("ticker", "")
        asset = e.get("asset_name", ticker)
        entry_p = e.get("entry_price", 0)
        entry_d = (e.get("entry_date") or "")[:16]
        headline = (e.get("signal_headline") or "")[:60]
        p5 = "✅" if e.get("profit_alerted_5") else "—"
        p10 = "✅" if e.get("profit_alerted_10") else "—"
        stop = "🛡" if e.get("stop_alerted") else "—"
        ticker_url = TICKER_LINKS.get(ticker, f"https://finance.yahoo.com/quote/{ticker}/")
        position_rows += f"""
        <tr>
          <td style="font-weight:600">{asset}</td>
          <td><a href="{ticker_url}" target="_blank" style="text-decoration:none"><code style="font-size:11px;color:var(--a2);border-bottom:1px dotted var(--a2)">{ticker}</code></a></td>
          <td style="color:var(--green)">${entry_p:,.4f}</td>
          <td style="color:var(--m);font-size:11px">{entry_d}</td>
          <td style="color:var(--m2);font-size:11px">{headline}{'...' if len(e.get('signal_headline',''))>60 else ''}</td>
          <td style="text-align:center">{p5}</td>
          <td style="text-align:center">{p10}</td>
          <td style="text-align:center">{stop}</td>
        </tr>"""

    tabs = ""
    for tab_market in ["All", "UAE/MENA", "Morocco", "Global"]:
        flag = MARKET_FLAG.get(tab_market, "🌐")
        active = "border-bottom:2px solid var(--a);color:var(--text)" if market == tab_market else "color:var(--m2)"
        tabs += f'<a href="/?market={tab_market}" style="padding:8px 16px;text-decoration:none;font-size:13px;font-weight:600;{active}">{flag if tab_market != "All" else "🌐"} {tab_market}</a>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Financial Intelligence Agent</title>
  <style>
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
    :root{{--bg:#07070f;--s:#0e0e1c;--s2:#141428;--b:#1a1a30;--b2:#242445;--a:#f59e0b;--a2:#fbbf24;--green:#10b981;--red:#ef4444;--text:#f0f0ff;--m:#55557a;--m2:#8080a8;--r:12px}}
    body{{font-family:-apple-system,BlinkMacSystemFont,'Inter',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;font-size:14px}}
    header{{border-bottom:1px solid var(--b);padding:0 40px;height:64px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;background:rgba(7,7,15,.96);backdrop-filter:blur(16px);z-index:100}}
    .logo{{display:flex;align-items:center;gap:10px;font-weight:700;font-size:16px;text-decoration:none;color:var(--text)}}
    .logo-dot{{width:10px;height:10px;border-radius:50%;background:var(--green);box-shadow:0 0 12px var(--green)}}
    .nav a{{color:var(--m2);text-decoration:none;font-size:13px;margin-left:24px}}
    main{{max-width:1500px;margin:0 auto;padding:32px 40px 80px}}
    h1{{font-size:26px;font-weight:700;margin-bottom:4px}}
    .sub{{color:var(--m2);font-size:13px;margin-bottom:28px}}
    .metrics{{display:grid;grid-template-columns:repeat(6,1fr);gap:12px;margin-bottom:28px}}
    .m-card{{background:var(--s);border:1px solid var(--b);border-radius:var(--r);padding:18px 20px}}
    .m-val{{font-size:28px;font-weight:700}}
    .m-lbl{{font-size:11px;color:var(--m);text-transform:uppercase;letter-spacing:.5px;margin-top:4px}}
    .section-label{{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;color:var(--m);margin-bottom:14px}}
    .tabs{{display:flex;border-bottom:1px solid var(--b);margin-bottom:16px}}
    .table-wrap{{background:var(--s);border:1px solid var(--b);border-radius:var(--r);overflow:hidden}}
    table{{width:100%;border-collapse:collapse}}
    th{{padding:11px 14px;text-align:left;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--m);border-bottom:1px solid var(--b);background:var(--s2)}}
    td{{padding:10px 14px;border-bottom:1px solid rgba(255,255,255,.04);font-size:13px;vertical-align:middle}}
    tr:hover td{{background:rgba(255,255,255,.02)}}
    tr:last-child td{{border-bottom:none}}
    .scan-btn{{background:var(--a);color:#07070f;border:none;border-radius:8px;padding:10px 20px;font-size:13px;font-weight:700;cursor:pointer;transition:opacity .15s}}
    .scan-btn:hover{{opacity:.85}}
    .scan-btn:disabled{{opacity:.4}}
    .spinner{{display:inline-block;width:12px;height:12px;border:2px solid rgba(7,7,15,.3);border-top-color:#07070f;border-radius:50%;animation:spin .7s linear infinite;vertical-align:middle;margin-right:5px}}
    @keyframes spin{{to{{transform:rotate(360deg)}}}}
    .gauge{{display:flex;gap:8px;align-items:center;margin-top:6px}}
    .gauge-bar{{height:6px;border-radius:3px;flex:1}}
    @media(max-width:900px){{main{{padding:20px}}.metrics{{grid-template-columns:repeat(3,1fr)}}}}
  </style>
</head>
<body>
<header>
  <a class="logo" href="/"><span class="logo-dot"></span>Financial Intelligence</a>
  <nav class="nav">
    <a href="/signals">Signals API</a>
    <a href="/docs">API</a>
    <button class="scan-btn" id="scanBtn" onclick="triggerScan()">⚡ Run Scan Now</button>
  </nav>
</header>
<main>
  <div style="margin-bottom:8px;color:var(--m2);font-size:13px">{today}</div>
  <h1>🌍 Global Financial Intelligence</h1>
  <p class="sub">FinBERT + Claude analysis across 🇦🇪 UAE/MENA · 🇲🇦 Morocco · 🌍 Global markets. BUY/HOLD/SELL signals + risk + stop-loss. Alerts on Telegram.</p>

  <div class="metrics">
    <div class="m-card">
      <div class="m-val">{total}</div>
      <div class="m-lbl">Total Signals</div>
    </div>
    <div class="m-card">
      <div class="m-val" style="color:var(--green)">{bullish}</div>
      <div class="m-lbl">Bullish</div>
      <div class="gauge"><div class="gauge-bar" style="background:var(--green);width:{bull_pct}%"></div><span style="font-size:11px;color:var(--m)">{bull_pct}%</span></div>
    </div>
    <div class="m-card">
      <div class="m-val" style="color:var(--red)">{bearish}</div>
      <div class="m-lbl">Bearish</div>
      <div class="gauge"><div class="gauge-bar" style="background:var(--red);width:{bear_pct}%"></div><span style="font-size:11px;color:var(--m)">{bear_pct}%</span></div>
    </div>
    <div class="m-card">
      <div class="m-val" style="color:#10b981">{buys}</div>
      <div class="m-lbl">BUY Signals</div>
    </div>
    <div class="m-card">
      <div class="m-val" style="color:#ef4444">{sells}</div>
      <div class="m-lbl">SELL Signals</div>
    </div>
    <div class="m-card">
      <div class="m-val" style="color:var(--a2)">{alerts}</div>
      <div class="m-lbl">Telegram Alerts</div>
    </div>
  </div>

  <div class="section-label">Active BUY Positions — Profit Tracking</div>
  {f'''<div class="table-wrap" style="margin-bottom:28px">
    <table>
      <thead>
        <tr>
          <th>Asset</th><th>Ticker</th><th>Entry Price</th><th>Recorded</th>
          <th>Signal</th><th>+5%</th><th>+10%</th><th>Stop</th>
        </tr>
      </thead>
      <tbody>{position_rows}</tbody>
    </table>
  </div>''' if position_rows else f'<div style="background:var(--s);border:1px solid var(--b);border-radius:var(--r);padding:24px;color:var(--m);font-size:13px;margin-bottom:28px">No active BUY positions yet — positions are recorded automatically when the agent fires a high-confidence BUY signal.</div>'}

  <div class="section-label">Market Signals</div>
  <div class="tabs">{tabs}</div>
  <div style="color:var(--m);font-size:11px;margin-bottom:10px">Hover over a row to see investment advice, stop-loss, and allocation details.</div>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Headline</th>
          <th>Signal</th>
          <th>Score</th>
          <th>Action</th>
          <th>Risk</th>
          <th>FinBERT</th>
          <th>Assets</th>
          <th>Source</th>
          <th>Analyzed</th>
          <th>🔔</th>
        </tr>
      </thead>
      <tbody id="signalBody">
        {signal_rows if signal_rows else '<tr><td colspan="10" style="text-align:center;color:var(--m);padding:40px">No signals yet — click Run Scan Now</td></tr>'}
      </tbody>
    </table>
  </div>
</main>

<script>
async function triggerScan() {{
  const btn = document.getElementById('scanBtn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>Scanning UAE/MENA + Morocco + Global...';
  try {{
    const r = await fetch('/scan/run', {{method:'POST'}});
    const d = await r.json();
    btn.innerHTML = '✅ Scan started — check Telegram';
    setTimeout(()=>{{btn.innerHTML='⚡ Run Scan Now';btn.disabled=false;location.reload();}}, 5000);
  }} catch(e) {{
    btn.innerHTML = '❌ Error';
    setTimeout(()=>{{btn.innerHTML='⚡ Run Scan Now';btn.disabled=false;}}, 3000);
  }}
}}
</script>
</body>
</html>"""


@app.post("/scan/run")
def trigger_scan():
    """Manually trigger a multi-market intelligence scan."""
    from scheduler import run_market_scan
    threading.Thread(target=run_market_scan, daemon=True).start()
    return {"status": "started", "message": "Scanning UAE/MENA + Morocco + Global — check Telegram for alerts"}


@app.post("/price/check")
def manual_price_check():
    """Manually trigger volume spike + profit check."""
    import threading
    from scheduler import run_price_checks
    threading.Thread(target=run_price_checks, daemon=True).start()
    return {"status": "started", "message": "Price check running — check Telegram"}


@app.get("/positions")
def positions_api():
    return get_active_entries()


@app.get("/signals")
def get_signals_api(limit: int = 100, market: str = None):
    return get_signals(limit=limit, market=market)


@app.get("/stats")
def stats():
    return get_stats()


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web:app", host="0.0.0.0", port=PORT, reload=False)
