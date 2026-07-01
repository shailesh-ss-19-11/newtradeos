"""
Dynamic strategy signal generation engine.
Supports multiple strategy types configurable by users.
Signal is generated on the LAST bar of the provided DataFrame (no look-ahead).
"""

import pandas as pd
import numpy as np
from typing import Literal

Signal = Literal['BUY', 'SELL', 'NEUTRAL']

STRATEGY_TYPES = [
    {
        'type': 'ema_crossover',
        'label': 'EMA Crossover',
        'description': 'Buy when fast EMA crosses above slow EMA, sell on crossunder',
        'params': [
            {'key': 'fast_period', 'label': 'Fast Period', 'type': 'number', 'default': 9, 'min': 2, 'max': 50},
            {'key': 'slow_period', 'label': 'Slow Period', 'type': 'number', 'default': 21, 'min': 5, 'max': 200},
        ]
    },
    {
        'type': 'rsi_strategy',
        'label': 'RSI Strategy',
        'description': 'Buy when RSI crosses above oversold level, sell when it crosses below overbought',
        'params': [
            {'key': 'period',      'label': 'RSI Period',   'type': 'number', 'default': 14, 'min': 5, 'max': 50},
            {'key': 'oversold',    'label': 'Oversold',     'type': 'number', 'default': 30, 'min': 10, 'max': 45},
            {'key': 'overbought',  'label': 'Overbought',   'type': 'number', 'default': 70, 'min': 55, 'max': 90},
        ]
    },
    {
        'type': 'macd_crossover',
        'label': 'MACD Crossover',
        'description': 'Buy when MACD line crosses above signal line, sell on crossunder',
        'params': [
            {'key': 'fast',   'label': 'Fast Period',   'type': 'number', 'default': 12, 'min': 5,  'max': 50},
            {'key': 'slow',   'label': 'Slow Period',   'type': 'number', 'default': 26, 'min': 10, 'max': 100},
            {'key': 'signal', 'label': 'Signal Period', 'type': 'number', 'default': 9,  'min': 3,  'max': 30},
        ]
    },
    {
        'type': 'bollinger_breakout',
        'label': 'Bollinger Bands Breakout',
        'description': 'Buy when price breaks above upper band, sell when it breaks below lower band',
        'params': [
            {'key': 'period',  'label': 'Period',          'type': 'number', 'default': 20,  'min': 5,   'max': 100},
            {'key': 'std_dev', 'label': 'Std Dev',         'type': 'number', 'default': 2.0, 'min': 1.0, 'max': 4.0},
        ]
    },
    {
        'type': 'supertrend',
        'label': 'Supertrend',
        'description': 'Buy when price moves above Supertrend line, sell when it moves below',
        'params': [
            {'key': 'period',     'label': 'ATR Period',   'type': 'number', 'default': 10,  'min': 5,   'max': 50},
            {'key': 'multiplier', 'label': 'Multiplier',   'type': 'number', 'default': 3.0, 'min': 1.0, 'max': 6.0},
        ]
    },
    {
        'type': 'multi_strategy_voting',
        'label': 'Multi-Strategy Voting',
        'description': 'Combines all 8 strategy modules using a voting system',
        'params': [
            {'key': 'min_votes', 'label': 'Min Votes Required', 'type': 'number', 'default': 4, 'min': 1, 'max': 8},
        ]
    },
    {
        'type': 'composite_signal',
        'label': 'Composite Signal (Custom)',
        'description': 'Combine EMA crossover + RSI filter + Volume filter with AND logic — toggle each on/off',
        'params': [
            {'key': 'use_ema',      'label': 'Use EMA Crossover (0/1)',   'type': 'number', 'default': 1,   'min': 0, 'max': 1},
            {'key': 'ema_fast',     'label': 'EMA Fast Period',           'type': 'number', 'default': 9,   'min': 2, 'max': 50},
            {'key': 'ema_slow',     'label': 'EMA Slow Period',           'type': 'number', 'default': 21,  'min': 5, 'max': 200},
            {'key': 'use_rsi',      'label': 'Use RSI Filter (0/1)',      'type': 'number', 'default': 1,   'min': 0, 'max': 1},
            {'key': 'rsi_period',   'label': 'RSI Period',                'type': 'number', 'default': 14,  'min': 5, 'max': 50},
            {'key': 'rsi_min',      'label': 'RSI Min Threshold',         'type': 'number', 'default': 40,  'min': 10, 'max': 80},
            {'key': 'use_volume',   'label': 'Use Volume Filter (0/1)',   'type': 'number', 'default': 0,   'min': 0, 'max': 1},
            {'key': 'volume_factor','label': 'Volume > N× 20-day Avg',   'type': 'number', 'default': 1.5, 'min': 1.0, 'max': 5.0},
        ]
    },
    {
        'type': 'ai_ml_signal',
        'label': 'AI / Machine Learning Signal',
        'description': 'RandomForest model trained on OHLCV features; learns patterns from historical data',
        'params': [
            {'key': 'lookback',           'label': 'Training Lookback (bars)', 'type': 'number', 'default': 252, 'min': 100, 'max': 1000},
            {'key': 'n_estimators',       'label': 'Trees in Forest',          'type': 'number', 'default': 100, 'min': 10,  'max': 500},
            {'key': 'prediction_horizon', 'label': 'Prediction Horizon (bars)','type': 'number', 'default': 5,   'min': 1,   'max': 20},
            {'key': 'return_threshold',   'label': 'BUY if return > % (fwd)',  'type': 'number', 'default': 2.0, 'min': 0.5, 'max': 10.0},
        ]
    },
]


