import pandas as pd
import numpy as np
import pandas_ta as ta
from typing import Optional


def _pivot_levels(prev_high: float, prev_low: float, prev_close: float) -> dict:
    pp = (prev_high + prev_low + prev_close) / 3
    r1 = 2 * pp - prev_low
    r2 = pp + (prev_high - prev_low)
    r3 = prev_high + 2 * (pp - prev_low)
    s1 = 2 * pp - prev_high
    s2 = pp - (prev_high - prev_low)
    s3 = prev_low - 2 * (prev_high - pp)
    return {'PP': pp, 'R1': r1, 'R2': r2, 'R3': r3, 'S1': s1, 'S2': s2, 'S3': s3}


def _camarilla_levels(prev_high: float, prev_low: float, prev_close: float) -> dict:
    rng = prev_high - prev_low
    return {
        'H4': prev_close + rng * 1.1 / 2,
        'H3': prev_close + rng * 1.1 / 4,
        'L3': prev_close - rng * 1.1 / 4,
        'L4': prev_close - rng * 1.1 / 2,
    }


def _fib_levels(swing_high: float, swing_low: float) -> dict:
    diff = swing_high - swing_low
    return {
        '23.6': swing_high - 0.236 * diff,
        '38.2': swing_high - 0.382 * diff,
        '50.0': swing_high - 0.500 * diff,
        '61.8': swing_high - 0.618 * diff,
        '78.6': swing_high - 0.786 * diff,
        'ext_127.2': swing_low - 0.272 * diff,
        'ext_161.8': swing_low - 0.618 * diff,
        'ext_261.8': swing_low - 1.618 * diff,
    }


def _find_sr_levels(df: pd.DataFrame, lookback: int = 100) -> list:
    subset = df.iloc[-lookback:] if len(df) >= lookback else df
    highs = subset['high'].values
    lows = subset['low'].values

    peaks = []
    troughs = []

    for i in range(2, len(highs) - 2):
        if highs[i] > highs[i-1] and highs[i] > highs[i+1] and highs[i] > highs[i-2] and highs[i] > highs[i+2]:
            peaks.append(highs[i])
        if lows[i] < lows[i-1] and lows[i] < lows[i+1] and lows[i] < lows[i-2] and lows[i] < lows[i+2]:
            troughs.append(lows[i])

    levels = []
    for level in peaks + troughs:
        found = False
        for existing in levels:
            if abs(existing['price'] - level) / level < 0.005:
                existing['touches'] += 1
                found = True
                break
        if not found:
            levels.append({'price': level, 'touches': 1})

    return sorted(levels, key=lambda x: x['price'])


