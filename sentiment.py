"""
Two-layer sentiment analysis:
  Layer 1 — FinBERT (HuggingFace ProsusAI/finbert): fast financial sentiment score
  Layer 2 — Claude: UAE market context, affected assets, alert-worthy reasoning
"""

import json
import logging
import re
import requests
from config import (ANTHROPIC_API_KEY, GROQ_API_KEY, HF_API_KEY,
                    FINBERT_URL, CLAUDE_MODEL, GROQ_MODEL, ALERT_THRESHOLD)

logger = logging.getLogger(__name__)


def _finbert_score(text: str) -> dict:
    """Call FinBERT via HuggingFace Inference API. Returns label + score."""
    if not HF_API_KEY:
        return {"label": "neutral", "score": 0.0}
    try:
        headers = {"Authorization": f"Bearer {HF_API_KEY}"}
        r = requests.post(FINBERT_URL, headers=headers,
                          json={"inputs": text[:512]}, timeout=15)
        r.raise_for_status()
        data = r.json()
        # HF returns [[{label, score}, ...]] — pick highest score
        candidates = data[0] if isinstance(data[0], list) else data
        best = max(candidates, key=lambda x: x["score"])
        return {"label": best["label"].lower(), "score": round(best["score"], 4)}
    except Exception as e:
        logger.warning(f"FinBERT API error: {e}")
        return {"label": "neutral", "score": 0.0}


def _claude_analyze(headline: str, body: str) -> dict:
    """Deep Claude analysis for UAE market context."""
    system = (
        "You are a financial intelligence analyst specializing in UAE/MENA markets. "
        "Given a news headline and body, return ONLY valid JSON with this structure:\n"
        '{"sentiment_score": <float -1.0 to 1.0>, '
        '"sentiment_label": "<STRONG_BULLISH|BULLISH|NEUTRAL|BEARISH|STRONG_BEARISH>", '
        '"confidence": <float 0.0 to 1.0>, '
        '"assets": ["<DFM|ADX|TASI|AED|Oil|Gold|UAE Real Estate|UAE Banking|...>"], '
        '"reasoning": "<2-3 sentence analysis focused on UAE/MENA market impact>"}\n\n'
        "Score guide: +0.8/+1.0=major bullish, +0.4/+0.7=bullish, -0.2/+0.2=neutral, "
        "-0.4/-0.7=bearish, -0.8/-1.0=major bearish."
    )
    prompt = f"Headline: {headline}\n\nBody: {body[:800]}"
    result = _llm_call(system, prompt)
    try:
        return json.loads(result.strip())
    except Exception:
        match = re.search(r'\{[\s\S]*\}', result)
        if match:
            return json.loads(match.group())
        return {
            "sentiment_score": 0.0,
            "sentiment_label": "NEUTRAL",
            "confidence": 0.5,
            "assets": [],
            "reasoning": result[:200]
        }


def _llm_call(system: str, prompt: str) -> str:
    if ANTHROPIC_API_KEY:
        try:
            import anthropic
            r = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY).messages.create(
                model=CLAUDE_MODEL, max_tokens=512, system=system,
                messages=[{"role": "user", "content": prompt}]
            )
            return r.content[0].text
        except Exception as e:
            if "credit" not in str(e).lower():
                raise
    if GROQ_API_KEY:
        from openai import OpenAI
        client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)
        r = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            max_tokens=512, temperature=0.1
        )
        return r.choices[0].message.content
    raise RuntimeError("No API key configured.")


def analyze_article(headline: str, body: str) -> dict:
    """
    Full two-layer analysis.
    Returns combined result with finbert + claude data.
    """
    # Layer 1: FinBERT (fast)
    finbert = _finbert_score(headline + " " + body[:200])

    # Layer 2: Claude (deep)
    claude = _claude_analyze(headline, body)

    # Map FinBERT label to numeric for blending
    fb_map = {"positive": 0.6, "negative": -0.6, "neutral": 0.0}
    fb_numeric = fb_map.get(finbert["label"], 0.0) * finbert["score"]

    # Blend: 30% FinBERT + 70% Claude
    blended_score = round(0.3 * fb_numeric + 0.7 * claude.get("sentiment_score", 0.0), 3)

    # Determine final label from blended score
    if blended_score >= 0.6:
        label = "STRONG_BULLISH"
    elif blended_score >= 0.3:
        label = "BULLISH"
    elif blended_score <= -0.6:
        label = "STRONG_BEARISH"
    elif blended_score <= -0.3:
        label = "BEARISH"
    else:
        label = "NEUTRAL"

    alert_worthy = abs(blended_score) >= ALERT_THRESHOLD and claude.get("confidence", 0) >= 0.6

    return {
        "finbert_label": finbert["label"],
        "finbert_score": finbert["score"],
        "sentiment_score": blended_score,
        "sentiment_label": label,
        "confidence": claude.get("confidence", 0.5),
        "assets": claude.get("assets", []),
        "reasoning": claude.get("reasoning", ""),
        "alert_worthy": alert_worthy,
    }