def get_strategy_types() -> list:
    return STRATEGY_TYPES


def generate_signal(strategy_type: str, params: dict, df: pd.DataFrame) -> Signal:
    if df is None or len(df) < 30:
        return 'NEUTRAL'

    try:
        if strategy_type == 'ema_crossover':
            return _ema_crossover(df, params)
        elif strategy_type == 'rsi_strategy':
            return _rsi_strategy(df, params)
        elif strategy_type == 'macd_crossover':
            return _macd_crossover(df, params)
        elif strategy_type == 'bollinger_breakout':
            return _bollinger_breakout(df, params)
        elif strategy_type == 'supertrend':
            return _supertrend(df, params)
        elif strategy_type == 'multi_strategy_voting':
            return _multi_strategy_voting(df, params)
        elif strategy_type == 'composite_signal':
            return _composite_signal(df, params)
        elif strategy_type == 'ai_ml_signal':
            return _ai_ml_signal(df, params)
        else:
            return 'NEUTRAL'
    except Exception:
        return 'NEUTRAL'


def _ema_crossover(df: pd.DataFrame, params: dict) -> Signal:
    fast = int(params.get('fast_period', 9))
    slow = int(params.get('slow_period', 21))

    if len(df) < slow + 2:
        return 'NEUTRAL'

    close = df['close']
    ema_f = close.ewm(span=fast, adjust=False).mean()
    ema_s = close.ewm(span=slow, adjust=False).mean()

    cross_up   = ema_f.iloc[-2] <= ema_s.iloc[-2] and ema_f.iloc[-1] > ema_s.iloc[-1]
    cross_down = ema_f.iloc[-2] >= ema_s.iloc[-2] and ema_f.iloc[-1] < ema_s.iloc[-1]

    if cross_up:
        return 'BUY'
    if cross_down:
        return 'SELL'
    return 'NEUTRAL'


def _rsi_strategy(df: pd.DataFrame, params: dict) -> Signal:
    period   = int(params.get('period', 14))
    oversold = float(params.get('oversold', 30))
    overbought = float(params.get('overbought', 70))

    if len(df) < period + 2:
        return 'NEUTRAL'

    close = df['close']
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    prev_rsi = rsi.iloc[-2]
    last_rsi = rsi.iloc[-1]

    if pd.isna(prev_rsi) or pd.isna(last_rsi):
        return 'NEUTRAL'

    if prev_rsi <= oversold and last_rsi > oversold:
        return 'BUY'
    if prev_rsi >= overbought and last_rsi < overbought:
        return 'SELL'
    return 'NEUTRAL'


def _macd_crossover(df: pd.DataFrame, params: dict) -> Signal:
    fast   = int(params.get('fast', 12))
    slow   = int(params.get('slow', 26))
    signal = int(params.get('signal', 9))

    if len(df) < slow + signal + 2:
        return 'NEUTRAL'

    close = df['close']
    ema_f = close.ewm(span=fast, adjust=False).mean()
    ema_s = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_f - ema_s
    sig_line  = macd_line.ewm(span=signal, adjust=False).mean()

    cross_up   = macd_line.iloc[-2] <= sig_line.iloc[-2] and macd_line.iloc[-1] > sig_line.iloc[-1]
    cross_down = macd_line.iloc[-2] >= sig_line.iloc[-2] and macd_line.iloc[-1] < sig_line.iloc[-1]

    if cross_up:
        return 'BUY'
    if cross_down:
        return 'SELL'
    return 'NEUTRAL'


