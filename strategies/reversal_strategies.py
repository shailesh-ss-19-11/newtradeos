import pandas as pd
import numpy as np
import pandas_ta as ta
from typing import Optional


def _find_peaks_troughs(arr: np.ndarray, min_distance: int = 3) -> tuple[list, list]:
    peaks = []
    troughs = []
    n = len(arr)
    for i in range(min_distance, n - min_distance):
        window = arr[i - min_distance:i + min_distance + 1]
        if arr[i] == window.max():
            peaks.append((i, arr[i]))
        if arr[i] == window.min():
            troughs.append((i, arr[i]))
    return peaks, troughs


def analyze(df: pd.DataFrame) -> dict:
    if len(df) < 25:
        return {'signal': 'NEUTRAL', 'strength': 0, 'confirmations': []}

    close = df['close']
    high = df['high']
    low = df['low']

    curr_close = close.iloc[-1]
    prev_close = close.iloc[-2]

    buy_strength = 0
    sell_strength = 0
    confirmations = []

    highs_arr = high.values
    lows_arr = low.values
    closes_arr = close.values

    # ─── Double Bottom / Top ───────────────────────────────────────────────────
    try:
        lookback = min(50, len(df))
        half = lookback // 2
        lows_first = lows_arr[-lookback:-half]
        lows_second = lows_arr[-half:]
        highs_first = highs_arr[-lookback:-half]
        highs_second = highs_arr[-half:]

        low1 = np.min(lows_first)
        low2 = np.min(lows_second)
        if abs(low1 - low2) / max(low1, 1) < 0.02 and curr_close > low2 and curr_close > closes_arr[-half]:
            buy_strength += 5
            confirmations.append(f'Double Bottom ({low1:.2f}, {low2:.2f})')

        high1 = np.max(highs_first)
        high2 = np.max(highs_second)
        if abs(high1 - high2) / max(high1, 1) < 0.02 and curr_close < high2 and curr_close < closes_arr[-half]:
            sell_strength += 5
            confirmations.append(f'Double Top ({high1:.2f}, {high2:.2f})')
    except Exception:
        pass

    # ─── Triple Bottom / Top ───────────────────────────────────────────────────
    try:
        if len(df) >= 60:
            third = len(df) // 3
            l1 = np.min(lows_arr[-60:-40])
            l2 = np.min(lows_arr[-40:-20])
            l3 = np.min(lows_arr[-20:])
            if abs(l1 - l2) / max(l1, 1) < 0.02 and abs(l2 - l3) / max(l2, 1) < 0.02 and curr_close > l3:
                buy_strength += 5
                confirmations.append(f'Triple Bottom ({l1:.2f})')

            h1 = np.max(highs_arr[-60:-40])
            h2 = np.max(highs_arr[-40:-20])
            h3 = np.max(highs_arr[-20:])
            if abs(h1 - h2) / max(h1, 1) < 0.02 and abs(h2 - h3) / max(h2, 1) < 0.02 and curr_close < h3:
                sell_strength += 5
                confirmations.append(f'Triple Top ({h1:.2f})')
    except Exception:
        pass

    # ─── Head and Shoulders ────────────────────────────────────────────────────
    try:
        if len(df) >= 30:
            peaks, _ = _find_peaks_troughs(highs_arr[-30:])
            if len(peaks) >= 3:
                last3 = peaks[-3:]
                idx0, h0 = last3[0]
                idx1, h1 = last3[1]
                idx2, h2 = last3[2]

                if h1 > h0 and h1 > h2 and abs(h0 - h2) / max(h0, 1) < 0.03:
                    neckline = (lows_arr[idx0] + lows_arr[idx2]) / 2 if idx0 < len(lows_arr) and idx2 < len(lows_arr) else 0
                    if curr_close < neckline and prev_close >= neckline:
                        sell_strength += 5
                        confirmations.append(f'Head and Shoulders Neckline Break ({neckline:.2f})')

        if len(df) >= 30:
            _, troughs = _find_peaks_troughs(lows_arr[-30:])
            if len(troughs) >= 3:
                last3 = troughs[-3:]
                idx0, t0 = last3[0]
                idx1, t1 = last3[1]
                idx2, t2 = last3[2]

                if t1 < t0 and t1 < t2 and abs(t0 - t2) / max(t0, 1) < 0.03:
                    neckline = (highs_arr[idx0] + highs_arr[idx2]) / 2 if idx0 < len(highs_arr) and idx2 < len(highs_arr) else 0
                    if curr_close > neckline and prev_close <= neckline:
                        buy_strength += 5
                        confirmations.append(f'Inverse H&S Neckline Break ({neckline:.2f})')
    except Exception:
        pass

    # ─── Wedge Patterns ────────────────────────────────────────────────────────
    try:
        if len(df) >= 20:
            subset_h = highs_arr[-20:]
            subset_l = lows_arr[-20:]
            x = np.arange(len(subset_h))

            slope_h, _ = np.polyfit(x, subset_h, 1)
            slope_l, _ = np.polyfit(x, subset_l, 1)

            if slope_h < 0 and slope_l < 0 and slope_h > slope_l:
                if curr_close > subset_h[-1]:
                    buy_strength += 4
                    confirmations.append('Falling Wedge Breakout Up')

            if slope_h > 0 and slope_l > 0 and slope_h < slope_l:
                if curr_close < subset_l[-1]:
                    sell_strength += 4
                    confirmations.append('Rising Wedge Breakdown')
    except Exception:
        pass

    # ─── Triangle Patterns ─────────────────────────────────────────────────────
    try:
        if len(df) >= 20:
            subset_h = highs_arr[-20:]
            subset_l = lows_arr[-20:]
            x = np.arange(len(subset_h))

            slope_h, intercept_h = np.polyfit(x, subset_h, 1)
            slope_l, intercept_l = np.polyfit(x, subset_l, 1)

            std_h = np.std(subset_h - (slope_h * x + intercept_h))
            std_l = np.std(subset_l - (slope_l * x + intercept_l))

            resistance_now = slope_h * (len(x) - 1) + intercept_h
            support_now = slope_l * (len(x) - 1) + intercept_l

            flat_high = abs(slope_h) < 0.05 * np.mean(subset_h) / len(x)
            rising_low = slope_l > 0
            flat_low = abs(slope_l) < 0.05 * np.mean(subset_l) / len(x)
            falling_high = slope_h < 0

            if flat_high and rising_low:
                if curr_close > resistance_now and prev_close <= resistance_now:
                    buy_strength += 4
                    confirmations.append('Ascending Triangle Breakout')

            if flat_low and falling_high:
                if curr_close < support_now and prev_close >= support_now:
                    sell_strength += 4
                    confirmations.append('Descending Triangle Breakdown')

            if falling_high and rising_low:
                prior_trend_up = closes_arr[-30] < closes_arr[-20] if len(closes_arr) >= 30 else False
                if curr_close > resistance_now and prior_trend_up:
                    buy_strength += 3
                    confirmations.append('Symmetrical Triangle Bullish Breakout')
                elif curr_close < support_now and not prior_trend_up:
                    sell_strength += 3
                    confirmations.append('Symmetrical Triangle Bearish Breakdown')
    except Exception:
        pass

    # ─── Cup and Handle ────────────────────────────────────────────────────────
    try:
        if len(df) >= 40:
            cup_section = closes_arr[-40:-10]
            handle_section = closes_arr[-10:]

            cup_left = cup_section[0]
            cup_bottom = np.min(cup_section)
            cup_right = cup_section[-1]
            cup_rim = max(cup_left, cup_right)

            handle_low = np.min(handle_section)
            handle_decline = (cup_rim - handle_low) / cup_rim if cup_rim > 0 else 0

            is_u_shape = cup_bottom < cup_left * 0.97 and abs(cup_left - cup_right) / cup_left < 0.03
            is_handle = 0.02 < handle_decline < 0.15

            if is_u_shape and is_handle and curr_close > cup_rim and prev_close <= cup_rim:
                buy_strength += 4
                confirmations.append(f'Cup and Handle Breakout (Rim: {cup_rim:.2f})')
    except Exception:
        pass

    # ─── Mean Reversion ────────────────────────────────────────────────────────
    try:
        ema20 = ta.ema(close, length=20)
        if ema20 is not None and len(ema20) >= 1:
            ema20_val = ema20.iloc[-1]
            deviation = (curr_close - ema20_val) / ema20_val * 100 if ema20_val > 0 else 0

            if deviation < -3:
                buy_strength += 2
                confirmations.append(f'Mean Reversion Setup ({deviation:.1f}% below EMA20)')
            elif deviation > 3:
                sell_strength += 2
                confirmations.append(f'Mean Reversion Setup ({deviation:.1f}% above EMA20)')
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
        'confirmations': confirmations
    }
