import pandas as pd
import numpy as np
import pandas_ta as ta


def _find_divergence(prices: np.ndarray, indicator: np.ndarray, window: int = 20) -> str:
    if len(prices) < window or len(indicator) < window:
        return 'NONE'

    half = window // 2
    p1 = prices[-window:-half]
    p2 = prices[-half:]
    i1 = indicator[-window:-half]
    i2 = indicator[-half:]

    p1_min = np.min(p1)
    p2_min = np.min(p2)
    i1_min = np.min(i1)
    i2_min = np.min(i2)

    p1_max = np.max(p1)
    p2_max = np.max(p2)
    i1_max = np.max(i1)
    i2_max = np.max(i2)

    if p2_min < p1_min and i2_min > i1_min:
        return 'BULL_DIVERGENCE'
    if p2_max > p1_max and i2_max < i1_max:
        return 'BEAR_DIVERGENCE'
    if p2_min > p1_min and i2_min < i1_min:
        return 'BULL_HIDDEN'
    if p2_max < p1_max and i2_max > i1_max:
        return 'BEAR_HIDDEN'
    return 'NONE'


def analyze(df: pd.DataFrame) -> dict:
    if len(df) < 30:
        return {'signal': 'NEUTRAL', 'strength': 0, 'confirmations': []}

    close = df['close']
    high = df['high']
    low = df['low']
    volume = df['volume']

    buy_strength = 0
    sell_strength = 0
    confirmations = []

    # ─── RSI ───────────────────────────────────────────────────────────────────
    try:
        rsi = ta.rsi(close, length=14)
        if rsi is not None and len(rsi) >= 2:
            rsi_curr = rsi.iloc[-1]
            rsi_prev = rsi.iloc[-2]

            if rsi_curr < 30:
                buy_strength += 4
                confirmations.append(f'RSI Oversold ({rsi_curr:.1f})')
            elif rsi_curr > 70:
                sell_strength += 4
                confirmations.append(f'RSI Overbought ({rsi_curr:.1f})')
            elif 30 <= rsi_curr <= 40 and rsi_curr > rsi_prev:
                buy_strength += 2
                confirmations.append('RSI Rising from 30-40 Zone')
            elif 60 <= rsi_curr <= 70 and rsi_curr < rsi_prev:
                sell_strength += 2
                confirmations.append('RSI Falling from 60-70 Zone')

            if rsi_prev <= 50 and rsi_curr > 50:
                buy_strength += 2
                confirmations.append('RSI Crossed 50 Upward')
            elif rsi_prev >= 50 and rsi_curr < 50:
                sell_strength += 2
                confirmations.append('RSI Crossed 50 Downward')

            # RSI divergence
            if len(rsi) >= 20:
                div = _find_divergence(close.values[-20:], rsi.values[-20:])
                if div == 'BULL_DIVERGENCE':
                    buy_strength += 5
                    confirmations.append('RSI Bullish Divergence')
                elif div == 'BEAR_DIVERGENCE':
                    sell_strength += 5
                    confirmations.append('RSI Bearish Divergence')
                elif div == 'BULL_HIDDEN':
                    buy_strength += 3
                    confirmations.append('RSI Hidden Bullish Divergence')
                elif div == 'BEAR_HIDDEN':
                    sell_strength += 3
                    confirmations.append('RSI Hidden Bearish Divergence')
    except Exception:
        pass

    # ─── MACD ──────────────────────────────────────────────────────────────────
    try:
        macd_df = ta.macd(close, fast=12, slow=26, signal=9)
        if macd_df is not None and not macd_df.empty and len(macd_df) >= 2:
            macd_col = [c for c in macd_df.columns if c.startswith('MACD_') and 'h' not in c.lower() and 's' not in c.lower()]
            sig_col = [c for c in macd_df.columns if 'MACDs_' in c]
            hist_col = [c for c in macd_df.columns if 'MACDh_' in c]

            if macd_col and sig_col and hist_col:
                macd_curr = macd_df[macd_col[0]].iloc[-1]
                macd_prev = macd_df[macd_col[0]].iloc[-2]
                sig_curr = macd_df[sig_col[0]].iloc[-1]
                sig_prev = macd_df[sig_col[0]].iloc[-2]
                hist_curr = macd_df[hist_col[0]].iloc[-1]
                hist_prev = macd_df[hist_col[0]].iloc[-2]

                if macd_prev <= sig_prev and macd_curr > sig_curr:
                    buy_strength += 4
                    confirmations.append('MACD Bullish Crossover')
                elif macd_prev >= sig_prev and macd_curr < sig_curr:
                    sell_strength += 4
                    confirmations.append('MACD Bearish Crossover')

                if hist_prev <= 0 and hist_curr > 0:
                    buy_strength += 3
                    confirmations.append('MACD Histogram Turned Positive')
                elif hist_prev >= 0 and hist_curr < 0:
                    sell_strength += 3
                    confirmations.append('MACD Histogram Turned Negative')
    except Exception:
        pass

    # ─── Stochastic ────────────────────────────────────────────────────────────
    try:
        stoch_df = ta.stoch(high, low, close, k=14, d=3, smooth_k=3)
        if stoch_df is not None and not stoch_df.empty and len(stoch_df) >= 2:
            k_col = [c for c in stoch_df.columns if 'STOCHk' in c]
            d_col = [c for c in stoch_df.columns if 'STOCHd' in c]

            if k_col and d_col:
                k_curr = stoch_df[k_col[0]].iloc[-1]
                k_prev = stoch_df[k_col[0]].iloc[-2]
                d_curr = stoch_df[d_col[0]].iloc[-1]
                d_prev = stoch_df[d_col[0]].iloc[-2]

                if k_curr < 20 and d_curr < 20 and k_prev <= d_prev and k_curr > d_curr:
                    buy_strength += 4
                    confirmations.append('Stochastic Oversold Bullish Cross')
                elif k_curr > 80 and d_curr > 80 and k_prev >= d_prev and k_curr < d_curr:
                    sell_strength += 4
                    confirmations.append('Stochastic Overbought Bearish Cross')

                if len(stoch_df) >= 20:
                    stoch_k = stoch_df[k_col[0]].values[-20:]
                    div = _find_divergence(close.values[-20:], stoch_k)
                    if div == 'BULL_DIVERGENCE':
                        buy_strength += 3
                        confirmations.append('Stochastic Bullish Divergence')
                    elif div == 'BEAR_DIVERGENCE':
                        sell_strength += 3
                        confirmations.append('Stochastic Bearish Divergence')
    except Exception:
        pass

    # ─── CCI ───────────────────────────────────────────────────────────────────
    try:
        cci = ta.cci(high, low, close, length=20)
        if cci is not None and len(cci) >= 2:
            cci_curr = cci.iloc[-1]
            cci_prev = cci.iloc[-2]

            if cci_prev <= -100 and cci_curr > -100:
                buy_strength += 3
                confirmations.append(f'CCI Crossed Above -100 ({cci_curr:.1f})')
            elif cci_prev >= 100 and cci_curr < 100:
                sell_strength += 3
                confirmations.append(f'CCI Crossed Below +100 ({cci_curr:.1f})')

            if len(cci) >= 20:
                div = _find_divergence(close.values[-20:], cci.values[-20:])
                if div == 'BULL_DIVERGENCE':
                    buy_strength += 3
                    confirmations.append('CCI Bullish Divergence')
                elif div == 'BEAR_DIVERGENCE':
                    sell_strength += 3
                    confirmations.append('CCI Bearish Divergence')
    except Exception:
        pass

    # ─── Williams %R ───────────────────────────────────────────────────────────
    try:
        willr = ta.willr(high, low, close, length=14)
        if willr is not None and len(willr) >= 1:
            wr_curr = willr.iloc[-1]
            if wr_curr < -80:
                buy_strength += 2
                confirmations.append(f'Williams %R Oversold ({wr_curr:.1f})')
            elif wr_curr > -20:
                sell_strength += 2
                confirmations.append(f'Williams %R Overbought ({wr_curr:.1f})')
    except Exception:
        pass

    # ─── ROC ───────────────────────────────────────────────────────────────────
    try:
        roc = ta.roc(close, length=12)
        if roc is not None and len(roc) >= 2:
            roc_curr = roc.iloc[-1]
            roc_prev = roc.iloc[-2]
            if roc_prev <= 0 and roc_curr > 0:
                buy_strength += 2
                confirmations.append('ROC Turned Positive')
            elif roc_prev >= 0 and roc_curr < 0:
                sell_strength += 2
                confirmations.append('ROC Turned Negative')
    except Exception:
        pass

    # ─── MFI ───────────────────────────────────────────────────────────────────
    try:
        mfi = ta.mfi(high, low, close, volume, length=14)
        if mfi is not None and len(mfi) >= 1:
            mfi_curr = mfi.iloc[-1]
            if mfi_curr < 20:
                buy_strength += 3
                confirmations.append(f'MFI Oversold ({mfi_curr:.1f})')
            elif mfi_curr > 80:
                sell_strength += 3
                confirmations.append(f'MFI Overbought ({mfi_curr:.1f})')
    except Exception:
        pass

    # ─── TSI ───────────────────────────────────────────────────────────────────
    try:
        tsi_df = ta.tsi(close)
        if tsi_df is not None and not tsi_df.empty and len(tsi_df) >= 2:
            tsi_col = [c for c in tsi_df.columns if c.startswith('TSI_')]
            sig_col = [c for c in tsi_df.columns if 'TSIs_' in c]
            if tsi_col and sig_col:
                tsi_curr = tsi_df[tsi_col[0]].iloc[-1]
                tsi_prev = tsi_df[tsi_col[0]].iloc[-2]
                sig_curr = tsi_df[sig_col[0]].iloc[-1]
                sig_prev = tsi_df[sig_col[0]].iloc[-2]

                if tsi_prev <= sig_prev and tsi_curr > sig_curr:
                    buy_strength += 2
                    confirmations.append('TSI Bullish Signal Cross')
                elif tsi_prev >= sig_prev and tsi_curr < sig_curr:
                    sell_strength += 2
                    confirmations.append('TSI Bearish Signal Cross')
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