def _bollinger_breakout(df: pd.DataFrame, params: dict) -> Signal:
    period  = int(params.get('period', 20))
    std_dev = float(params.get('std_dev', 2.0))

    if len(df) < period + 2:
        return 'NEUTRAL'

    close = df['close']
    sma   = close.rolling(period).mean()
    std   = close.rolling(period).std()
    upper = sma + std_dev * std
    lower = sma - std_dev * std

    prev_close = close.iloc[-2]
    last_close = close.iloc[-1]
    prev_upper = upper.iloc[-2]
    prev_lower = lower.iloc[-2]
    last_upper = upper.iloc[-1]
    last_lower = lower.iloc[-1]

    if any(pd.isna([prev_close, last_close, prev_upper, prev_lower])):
        return 'NEUTRAL'

    if prev_close <= prev_upper and last_close > last_upper:
        return 'BUY'
    if prev_close >= prev_lower and last_close < last_lower:
        return 'SELL'
    return 'NEUTRAL'


def _supertrend(df: pd.DataFrame, params: dict) -> Signal:
    period     = int(params.get('period', 10))
    multiplier = float(params.get('multiplier', 3.0))

    if len(df) < period + 5:
        return 'NEUTRAL'

    high  = df['high'].values
    low   = df['low'].values
    close = df['close'].values
    n     = len(df)

    tr = np.zeros(n)
    for i in range(1, n):
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i-1]), abs(low[i] - close[i-1]))

    atr = np.zeros(n)
    atr[period] = np.mean(tr[1:period+1])
    for i in range(period + 1, n):
        atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period

    basic_upper = (high + low) / 2 + multiplier * atr
    basic_lower = (high + low) / 2 - multiplier * atr

    final_upper = basic_upper.copy()
    final_lower = basic_lower.copy()
    direction   = np.zeros(n)

    for i in range(1, n):
        final_upper[i] = basic_upper[i] if (basic_upper[i] < final_upper[i-1] or close[i-1] > final_upper[i-1]) else final_upper[i-1]
        final_lower[i] = basic_lower[i] if (basic_lower[i] > final_lower[i-1] or close[i-1] < final_lower[i-1]) else final_lower[i-1]

        if close[i] > final_upper[i]:
            direction[i] = 1   # bullish
        elif close[i] < final_lower[i]:
            direction[i] = -1  # bearish
        else:
            direction[i] = direction[i-1]

    if direction[-2] == -1 and direction[-1] == 1:
        return 'BUY'
    if direction[-2] == 1 and direction[-1] == -1:
        return 'SELL'
    return 'NEUTRAL'


def _composite_signal(df: pd.DataFrame, params: dict) -> Signal:
    """AND-logic combination of EMA crossover + RSI filter + Volume filter."""
    use_ema    = int(params.get('use_ema', 1)) == 1
    use_rsi    = int(params.get('use_rsi', 1)) == 1
    use_vol    = int(params.get('use_volume', 0)) == 1

    close  = df['close']
    conditions_met = []

    if use_ema:
        fast = int(params.get('ema_fast', 9))
        slow = int(params.get('ema_slow', 21))
        if len(df) < slow + 2:
            return 'NEUTRAL'
        ema_f = close.ewm(span=fast, adjust=False).mean()
        ema_s = close.ewm(span=slow, adjust=False).mean()
        cross_up = ema_f.iloc[-2] <= ema_s.iloc[-2] and ema_f.iloc[-1] > ema_s.iloc[-1]
        conditions_met.append(cross_up)

    if use_rsi:
        period  = int(params.get('rsi_period', 14))
        rsi_min = float(params.get('rsi_min', 40))
        if len(df) < period + 2:
            return 'NEUTRAL'
        delta = close.diff()
        gain  = delta.clip(lower=0).rolling(period).mean()
        loss  = (-delta.clip(upper=0)).rolling(period).mean()
        rs    = gain / loss.replace(0, np.nan)
        rsi   = 100 - (100 / (1 + rs))
        conditions_met.append(not pd.isna(rsi.iloc[-1]) and rsi.iloc[-1] > rsi_min)

    if use_vol:
        if 'volume' in df.columns:
            vol_factor = float(params.get('volume_factor', 1.5))
            vol_avg    = df['volume'].rolling(20).mean()
            conditions_met.append(df['volume'].iloc[-1] > vol_factor * vol_avg.iloc[-1])

    if not conditions_met:
        return 'NEUTRAL'

    return 'BUY' if all(conditions_met) else 'NEUTRAL'


