import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional
import pytz

from strategies import (
    candlestick_patterns,
    trend_strategies,
    momentum_strategies,
    breakout_strategies,
    support_resistance,
    volume_strategies,
    reversal_strategies,
    options_strategies,
    market_regime,
)
from core import risk_calculator
from core.data_fetcher import fetch_historical, fetch_option_chain, fetch_quotes

IST = pytz.timezone('Asia/Kolkata')

STRATEGY_NAMES = [
    'candlestick', 'trend', 'momentum', 'breakout',
    'support_resistance', 'volume', 'reversal', 'options'
]

# Base weights — multiplied by regime weights at runtime
_BASE_WEIGHTS = {
    'candlestick':        1.0,
    'trend':              1.2,
    'momentum':           1.1,
    'breakout':           1.1,
    'support_resistance': 1.0,
    'volume':             1.0,
    'reversal':           0.9,
    'options':            0.8,
}


def _is_market_hours() -> bool:
    now = datetime.now(IST)
    if now.weekday() >= 5:
        return False
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    cutoff      = now.replace(hour=15, minute=20, second=0, microsecond=0)
    return market_open <= now <= cutoff


def _get_confidence(score: float) -> str:
    if score >= 6.5:
        return 'HIGH'
    elif score >= 4.5:
        return 'MEDIUM'
    return 'LOW'


def _get_mtf_alignment(primary_signal: str, htf_signal: str, ltf_signal: str) -> str:
    signals    = [primary_signal, htf_signal, ltf_signal]
    buy_count  = signals.count('BUY')
    sell_count = signals.count('SELL')
    if buy_count == 3:
        return 'ALL_BULLISH'
    elif sell_count == 3:
        return 'ALL_BEARISH'
    elif buy_count == 2 and primary_signal == 'BUY':
        return 'MOSTLY_BULLISH'
    elif sell_count == 2 and primary_signal == 'SELL':
        return 'MOSTLY_BEARISH'
    elif buy_count >= 1 and sell_count >= 1:
        return 'MIXED'
    return 'NEUTRAL'


def _weighted_votes(results: dict, regime_weights: dict) -> tuple:
    """
    Returns (primary_signal, weighted_score, raw_buy_votes, raw_sell_votes).
    weighted_score is the sum of weights for the winning side — not a simple count.
    """
    buy_score  = 0.0
    sell_score = 0.0
    raw_buy    = 0
    raw_sell   = 0

    for name in STRATEGY_NAMES:
        r      = results.get(name, {})
        sig    = r.get('signal', 'NEUTRAL')
        base_w = _BASE_WEIGHTS.get(name, 1.0)
        reg_w  = regime_weights.get(name, 1.0)
        weight = base_w * reg_w

        if sig == 'BUY':
            buy_score += weight
            raw_buy   += 1
        elif sig == 'SELL':
            sell_score += weight
            raw_sell   += 1

    if buy_score > sell_score:
        return 'BUY', buy_score, raw_buy, raw_sell
    elif sell_score > buy_score:
        return 'SELL', sell_score, raw_sell, raw_buy
    return 'NEUTRAL', 0.0, raw_buy, raw_sell


