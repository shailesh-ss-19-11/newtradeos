"""
News Sentiment Filter — fetches recent news for a symbol via NewsData.io
and returns a sentiment score. Negative sentiment blocks signals.

Set NEWSDATA_API_KEY in .env to enable. If key missing, returns NEUTRAL.
Free tier: 200 requests/day.
"""

import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

_API_KEY   = os.getenv('NEWSDATA_API_KEY', '')
_BASE_URL  = 'https://newsdata.io/api/1/news'
_CACHE     = {}           # symbol → (timestamp, result)
_CACHE_TTL = 1800         # 30 minutes

# Words that indicate strong negative sentiment
_NEGATIVE_KEYWORDS = [
    'fraud', 'scam', 'investigation', 'raid', 'sebi', 'penalty', 'ban',
    'bankruptcy', 'default', 'debt', 'downgrade', 'recall', 'lawsuit',
    'arrest', 'probe', 'loss', 'decline', 'fell', 'drops', 'crash',
    'scandal', 'violation', 'regulatory', 'suspended', 'delisted',
]

_POSITIVE_KEYWORDS = [
    'profit', 'revenue', 'growth', 'beat', 'outperform', 'buyback',
    'dividend', 'upgrade', 'acquisition', 'launch', 'partnership',
    'record', 'strong', 'rises', 'jumps', 'surge', 'rally',
]


def _extract_ticker(symbol: str) -> str:
    s = symbol.upper()
    if ':' in s:
        s = s.split(':')[1]
    return s.replace('-EQ', '').replace('-INDEX', '').replace('-BE', '')


def _score_text(text: str) -> int:
    """Simple keyword-based scoring: +1 positive, -1 negative. Returns -10 to +10."""
    if not text:
        return 0
    text_lower = text.lower()
    score = 0
    for kw in _POSITIVE_KEYWORDS:
        if kw in text_lower:
            score += 1
    for kw in _NEGATIVE_KEYWORDS:
        if kw in text_lower:
            score -= 2          # Weight negative news more heavily
    return max(-10, min(10, score))


def analyze(symbol: str) -> dict:
    """
    Returns:
        sentiment: 'POSITIVE' | 'NEUTRAL' | 'NEGATIVE'
        score: int (-10 to +10)
        blocked: bool  (True = don't trade)
        articles: int
        reason: str
    """
    ticker = _extract_ticker(symbol)

    # Return neutral if no API key configured
    if not _API_KEY:
        return {'sentiment': 'NEUTRAL', 'score': 0, 'blocked': False,
                'articles': 0, 'reason': 'News API not configured'}

    # Check cache
    now = time.time()
    if ticker in _CACHE:
        ts, cached = _CACHE[ticker]
        if now - ts < _CACHE_TTL:
            return cached

    try:
        resp = requests.get(
            _BASE_URL,
            params={
                'apikey':   _API_KEY,
                'q':        ticker,
                'country':  'in',
                'language': 'en',
                'category': 'business',
                'size':     5,
            },
            timeout=8
        )
        data = resp.json()

        if data.get('status') != 'success':
            result = {'sentiment': 'NEUTRAL', 'score': 0, 'blocked': False,
                      'articles': 0, 'reason': f"API error: {data.get('message', '')}"}
            _CACHE[ticker] = (now, result)
            return result

        articles = data.get('results', [])
        total_score = 0
        for art in articles:
            combined = f"{art.get('title', '')} {art.get('description', '')}"
            total_score += _score_text(combined)

        avg_score = round(total_score / len(articles), 1) if articles else 0

        if avg_score <= -3:
            sentiment = 'NEGATIVE'
            blocked   = True
            reason    = f"Negative news detected (score {avg_score}) — {len(articles)} articles"
        elif avg_score >= 2:
            sentiment = 'POSITIVE'
            blocked   = False
            reason    = f"Positive news sentiment (score {avg_score})"
        else:
            sentiment = 'NEUTRAL'
            blocked   = False
            reason    = f"Neutral sentiment (score {avg_score})"

        result = {
            'sentiment': sentiment,
            'score':     avg_score,
            'blocked':   blocked,
            'articles':  len(articles),
            'reason':    reason,
        }
        _CACHE[ticker] = (now, result)
        return result

    except Exception as e:
        result = {'sentiment': 'NEUTRAL', 'score': 0, 'blocked': False,
                  'articles': 0, 'reason': f'News fetch failed: {str(e)[:60]}'}
        _CACHE[ticker] = (now, result)
        return result