def _ai_ml_signal(df: pd.DataFrame, params: dict) -> Signal:
    """RandomForest trained on OHLCV-derived features; signal for the last bar."""
    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.preprocessing import StandardScaler
    except ImportError:
        return 'NEUTRAL'

    lookback   = int(params.get('lookback', 252))
    n_trees    = int(params.get('n_estimators', 100))
    horizon    = int(params.get('prediction_horizon', 5))
    threshold  = float(params.get('return_threshold', 2.0)) / 100.0

    if len(df) < lookback + horizon + 30:
        return 'NEUTRAL'

    close  = df['close'].values
    high   = df['high'].values
    low    = df['low'].values
    volume = df['volume'].values if 'volume' in df.columns else np.ones(len(df))

    def _build_features(i):
        c = close[:i+1]
        ret1  = (c[-1] / c[-2] - 1) if len(c) > 1 else 0
        ret5  = (c[-1] / c[-6] - 1) if len(c) > 5 else 0
        ret20 = (c[-1] / c[-21] - 1) if len(c) > 20 else 0
        # RSI(14)
        delta = np.diff(c[-16:]) if len(c) >= 16 else np.zeros(1)
        gain  = np.mean(delta[delta > 0]) if np.any(delta > 0) else 0
        loss  = -np.mean(delta[delta < 0]) if np.any(delta < 0) else 1e-9
        rsi   = 100 - 100 / (1 + gain / max(loss, 1e-9))
        # Bollinger position
        if len(c) >= 20:
            sma = np.mean(c[-20:])
            std = np.std(c[-20:])
            bb_pos = (c[-1] - sma) / max(std, 1e-9)
        else:
            bb_pos = 0
        # Volume ratio
        v    = volume[:i+1]
        vrat = (v[-1] / np.mean(v[-20:])) if len(v) >= 20 else 1.0
        # HL range ratio
        hl_r = (high[i] - low[i]) / max(close[i], 1e-9)
        return [ret1, ret5, ret20, rsi, bb_pos, vrat, hl_r]

    # Build training set using rows [0 .. len-horizon-2]
    use = min(lookback, len(df) - horizon - 2)
    start_idx = len(df) - use - horizon - 1

    X, y = [], []
    for i in range(start_idx, len(df) - horizon - 1):
        feat  = _build_features(i)
        fwd_r = close[i + horizon] / close[i] - 1
        label = 1 if fwd_r > threshold else (-1 if fwd_r < -threshold else 0)
        X.append(feat)
        y.append(label)

    X, y = np.array(X), np.array(y)
    if len(X) < 20 or len(np.unique(y)) < 2:
        return 'NEUTRAL'

    scaler = StandardScaler()
    X_s = scaler.fit_transform(X)

    clf = RandomForestClassifier(n_estimators=n_trees, random_state=42, n_jobs=-1)
    clf.fit(X_s, y)

    feat_last = np.array([_build_features(len(df) - 1)])
    pred = clf.predict(scaler.transform(feat_last))[0]

    if pred == 1:
        return 'BUY'
    if pred == -1:
        return 'SELL'
    return 'NEUTRAL'


def _multi_strategy_voting(df: pd.DataFrame, params: dict) -> Signal:
    min_votes = int(params.get('min_votes', 4))

    try:
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from strategies import (
            candlestick_patterns, trend_strategies, momentum_strategies,
            breakout_strategies, support_resistance, volume_strategies,
            reversal_strategies
        )
        results = {
            'candlestick': candlestick_patterns.analyze(df),
            'trend':       trend_strategies.analyze(df),
            'momentum':    momentum_strategies.analyze(df),
            'breakout':    breakout_strategies.analyze(df),
            'support_resistance': support_resistance.analyze(df),
            'volume':      volume_strategies.analyze(df),
            'reversal':    reversal_strategies.analyze(df),
        }
        buy_votes  = sum(1 for r in results.values() if r.get('signal') == 'BUY')
        sell_votes = sum(1 for r in results.values() if r.get('signal') == 'SELL')

        if buy_votes >= min_votes and buy_votes > sell_votes:
            return 'BUY'
        if sell_votes >= min_votes and sell_votes > buy_votes:
            return 'SELL'
        return 'NEUTRAL'
    except Exception:
        return 'NEUTRAL'