def run(
    symbol: str,
    fyers=None,
    account_balance: float = 500000,
    max_risk_pct: float = 0.01,
    max_capital_pct: float = 0.20,
    min_strategies: int = 6,
    min_strategies_volatile: int = 7,
    min_rr: float = 2.0,
    min_vol_ratio: float = 1.2,
    active_trades: list = None,
    today_pnl: float = 0,
    max_daily_loss: float = 0.03,
    force: bool = False,
    verbose: bool = False,
) -> Optional[dict]:

    if active_trades is None:
        active_trades = []

    def _reject(reason: str):
        if verbose:
            print(f"[Engine] {symbol} BLOCKED - {reason}")
        return None

    # Gate 4: Market hours check
    if not force and not _is_market_hours():
        return _reject("outside market hours")

    # Fetch primary timeframe (15-min) data
    df_15 = fetch_historical(symbol, '15', fyers=fyers)
    if df_15 is None or len(df_15) < 50:
        rows = len(df_15) if df_15 is not None else 0
        return _reject(f"insufficient 15m data (rows={rows})")

    # Fetch higher timeframe (60-min) for trend filter
    df_60 = fetch_historical(symbol, '60', fyers=fyers)

    # Fetch lower timeframe (5-min) for entry timing
    df_5 = fetch_historical(symbol, '5', fyers=fyers)

    # Get live price
    quotes      = fetch_quotes([symbol], fyers=fyers)
    entry_price = quotes.get(symbol, {}).get('ltp', 0)
    if entry_price == 0:
        entry_price = float(df_15['close'].iloc[-1])

    # Fetch options data for indices
    options_data = None
    is_index     = any(kw in symbol.upper() for kw in ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'SENSEX'])
    if is_index:
        options_data = fetch_option_chain(symbol, fyers=fyers)

    # ── Market Regime Detection ────────────────────────────────────────────────
    regime_data    = market_regime.detect(df_15)
    regime         = regime_data.get('regime', 'UNKNOWN')
    regime_weights = regime_data.get('weights', {k: 1.0 for k in STRATEGY_NAMES})

    # Gate T: Time-of-day filter — skip opening noise and EOD chop
    if not force:
        now_ist = datetime.now(IST)
        _h, _m = now_ist.hour, now_ist.minute
        in_opening_noise = (_h == 9 and _m < 30)
        in_eod_chop      = (_h == 15 and _m >= 0)
        if in_opening_noise:
            return _reject("GateT opening noise window (9:15–9:30) — skip")
        if in_eod_chop:
            return _reject("GateT EOD window (15:00–15:30) — skip")

    # Gate R: Regime filter — only trade TRENDING markets
    # RANGING (ADX<25): no trend momentum → high false-signal rate
    # VOLATILE (hist_vol>2.5%): erratic moves → stops get hunted
    if regime == 'RANGING':
        return _reject(
            f"GateR RANGING market (ADX={regime_data.get('adx', 0):.1f}) — no directional edge"
        )
    if regime == 'VOLATILE':
        return _reject(
            f"GateR VOLATILE market (hist_vol={regime_data.get('hist_vol', 0):.2f}%) — stops get hunted"
        )

    # ── Run all 8 strategies (per-strategy exception isolation) ───────────────
    results = {}
    _strategy_calls = [
        ('candlestick',        lambda: candlestick_patterns.analyze(df_15)),
        ('trend',              lambda: trend_strategies.analyze(df_15)),
        ('momentum',           lambda: momentum_strategies.analyze(df_15)),
        ('breakout',           lambda: breakout_strategies.analyze(df_15)),
        ('support_resistance', lambda: support_resistance.analyze(df_15, options_data)),
        ('volume',             lambda: volume_strategies.analyze(df_15)),
        ('reversal',           lambda: reversal_strategies.analyze(df_15)),
        ('options',            lambda: options_strategies.analyze(df_15, symbol, options_data)),
    ]
    for _name, _fn in _strategy_calls:
        try:
            results[_name] = _fn()
        except Exception as _se:
            print(f"[Engine] {symbol} strategy '{_name}' error: {_se}")
            results[_name] = {'signal': 'NEUTRAL', 'strength': 0, 'confirmations': []}

    # ── Weighted voting ────────────────────────────────────────────────────────
    primary_signal, weighted_score, raw_votes, _ = _weighted_votes(results, regime_weights)

    if verbose:
        print(f"[Engine] {symbol} votes: {primary_signal} raw={raw_votes} score={weighted_score:.2f}")

    if primary_signal == 'NEUTRAL':
        return _reject(f"no majority signal (raw_buy={raw_votes})")

    # Gate 1: Minimum raw strategy confirmations — higher bar in VOLATILE regime
    required_votes = min_strategies_volatile if regime == 'VOLATILE' else min_strategies
    if raw_votes < required_votes:
        return _reject(
            f"Gate1 votes {raw_votes}/{len(STRATEGY_NAMES)} < {required_votes} required"
            f" (regime={regime})"
        )

    # Gate 2: Volume gate — need above-average participation to confirm move
    vol_ratio = results['volume'].get('vol_ratio', 1.0)
    if vol_ratio < min_vol_ratio:
        return _reject(f"Gate2 vol_ratio={vol_ratio:.2f} < {min_vol_ratio:.2f} (thin volume)")

    # Higher timeframe analysis
    htf_signal = 'NEUTRAL'
    if df_60 is not None and len(df_60) >= 50:
        htf_trend  = trend_strategies.analyze(df_60)
        htf_signal = htf_trend.get('signal', 'NEUTRAL')

    ltf_signal = 'NEUTRAL'
    if df_5 is not None and len(df_5) >= 50:
        ltf_trend  = trend_strategies.analyze(df_5)
        ltf_signal = ltf_trend.get('signal', 'NEUTRAL')

    # Gate 3: Higher timeframe filter — hard conflict AND mixed alignment blocked
    if htf_signal != 'NEUTRAL' and htf_signal != primary_signal:
        return _reject(f"Gate3 HTF conflict: 15m={primary_signal} 60m={htf_signal}")

    mtf_alignment = _get_mtf_alignment(primary_signal, htf_signal, ltf_signal)
    if mtf_alignment == 'MIXED':
        return _reject("Gate3 MTF MIXED — signals disagree across timeframes, no clear direction")
    mtf_bonus     = 1.5 if 'ALL_' in mtf_alignment else 0.0

    # Gate 5: No duplicate active trade for same symbol
    for active in active_trades:
        if active.get('symbol') == symbol and active.get('status') == 'ACTIVE':
            return _reject("Gate5 duplicate active trade")

    # Gate 5b: Correlation guard
    try:
        from core.correlation_guard import is_allowed
        corr_ok, corr_reason = is_allowed(symbol, active_trades)
        if not corr_ok:
            print(f"[Engine] {symbol} blocked by correlation guard: {corr_reason}")
            return None
    except Exception:
        pass

    # Gate 6: Daily loss limit
    if today_pnl < -(account_balance * max_daily_loss):
        return _reject(f"Gate6 daily loss limit hit (today_pnl={today_pnl:.0f})")

    # ── Risk calculation ───────────────────────────────────────────────────────
    sr_levels = []
    if results['support_resistance'].get('levels'):
        horizontal = results['support_resistance']['levels'].get('horizontal_sr', [])
        sr_levels  = [l['price'] for l in horizontal]

    risk_data = risk_calculator.calculate(
        df=df_15,
        signal_type=primary_signal,
        entry_price=entry_price,
        support_levels=sr_levels,
        account_balance=account_balance,
        max_risk_pct=max_risk_pct,
        max_capital_pct=max_capital_pct,
    )
    if not risk_data:
        return _reject("Gate7 risk calculation failed (insufficient ATR data?)")

    # Gate 8: Risk-reward check
    rr = risk_data.get('riskReward', 0)
    if rr < min_rr:
        return _reject(f"Gate8 R:R={rr:.2f} < {min_rr}")

    # Volatile regime → require slightly higher R:R
    if regime == 'VOLATILE' and rr < min_rr * 1.2:
        return _reject(f"Gate8 R:R={rr:.2f} < {min_rr*1.2:.2f} (VOLATILE regime)")

    # Gate 9: Confidence gate — require HIGH confidence only (score ≥ 6.5)
    pre_confidence = _get_confidence(weighted_score)
    if pre_confidence != 'HIGH':
        return _reject(f"Gate9 confidence={pre_confidence} (score={weighted_score:.2f}) — require HIGH (≥6.5)")

    # ── Build signal dict ──────────────────────────────────────────────────────
    display_symbol = symbol
    if ':' in display_symbol:
        display_symbol = display_symbol.split(':')[1]
    display_symbol = display_symbol.replace('-EQ', '').replace('-INDEX', '')

    now_ist        = datetime.now(IST)
    final_score    = weighted_score + mtf_bonus
    confidence     = _get_confidence(final_score)

    strategy_vote_summary = {}
    for name in STRATEGY_NAMES:
        r = results.get(name, {})
        strategy_vote_summary[name] = {
            'signal':        r.get('signal', 'NEUTRAL'),
            'strength':      r.get('strength', 0),
            'confirmations': r.get('confirmations', [])[:3],
            'weight':        round(_BASE_WEIGHTS.get(name, 1.0) * regime_weights.get(name, 1.0), 2),
        }

    signal = {
        'symbol':                  symbol,
        'displaySymbol':           display_symbol,
        'type':                    primary_signal,
        'confidence':              confidence,
        'votes':                   f'{raw_votes}/8',
        'votesCount':              raw_votes,
        'weightedScore':           round(final_score, 2),
        'multiTimeframeAlignment': mtf_alignment,
        'marketRegime':            regime,
        'regimeData':              {
            'adx':            regime_data.get('adx', 0),
            'volatility_pct': regime_data.get('volatility_pct', 0),
        },
        'entryPrice':         risk_data['entryPrice'],
        'stopLoss':           risk_data['stopLoss'],
        'stopLossPercent':    risk_data['stopLossPercent'],
        'target1':            risk_data['target1'],
        'target2':            risk_data['target2'],
        'target3':            risk_data['target3'],
        'target4':            risk_data['target4'],
        'target5':            risk_data['target5'],
        'target1Pct':         risk_data['target1Pct'],
        'target2Pct':         risk_data['target2Pct'],
        'target3Pct':         risk_data['target3Pct'],
        'positionSize':       risk_data['positionSize'],
        'capitalRequired':    risk_data['capitalRequired'],
        'maxLoss':            risk_data['maxLoss'],
        'riskReward':         risk_data['riskReward'],
        'atr':                risk_data['atr'],
        'strategies':         strategy_vote_summary,
        'optionsData':        options_data,
        'volRatio':           vol_ratio,
        'signalTime':         now_ist.isoformat(),
        'date':               now_ist.strftime('%Y-%m-%d'),
    }

    # ── News Sentiment Filter (non-blocking on error) ──────────────────────────
    try:
        import os as _os
        if _os.getenv('NEWSDATA_API_KEY'):
            from core.news_filter import analyze as news_analyze
            news = news_analyze(symbol)
            signal['newsSentiment'] = news
            if news.get('blocked'):
                print(f"[Engine] {symbol} blocked by news filter: {news.get('reason')}")
                return None
    except Exception:
        pass

    # ── ML Signal Filter (non-blocking when model not trained) ────────────────
    try:
        from core.ml_filter import predict as ml_predict
        ml_result = ml_predict(signal)
        signal['mlFilter'] = ml_result
        if not ml_result.get('allowed', True):
            print(f"[Engine] {symbol} blocked by ML filter: {ml_result.get('reason')}")
            return None
    except Exception:
        pass

    return signal