def analyze(df: pd.DataFrame, options_data: Optional[dict] = None) -> dict:
    if len(df) < 10:
        return {'signal': 'NEUTRAL', 'strength': 0, 'confirmations': [], 'levels': {}}

    close = df['close']
    high = df['high']
    low = df['low']

    curr_close = close.iloc[-1]
    prev_close_val = close.iloc[-2] if len(close) >= 2 else curr_close

    buy_strength = 0
    sell_strength = 0
    confirmations = []
    all_levels = {}

    # ─── Pivot Points ──────────────────────────────────────────────────────────
    try:
        ph = high.iloc[-2] if len(high) > 1 else high.iloc[-1]
        pl = low.iloc[-2] if len(low) > 1 else low.iloc[-1]
        pc = close.iloc[-2] if len(close) > 1 else close.iloc[-1]

        pivots = _pivot_levels(ph, pl, pc)
        all_levels['pivots'] = pivots
        pp_val = pivots['PP']

        tolerance = 0.002

        for level_name, level_val in [('S3', pivots['S3']), ('S2', pivots['S2']), ('S1', pivots['S1'])]:
            if abs(curr_close - level_val) / curr_close < tolerance:
                if curr_close > prev_close_val:
                    buy_strength += 4
                    confirmations.append(f'Pivot {level_name} Bounce ({level_val:.2f})')

        for level_name, level_val in [('R1', pivots['R1']), ('R2', pivots['R2']), ('R3', pivots['R3'])]:
            if abs(curr_close - level_val) / curr_close < tolerance:
                if curr_close < prev_close_val:
                    sell_strength += 4
                    confirmations.append(f'Pivot {level_name} Rejection ({level_val:.2f})')
    except Exception:
        pass

    # ─── Camarilla Pivots ──────────────────────────────────────────────────────
    try:
        cam = _camarilla_levels(ph, pl, pc)
        all_levels['camarilla'] = cam

        if curr_close > cam['H4'] and prev_close_val <= cam['H4']:
            buy_strength += 3
            confirmations.append(f"Camarilla H4 Breakout ({cam['H4']:.2f})")
        elif curr_close < cam['L4'] and prev_close_val >= cam['L4']:
            sell_strength += 3
            confirmations.append(f"Camarilla L4 Breakout ({cam['L4']:.2f})")
    except Exception:
        pass

    # ─── Fibonacci Retracement ─────────────────────────────────────────────────
    try:
        lookback_fib = min(50, len(df))
        swing_high = high.iloc[-lookback_fib:].max()
        swing_low = low.iloc[-lookback_fib:].min()

        fib = _fib_levels(swing_high, swing_low)
        all_levels['fibonacci'] = fib

        tolerance_fib = 0.004
        fib_retracements = {
            '23.6': fib['23.6'], '38.2': fib['38.2'],
            '50.0': fib['50.0'], '61.8': fib['61.8'], '78.6': fib['78.6']
        }

        for level_name, level_val in fib_retracements.items():
            if abs(curr_close - level_val) / curr_close < tolerance_fib:
                strength_bonus = 1 if level_name == '61.8' else 0
                if curr_close > prev_close_val:
                    buy_strength += 3 + strength_bonus
                    confirmations.append(f'Fib {level_name}% Support Bounce ({level_val:.2f})')
                else:
                    sell_strength += 3 + strength_bonus
                    confirmations.append(f'Fib {level_name}% Resistance Rejection ({level_val:.2f})')
    except Exception:
        pass

    # ─── Horizontal S/R Levels ─────────────────────────────────────────────────
    try:
        sr_levels = _find_sr_levels(df)
        all_levels['horizontal_sr'] = sr_levels

        for level_info in sr_levels:
            lp = level_info['price']
            touches = level_info['touches']
            if abs(curr_close - lp) / curr_close < 0.003:
                extra = min(touches - 1, 2)
                if curr_close > prev_close_val:
                    buy_strength += 3 + extra
                    confirmations.append(f'Horizontal Support ({lp:.2f}, {touches} touches)')
                else:
                    sell_strength += 3 + extra
                    confirmations.append(f'Horizontal Resistance ({lp:.2f}, {touches} touches)')
    except Exception:
        pass

    # ─── Round Number Levels ───────────────────────────────────────────────────
    try:
        price = curr_close
        for increment in [1000, 500, 100, 50]:
            nearest = round(price / increment) * increment
            if abs(price - nearest) / price < 0.002:
                if price > prev_close_val:
                    buy_strength += 2
                    confirmations.append(f'Round Number Support ({nearest})')
                else:
                    sell_strength += 2
                    confirmations.append(f'Round Number Resistance ({nearest})')
                break
    except Exception:
        pass

    # ─── Options OI Wall ───────────────────────────────────────────────────────
    max_pain = None
    pcr = None
    ce_resistance = None
    pe_support = None

    if options_data:
        try:
            max_pain = options_data.get('max_pain')
            pcr = options_data.get('pcr', 0)
            ce_resistance = options_data.get('ce_resistance')
            pe_support = options_data.get('pe_support')

            if max_pain and curr_close:
                if max_pain > curr_close and max_pain - curr_close > curr_close * 0.005:
                    buy_strength += 2
                    confirmations.append(f'Below OI Max Pain ({max_pain})')
                elif max_pain < curr_close and curr_close - max_pain > curr_close * 0.005:
                    sell_strength += 2
                    confirmations.append(f'Above OI Max Pain ({max_pain})')

            if ce_resistance and abs(curr_close - ce_resistance) / curr_close < 0.005:
                sell_strength += 3
                confirmations.append(f'Near CE OI Wall Resistance ({ce_resistance})')

            if pe_support and abs(curr_close - pe_support) / curr_close < 0.005:
                buy_strength += 3
                confirmations.append(f'Near PE OI Wall Support ({pe_support})')

            if pcr > 1.5:
                buy_strength += 2
                confirmations.append(f'PCR Bullish ({pcr:.2f})')
            elif pcr < 0.7:
                sell_strength += 2
                confirmations.append(f'PCR Bearish ({pcr:.2f})')

        except Exception:
            pass

    # ─── Final signal ──────────────────────────────────────────────────────────
    if buy_strength > sell_strength:
        signal = 'BUY'
        strength = buy_strength
    elif sell_strength > buy_strength:
        signal = 'SELL'
        strength = sell_strength
    else:
        signal = 'NEUTRAL'
        strength = 0

    return {
        'signal': signal,
        'strength': strength,
        'buy_strength': buy_strength,
        'sell_strength': sell_strength,
        'confirmations': confirmations,
        'levels': all_levels,
        'max_pain': max_pain,
        'pcr': pcr,
        'ce_resistance': ce_resistance,
        'pe_support': pe_support
    }
