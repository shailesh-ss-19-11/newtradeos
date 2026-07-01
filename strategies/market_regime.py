import pandas as pd
import numpy as np


def detect(df: pd.DataFrame) -> dict:
    """
    Classify current market as TRENDING, RANGING, or VOLATILE.
    Returns regime dict used by combined_engine to adjust strategy weights.
    """
    try:
        if df is None or len(df) < 30:
            return {'regime': 'UNKNOWN', 'adx': 0, 'volatility_pct': 0, 'trend_strength': 0}

        close = df['close'].astype(float)
        high  = df['high'].astype(float)
        low   = df['low'].astype(float)

        # ADX (14-period)
        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low  - close.shift(1)).abs()
        ], axis=1).max(axis=1)

        dm_plus  = (high - high.shift(1)).clip(lower=0)
        dm_minus = (low.shift(1) - low).clip(lower=0)
        dm_plus  = dm_plus.where(dm_plus > dm_minus, 0)
        dm_minus = dm_minus.where(dm_minus > dm_plus, 0)

        atr14     = tr.ewm(span=14, adjust=False).mean()
        di_plus   = 100 * dm_plus.ewm(span=14, adjust=False).mean() / atr14.replace(0, np.nan)
        di_minus  = 100 * dm_minus.ewm(span=14, adjust=False).mean() / atr14.replace(0, np.nan)
        dx        = 100 * (di_plus - di_minus).abs() / (di_plus + di_minus).replace(0, np.nan)
        adx       = dx.ewm(span=14, adjust=False).mean().iloc[-1]
        adx       = float(adx) if not np.isnan(adx) else 0.0

        # Volatility: ATR as % of price
        atr_val     = float(atr14.iloc[-1]) if not np.isnan(atr14.iloc[-1]) else 0.0
        current_price = float(close.iloc[-1])
        volatility_pct = (atr_val / current_price * 100) if current_price else 0.0

        # Historical volatility (20-period std of returns)
        returns    = close.pct_change().dropna()
        hist_vol   = float(returns.rolling(20).std().iloc[-1] * 100) if len(returns) >= 20 else 0.0

        # Trend direction: slope of EMA20
        ema20      = close.ewm(span=20, adjust=False).mean()
        slope      = (float(ema20.iloc[-1]) - float(ema20.iloc[-5])) / float(ema20.iloc[-5]) * 100 if float(ema20.iloc[-5]) else 0
        trend_strength = abs(slope)

        # Classification logic
        if hist_vol > 2.5:
            regime = 'VOLATILE'
        elif adx >= 25:
            regime = 'TRENDING'
        else:
            regime = 'RANGING'

        # Strategy weight multipliers for each regime
        # Trending  → favour trend + momentum + breakout
        # Ranging   → favour support_resistance + reversal + candlestick
        # Volatile  → reduce all weights, require higher vote threshold
        weight_map = {
            'TRENDING': {
                'candlestick': 0.8, 'trend': 1.5, 'momentum': 1.3,
                'breakout': 1.4, 'support_resistance': 0.8,
                'volume': 1.2, 'reversal': 0.6, 'options': 1.0
            },
            'RANGING': {
                'candlestick': 1.3, 'trend': 0.7, 'momentum': 1.0,
                'breakout': 0.6, 'support_resistance': 1.5,
                'volume': 1.0, 'reversal': 1.4, 'options': 1.0
            },
            'VOLATILE': {
                'candlestick': 0.7, 'trend': 0.7, 'momentum': 0.8,
                'breakout': 0.7, 'support_resistance': 1.0,
                'volume': 1.3, 'reversal': 0.7, 'options': 1.0
            },
            'UNKNOWN': {
                'candlestick': 1.0, 'trend': 1.0, 'momentum': 1.0,
                'breakout': 1.0, 'support_resistance': 1.0,
                'volume': 1.0, 'reversal': 1.0, 'options': 1.0
            }
        }

        return {
            'regime': regime,
            'adx': round(adx, 2),
            'volatility_pct': round(volatility_pct, 3),
            'hist_vol': round(hist_vol, 3),
            'trend_strength': round(trend_strength, 4),
            'weights': weight_map[regime]
        }

    except Exception:
        return {
            'regime': 'UNKNOWN', 'adx': 0, 'volatility_pct': 0,
            'trend_strength': 0,
            'weights': {k: 1.0 for k in ['candlestick','trend','momentum','breakout',
                                           'support_resistance','volume','reversal','options']}
        }
