import pandas as pd
import numpy as np
import pandas_ta as ta
from typing import Optional


def analyze(df: pd.DataFrame) -> dict:
    if len(df) < 50:
        return {'signal': 'NEUTRAL', 'strength': 0, 'confirmations': []}

    close = df['close']
    high = df['high']
    low = df['low']

    buy_strength = 0
    sell_strength = 0
    confirmations = []

    # ─── EMA calculations ──────────────────────────────────────────────────────
    ema9 = ta.ema(close, length=9)
    ema21 = ta.ema(close, length=21)
    ema50 = ta.ema(close, length=50)
    ema200 = ta.ema(close, length=200) if len(df) >= 200 else None

    if ema9 is not None and ema21 is not None and len(ema9) >= 2:
        ema9_curr = ema9.iloc[-1]
        ema9_prev = ema9.iloc[-2]
        ema21_curr = ema21.iloc[-1]
        ema21_prev = ema21.iloc[-2]

        # EMA 9/21 crossover
        if ema9_prev <= ema21_prev and ema9_curr > ema21_curr:
            buy_strength += 4
            confirmations.append('EMA9/21 Bullish Crossover')
        elif ema9_prev >= ema21_prev and ema9_curr < ema21_curr:
            sell_strength += 4
            confirmations.append('EMA9/21 Bearish Crossover')

        # EMA trend alignment
        curr_close = close.iloc[-1]
        if ema50 is not None:
            ema50_curr = ema50.iloc[-1]
            if curr_close > ema9_curr > ema21_curr > ema50_curr:
                buy_strength += 2
                confirmations.append('EMA Full Bullish Alignment')
            elif curr_close < ema9_curr < ema21_curr < ema50_curr:
                sell_strength += 2
                confirmations.append('EMA Full Bearish Alignment')

    # ─── EMA 50/200 Golden/Death Cross ─────────────────────────────────────────
    if ema50 is not None and ema200 is not None and len(ema50) >= 2 and len(ema200) >= 2:
        e50_curr = ema50.iloc[-1]
        e50_prev = ema50.iloc[-2]
        e200_curr = ema200.iloc[-1]
        e200_prev = ema200.iloc[-2]

        if e50_prev <= e200_prev and e50_curr > e200_curr:
            buy_strength += 5
            confirmations.append('EMA50/200 Golden Cross')
        elif e50_prev >= e200_prev and e50_curr < e200_curr:
            sell_strength += 5
            confirmations.append('EMA50/200 Death Cross')

    # ─── ADX ───────────────────────────────────────────────────────────────────
    try:
        adx_df = ta.adx(high, low, close, length=14)
        if adx_df is not None and not adx_df.empty:
            adx_col = [c for c in adx_df.columns if c.startswith('ADX_')]
            dmp_col = [c for c in adx_df.columns if c.startswith('DMP_')]
            dmn_col = [c for c in adx_df.columns if c.startswith('DMN_')]

            if adx_col and dmp_col and dmn_col:
                adx_val = adx_df[adx_col[0]].iloc[-1]
                dmp_val = adx_df[dmp_col[0]].iloc[-1]
                dmn_val = adx_df[dmn_col[0]].iloc[-1]

                if adx_val > 25:
                    if dmp_val > dmn_val:
                        buy_strength += 3
                        confirmations.append(f'ADX Bullish Trend ({adx_val:.1f})')
                    else:
                        sell_strength += 3
                        confirmations.append(f'ADX Bearish Trend ({adx_val:.1f})')

                    # ADX slope
                    adx_prev = adx_df[adx_col[0]].iloc[-3:]
                    if all(adx_prev.iloc[i] < adx_prev.iloc[i+1] for i in range(len(adx_prev)-1)):
                        if dmp_val > dmn_val:
                            buy_strength += 1
                        else:
                            sell_strength += 1
                        confirmations.append('ADX Strengthening')
    except Exception:
        pass

    # ─── Supertrend ────────────────────────────────────────────────────────────
    try:
        st_df = ta.supertrend(high, low, close, length=10, multiplier=3.0)
        if st_df is not None and not st_df.empty:
            dir_col = [c for c in st_df.columns if 'SUPERTd' in c]
            if dir_col:
                curr_dir = st_df[dir_col[0]].iloc[-1]
                prev_dir = st_df[dir_col[0]].iloc[-2]

                if curr_dir == 1:
                    if prev_dir == -1:
                        buy_strength += 4
                        confirmations.append('Supertrend Bullish Flip')
                    else:
                        buy_strength += 2
                        confirmations.append('Supertrend Bullish')
                elif curr_dir == -1:
                    if prev_dir == 1:
                        sell_strength += 4
                        confirmations.append('Supertrend Bearish Flip')
                    else:
                        sell_strength += 2
                        confirmations.append('Supertrend Bearish')
    except Exception:
        pass

    # ─── Parabolic SAR ─────────────────────────────────────────────────────────
    try:
        psar_df = ta.psar(high, low, close)
        if psar_df is not None and not psar_df.empty:
            long_col = [c for c in psar_df.columns if 'PSARl' in c]
            short_col = [c for c in psar_df.columns if 'PSARs' in c]
            if long_col and short_col:
                sar_long_curr = psar_df[long_col[0]].iloc[-1]
                sar_long_prev = psar_df[long_col[0]].iloc[-2]
                sar_short_curr = psar_df[short_col[0]].iloc[-1]
                sar_short_prev = psar_df[short_col[0]].iloc[-2]

                curr_close = close.iloc[-1]

                if not np.isnan(sar_long_curr) and curr_close > sar_long_curr:
                    buy_strength += 2
                    if np.isnan(sar_long_prev):
                        buy_strength += 2
                        confirmations.append('PSAR Bullish Flip')
                    else:
                        confirmations.append('PSAR Bullish')

                elif not np.isnan(sar_short_curr) and curr_close < sar_short_curr:
                    sell_strength += 2
                    if np.isnan(sar_short_prev):
                        sell_strength += 2
                        confirmations.append('PSAR Bearish Flip')
                    else:
                        confirmations.append('PSAR Bearish')
    except Exception:
        pass

    # ─── Ichimoku Cloud ────────────────────────────────────────────────────────
    try:
        ichi = ta.ichimoku(high, low, close)
        if ichi is not None and len(ichi) >= 2:
            ichi_df = ichi[0]
            if ichi_df is not None and not ichi_df.empty:
                tenkan_col = [c for c in ichi_df.columns if 'ITS' in c]
                kijun_col = [c for c in ichi_df.columns if 'IKS' in c]
                senkoa_col = [c for c in ichi_df.columns if 'ISA' in c]
                senkob_col = [c for c in ichi_df.columns if 'ISB' in c]

                if tenkan_col and kijun_col and senkoa_col and senkob_col:
                    tenkan = ichi_df[tenkan_col[0]].iloc[-1]
                    kijun = ichi_df[kijun_col[0]].iloc[-1]
                    tenkan_prev = ichi_df[tenkan_col[0]].iloc[-2]
                    kijun_prev = ichi_df[kijun_col[0]].iloc[-2]
                    senka = ichi_df[senkoa_col[0]].iloc[-1]
                    senkb = ichi_df[senkob_col[0]].iloc[-1]

                    cloud_top = max(senka, senkb)
                    cloud_bot = min(senka, senkb)
                    curr_close = close.iloc[-1]

                    if curr_close > cloud_top and tenkan > kijun:
                        buy_strength += 3
                        confirmations.append('Ichimoku Bullish')
                    elif curr_close < cloud_bot and tenkan < kijun:
                        sell_strength += 3
                        confirmations.append('Ichimoku Bearish')

                    if tenkan_prev <= kijun_prev and tenkan > kijun:
                        buy_strength += 2
                        confirmations.append('Ichimoku TK Bullish Cross')
                    elif tenkan_prev >= kijun_prev and tenkan < kijun:
                        sell_strength += 2
                        confirmations.append('Ichimoku TK Bearish Cross')
    except Exception:
        pass

    # ─── DEMA and TEMA ─────────────────────────────────────────────────────────
    try:
        dema = ta.dema(close, length=20)
        if dema is not None and not dema.empty:
            if close.iloc[-1] > dema.iloc[-1]:
                buy_strength += 1
                confirmations.append('DEMA Bullish')
            else:
                sell_strength += 1
                confirmations.append('DEMA Bearish')
    except Exception:
        pass

    try:
        tema = ta.tema(close, length=20)
        if tema is not None and not tema.empty:
            if close.iloc[-1] > tema.iloc[-1]:
                buy_strength += 1
                confirmations.append('TEMA Bullish')
            else:
                sell_strength += 1
                confirmations.append('TEMA Bearish')
    except Exception:
        pass

    # ─── HMA slope ─────────────────────────────────────────────────────────────
    try:
        hma = ta.hma(close, length=21)
        if hma is not None and len(hma) >= 3:
            h_curr = hma.iloc[-1]
            h_prev = hma.iloc[-2]
            if h_curr > h_prev:
                buy_strength += 2
                confirmations.append('HMA Slope Positive')
            else:
                sell_strength += 2
                confirmations.append('HMA Slope Negative')
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
