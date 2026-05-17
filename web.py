"""UAE Financial Intelligence Agent — FastAPI dashboard."""

import threading
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from config import PORT
from database import init_db, get_signals, get_stats

app = FastAPI(title="UAE Financial Intelligence Agent", version="1.0.0")
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


@app.get("/", response_class=HTMLResponse)
def dashboard():
    stats = get_stats()
    signals = get_signals(limit=50)
    today = datetime.now().strftime("%A, %B %d")

    signal_rows = ""
    for s in signals:
        label = s.get("sentiment_label", "NEUTRAL")
        score = s.get("sentiment_score", 0)
        color = LABEL_COLOR.get(label, "#8080a8")
        emoji = LABEL_EMOJI.get(label, "➡️")
        finbert = s.get("finbert_label", "—")
        assets = s.get("assets", "—")
        alerted = "🔔" if s.get("alerted") else ""
        headline = (s.get("headline") or "")[:90]
        source = s.get("source", "")
        url = s.get("url", "#")
        analyzed = (s.get("analyzed_at") or "")[:16]
        signal_rows += f"""
        <tr>
          <td><a href="{url}" target="_blank" style="color:var(--text);text-decoration:none">{headline}{'...' if len(s.get('headline',''))>90 else ''}</a></td>
          <td style="color:{color};font-weight:700;white-space:nowrap">{emoji} {label}</td>
          <td style="color:{color};text-align:center">{score:+.2f}</td>
          <td style="color:var(--m2);font-size:11px">{finbert.upper()}</td>
          <td style="color:var(--m2);font-size:11px">{assets}</td>
          <td style="color:var(--m2);font-size:11px">{source}</td>
          <td style="color:var(--m);font-size:11px;white-space:nowrap">{analyzed}</td>
          <td style="text-align:center">{alerted}</td>
        </tr>"""

    total = stats.get("total", 0)
    bullish = stats.get("bullish", 0)
    bearish = stats.get("bearish", 0)
    alerts = stats.get("alerts_sent", 0)
    bull_pct = round(bullish / total * 100) if total else 0
    bear_pct = round(bearish / total * 100) if total else 0

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>UAE Financial Intelligence Agent</title>
  <style>
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
    :root{{--bg:#07070f;--s:#0e0e1c;--s2:#141428;--b:#1a1a30;--b2:#242445;--a:#f59e0b;--a2:#fbbf24;--green:#10b981;--red:#ef4444;--text:#f0f0ff;--m:#55557a;--m2:#8080a8;--r:12px}}
    body{{font-family:-apple-system,BlinkMacSystemFont,'Inter',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;font-size:14px}}
    header{{border-bottom:1px solid var(--b);padding:0 40px;height:64px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;background:rgba(7,7,15,.96);backdrop-filter:blur(16px);z-index:100}}
    .logo{{display:flex;align-items:center;gap:10px;font-weight:700;font-size:16px;text-decoration:none;color:var(--text)}}
    .logo-dot{{width:10px;height:10px;border-radius:50%;background:var(--green);box-shadow:0 0 12px var(--green)}}
    .nav a{{color:var(--m2);text-decoration:none;font-size:13px;margin-left:24px}}
    main{{max-width:1400px;margin:0 auto;padding:32px 40px 80px}}
    h1{{font-size:26px;font-weight:700;margin-bottom:4px}}
    .sub{{color:var(--m2);font-size:13px;margin-bottom:28px}}
    .metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:28px}}
    .m-card{{background:var(--s);border:1px solid var(--b);border-radius:var(--r);padding:18px 20px}}
    .m-val{{font-size:28px;font-weight:700}}
    .m-lbl{{font-size:11px;color:var(--m);text-transform:uppercase;letter-spacing:.5px;margin-top:4px}}
    .section-label{{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;color:var(--m);margin-bottom:14px}}
    .table-wrap{{background:var(--s);border:1px solid var(--b);border-radius:var(--r);overflow:hidden}}
    table{{width:100%;border-collapse:collapse}}
    th{{padding:11px 14px;text-align:left;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--m);border-bottom:1px solid var(--b);background:var(--s2)}}
    td{{padding:12px 14px;border-bottom:1px solid rgba(255,255,255,.04);font-size:13px;vertical-align:middle}}
    tr:hover td{{background:rgba(255,255,255,.02)}}
    tr:last-child td{{border-bottom:none}}
    .scan-btn{{background:var(--a);color:#07070f;border:none;border-radius:8px;padding:10px 20px;font-size:13px;font-weight:700;cursor:pointer;transition:opacity .15s}}
    .scan-btn:hover{{opacity:.85}}
    .scan-btn:disabled{{opacity:.4}}
    .spinner{{display:inline-block;width:12px;height:12px;border:2px solid rgba(7,7,15,.3);border-top-color:#07070f;border-radius:50%;animation:spin .7s linear infinite;vertical-align:middle;margin-right:5px}}
    @keyframes spin{{to{{transform:rotate(360deg)}}}}
    .gauge{{display:flex;gap:8px;align-items:center;margin-top:6px}}
    .gauge-bar{{height:6px;border-radius:3px;flex:1}}
    @media(max-width:900px){{main{{padding:20px}}.metrics{{grid-template-columns:repeat(2,1fr)}}}}
  </style>
</head>
<body>
<header>
  <a class="logo" href="/"><span class="logo-dot"></span>UAE Financial Intelligence</a>
  <nav class="nav">
    <a href="/signals">Signals API</a>
    <a href="/docs">API</a>
    <button class="scan-btn" id="scanBtn" onclick="triggerScan()">⚡ Run Scan Now</button>
  </nav>
</header>
<main>
  <div style="margin-bottom:8px;color:var(--m2);font-size:13px">{today}</div>
  <h1>🇦🇪 UAE Market Intelligence</h1>
  <p class="sub">FinBERT + Claude sentiment analysis on UAE/MENA financial news. Alerts on Telegram.</p>

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
      <div class="m-val" style="color:var(--a2)">{alerts}</div>
      <div class="m-lbl">Telegram Alerts</div>
    </div>
  </div>

  <div class="section-label">Latest Market Signals</div>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Headline</th>
          <th>Signal</th>
          <th>Score</th>
          <th>FinBERT</th>
          <th>Assets</th>
          <th>Source</th>
          <th>Analyzed</th>
          <th>🔔</th>
        </tr>
      </thead>
      <tbody id="signalBody">
        {signal_rows if signal_rows else '<tr><td colspan="8" style="text-align:center;color:var(--m);padding:40px">No signals yet — click Run Scan Now</td></tr>'}
      </tbody>
    </table>
  </div>
</main>

<script>
async function triggerScan() {{
  const btn = document.getElementById('scanBtn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>Scanning...';
  try {{
    const r = await fetch('/scan/run', {{method:'POST'}});
    const d = await r.json();
    btn.innerHTML = '✅ Scan started — check Telegram';
    setTimeout(()=>{{btn.innerHTML='⚡ Run Scan Now';btn.disabled=false;location.reload();}}, 4000);
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
    """Manually trigger a market intelligence scan."""
    from scheduler import run_market_scan
    threading.Thread(target=run_market_scan, daemon=True).start()
    return {"status": "started", "message": "Scan running — check Telegram for alerts"}


@app.get("/signals")
def get_signals_api(limit: int = 100):
    return get_signals(limit=limit)


@app.get("/stats")
def stats():
    return get_stats()


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web:app", host="0.0.0.0", port=PORT, reload=False)
