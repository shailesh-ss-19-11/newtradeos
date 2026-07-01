import pandas as pd
import numpy as np
import pandas_ta as ta


def _calculate_vwap(df: pd.DataFrame) -> pd.Series:
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    if hasattr(df.index, 'tz') and df.index.tz is not None:
        date_str = df.index.strftime('%Y-%m-%d')
        vwap_series = pd.Series(index=df.index, dtype=float)
        for date in date_str.unique():
            mask = date_str == date
            day_df = df[mask]
            day_tp = typical_price[mask]
            day_vol = day_df['volume']
            cum_tp_vol = (day_tp * day_vol).cumsum()
            cum_vol = day_vol.cumsum()
            vwap_series[mask] = cum_tp_vol / cum_vol.replace(0, np.nan)
        return vwap_series
    else:
        cum_tp_vol = (typical_price * df['volume']).cumsum()
        cum_vol = df['volume'].cumsum()
        return cum_tp_vol / cum_vol.replace(0, np.nan)


def analyze(df: pd.DataFrame) -> dict:
    if len(df) < 25:
        return {'signal': 'NEUTRAL', 'strength': 0, 'confirmations': [], 'vol_ratio': 1.0}

    close = df['close']
    high = df['high']
    low = df['low']
    volume = df['volume']

    curr_close = close.iloc[-1]
    prev_close = close.iloc[-2]

    buy_strength = 0
    sell_strength = 0
    confirmations = []

    avg_vol_20 = volume.iloc[-20:].mean()
    curr_vol = volume.iloc[-1]
    vol_ratio = curr_vol / avg_vol_20 if avg_vol_20 > 0 else 1.0

    # ─── VWAP ──────────────────────────────────────────────────────────────────
    try:
        vwap_series = _calculate_vwap(df)
        vwap_curr = vwap_series.iloc[-1]
        vwap_prev = vwap_series.iloc[-2]

        atr_series = ta.atr(high, low, close, length=14)
        atr_val = atr_series.iloc[-1] if atr_series is not None and len(atr_series) > 0 else 0

        if prev_close <= vwap_prev and curr_close > vwap_curr:
            buy_strength += 4
            confirmations.append(f'VWAP Bullish Cross ({vwap_curr:.2f})')
        elif prev_close >= vwap_prev and curr_close < vwap_curr:
            sell_strength += 4
            confirmations.append(f'VWAP Bearish Cross ({vwap_curr:.2f})')
        elif curr_close > vwap_curr:
            buy_strength += 1
            confirmations.append('Price Above VWAP')
        else:
            sell_strength += 1
            confirmations.append('Price Below VWAP')

        if atr_val > 0:
            dist_from_vwap = abs(curr_close - vwap_curr)
            if dist_from_vwap > 1.5 * atr_val:
                if curr_close > vwap_curr and curr_close < vwap_curr + 2 * atr_val:
                    buy_strength += 2
                    confirmations.append('VWAP Mean Reversion Setup (Extended)')
                elif curr_close < vwap_curr:
                    sell_strength += 2
                    confirmations.append('VWAP Mean Reversion Setup (Extended)')
    except Exception:
        pass

    # ─── Volume Spike ──────────────────────────────────────────────────────────
    try:
        is_green = curr_close > prev_close
        if vol_ratio >= 3.0:
            if is_green:
                buy_strength += 5
                confirmations.append(f'Massive Volume Spike Bullish ({vol_ratio:.1f}x)')
            else:
                sell_strength += 5
                confirmations.append(f'Massive Volume Spike Bearish ({vol_ratio:.1f}x)')
        elif vol_ratio >= 1.5:
            if is_green:
                buy_strength += 2
                confirmations.append(f'Volume Surge Bullish ({vol_ratio:.1f}x)')
            else:
                sell_strength += 2
                confirmations.append(f'Volume Surge Bearish ({vol_ratio:.1f}x)')
    except Exception:
        pass

    # ─── OBV Divergence ────────────────────────────────────────────────────────
    try:
        obv = ta.obv(close, volume)
        if obv is not None and len(obv) >= 6:
            obv_curr = obv.iloc[-1]
            obv_5ago = obv.iloc[-6]
            close_5ago = close.iloc[-6]

            if curr_close < close_5ago and obv_curr > obv_5ago:
                buy_strength += 4
                confirmations.append('OBV Bullish Divergence (Price Down, OBV Up)')
            elif curr_close > close_5ago and obv_curr < obv_5ago:
                sell_strength += 4
                confirmations.append('OBV Bearish Divergence (Price Up, OBV Down)')
    except Exception:
        pass

    # ─── CMF ───────────────────────────────────────────────────────────────────
    try:
        cmf = ta.cmf(high, low, close, volume, length=20)
        if cmf is not None and len(cmf) >= 2:
            cmf_curr = cmf.iloc[-1]
            cmf_prev = cmf.iloc[-2]

            if cmf_curr > 0.1:
                buy_strength += 2
                confirmations.append(f'CMF Bullish ({cmf_curr:.3f})')
            elif cmf_curr < -0.1:
                sell_strength += 2
                confirmations.append(f'CMF Bearish ({cmf_curr:.3f})')

            if cmf_prev <= 0 and cmf_curr > 0:
                buy_strength += 3
                confirmations.append('CMF Zero Cross Bullish')
            elif cmf_prev >= 0 and cmf_curr < 0:
                sell_strength += 3
                confirmations.append('CMF Zero Cross Bearish')
    except Exception:
        pass

    # ─── Accumulation/Distribution Line ────────────────────────────────────────
    try:
        ad = ta.ad(high, low, close, volume)
        if ad is not None and len(ad) >= 6:
            ad_curr = ad.iloc[-1]
            ad_prev = ad.iloc[-6]
            close_5ago = close.iloc[-6]

            if ad_curr > ad_prev and abs(curr_close - close_5ago) / close_5ago < 0.005:
                buy_strength += 2
                confirmations.append('Accumulation Detected (A/D Rising, Price Flat)')
            elif ad_curr < ad_prev and abs(curr_close - close_5ago) / close_5ago < 0.005:
                sell_strength += 2
                confirmations.append('Distribution Detected (A/D Falling, Price Flat)')
    except Exception:
        pass

    # ─── Volume Profile HVN ────────────────────────────────────────────────────
    try:
        lookback = min(50, len(df))
        subset = df.iloc[-lookback:]
        price_range = subset['high'].max() - subset['low'].min()
        if price_range > 0:
            n_bins = 20
            bin_size = price_range / n_bins
            bin_volumes = {}
            for _, row in subset.iterrows():
                bin_idx = int((row['close'] - subset['low'].min()) / bin_size)
                bin_volumes[bin_idx] = bin_volumes.get(bin_idx, 0) + row['volume']

            if bin_volumes:
                hvn_bin = max(bin_volumes, key=bin_volumes.get)
                hvn_price = subset['low'].min() + hvn_bin * bin_size + bin_size / 2

                if abs(curr_close - hvn_price) / curr_close < 0.005:
                    if curr_close > hvn_price:
                        buy_strength += 2
                        confirmations.append(f'Price at HVN Support ({hvn_price:.2f})')
                    else:
                        sell_strength += 2
                        confirmations.append(f'Price at HVN Resistance ({hvn_price:.2f})')
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
        'vol_ratio': round(vol_ratio, 2)
    }
