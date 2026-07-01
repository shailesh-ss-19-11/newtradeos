import pandas as pd
import numpy as np
import pandas_ta as ta
from datetime import datetime
import pytz

IST = pytz.timezone('Asia/Kolkata')


def analyze(df: pd.DataFrame) -> dict:
    if len(df) < 25:
        return {'signal': 'NEUTRAL', 'strength': 0, 'confirmations': []}

    close = df['close']
    high = df['high']
    low = df['low']
    volume = df['volume']

    buy_strength = 0
    sell_strength = 0
    confirmations = []

    curr_close = close.iloc[-1]
    avg_vol = volume.iloc[-20:].mean()

    # ─── Bollinger Bands ───────────────────────────────────────────────────────
    try:
        bb = ta.bbands(close, length=20, std=2)
        if bb is not None and not bb.empty:
            bbl_col = [c for c in bb.columns if c.startswith('BBL_')]
            bbm_col = [c for c in bb.columns if c.startswith('BBM_')]
            bbu_col = [c for c in bb.columns if c.startswith('BBU_')]
            bbb_col = [c for c in bb.columns if c.startswith('BBB_')]
            bbp_col = [c for c in bb.columns if c.startswith('BBP_')]

            if bbl_col and bbu_col and bbb_col:
                bbl = bb[bbl_col[0]]
                bbu = bb[bbu_col[0]]
                bbm = bb[bbm_col[0]]
                bbb = bb[bbb_col[0]]

                bbl_curr = bbl.iloc[-1]
                bbu_curr = bbu.iloc[-1]
                bbm_curr = bbm.iloc[-1]
                bbb_curr = bbb.iloc[-1]
                bbb_avg = bbb.iloc[-20:].mean()

                is_squeeze = bbb_curr < 0.5 * bbb_avg

                if is_squeeze:
                    if curr_close > bbu_curr:
                        buy_strength += 5
                        confirmations.append('BB Squeeze Breakout Up')
                    elif curr_close < bbl_curr:
                        sell_strength += 5
                        confirmations.append('BB Squeeze Breakout Down')
                else:
                    if curr_close > bbu_curr:
                        buy_strength += 3
                        confirmations.append('BB Bounce Upper')
                    elif curr_close < bbl_curr:
                        buy_strength += 3
                        confirmations.append('BB Lower Band Bounce')

                prev_close = close.iloc[-2]
                if prev_close < bbm_curr <= curr_close:
                    buy_strength += 1
                    confirmations.append('BB Midline Cross Up')
                elif prev_close > bbm_curr >= curr_close:
                    sell_strength += 1
                    confirmations.append('BB Midline Cross Down')

                if bbp_col:
                    bbp_curr = bb[bbp_col[0]].iloc[-1]
                    bbp_prev = bb[bbp_col[0]].iloc[-2]
                    if bbp_curr < 0.05 and bbp_curr > bbp_prev:
                        buy_strength += 2
                        confirmations.append('BB %B Oversold Rising')
                    elif bbp_curr > 0.95 and bbp_curr < bbp_prev:
                        sell_strength += 2
                        confirmations.append('BB %B Overbought Falling')
    except Exception:
        pass

    # ─── Keltner Channel ───────────────────────────────────────────────────────
    try:
        kc = ta.kc(high, low, close)
        if kc is not None and not kc.empty:
            kcu_col = [c for c in kc.columns if 'KCUe' in c]
            kcl_col = [c for c in kc.columns if 'KCLe' in c]
            if kcu_col and kcl_col:
                kcu = kc[kcu_col[0]].iloc[-1]
                kcl = kc[kcl_col[0]].iloc[-1]
                kcu_prev = kc[kcu_col[0]].iloc[-2]
                kcl_prev = kc[kcl_col[0]].iloc[-2]
                prev_close = close.iloc[-2]

                if prev_close <= kcu_prev and curr_close > kcu:
                    buy_strength += 3
                    confirmations.append('Keltner Channel Breakout Up')
                elif prev_close >= kcl_prev and curr_close < kcl:
                    sell_strength += 3
                    confirmations.append('Keltner Channel Breakout Down')
    except Exception:
        pass

    # ─── Donchian Channel ──────────────────────────────────────────────────────
    try:
        dc = ta.donchian(high, low, length=20)
        if dc is not None and not dc.empty:
            dcu_col = [c for c in dc.columns if 'DCU_' in c]
            dcl_col = [c for c in dc.columns if 'DCL_' in c]
            if dcu_col and dcl_col:
                donch_high = high.iloc[-21:-1].max()
                donch_low = low.iloc[-21:-1].min()

                if curr_close > donch_high:
                    buy_strength += 4
                    confirmations.append('Donchian 20-period Breakout Up')
                elif curr_close < donch_low:
                    sell_strength += 4
                    confirmations.append('Donchian 20-period Breakout Down')
    except Exception:
        pass

    # ─── Opening Range Breakout ────────────────────────────────────────────────
    try:
        if hasattr(df.index, 'tz') and df.index.tz is not None:
            now_ist = datetime.now(IST)
            today_str = now_ist.strftime('%Y-%m-%d')

            today_mask = df.index.strftime('%Y-%m-%d') == today_str
            today_df = df[today_mask]

            if len(today_df) >= 2:
                first_candle = today_df.iloc[0]
                orb_high = first_candle['high']
                orb_low = first_candle['low']

                current_hour = now_ist.hour
                current_min = now_ist.minute
                within_orb_time = (current_hour == 9 and current_min < 75) or (current_hour == 10) or (current_hour == 11 and current_min < 15)

                if within_orb_time:
                    if curr_close > orb_high:
                        buy_strength += 4
                        confirmations.append(f'ORB Breakout Up (ORB High: {orb_high:.2f})')
                    elif curr_close < orb_low:
                        sell_strength += 4
                        confirmations.append(f'ORB Breakout Down (ORB Low: {orb_low:.2f})')
    except Exception:
        pass

    # ─── Previous Day High/Low ─────────────────────────────────────────────────
    try:
        if hasattr(df.index, 'tz') and df.index.tz is not None:
            today_str = datetime.now(IST).strftime('%Y-%m-%d')
            today_mask = df.index.strftime('%Y-%m-%d') == today_str
            prev_mask = ~today_mask
            prev_df = df[prev_mask]

            if len(prev_df) > 0:
                prev_day_dates = prev_df.index.strftime('%Y-%m-%d').unique()
                if len(prev_day_dates) >= 1:
                    last_prev_date = sorted(prev_day_dates)[-1]
                    prev_day_df = prev_df[prev_df.index.strftime('%Y-%m-%d') == last_prev_date]
                    pdh = prev_day_df['high'].max()
                    pdl = prev_day_df['low'].min()
                    pdc = prev_day_df['close'].iloc[-1]

                    if curr_close > pdh:
                        buy_strength += 3
                        confirmations.append(f'PDH Breakout ({pdh:.2f})')
                    elif curr_close < pdl:
                        sell_strength += 3
                        confirmations.append(f'PDL Breakdown ({pdl:.2f})')

                    if abs(curr_close - pdc) / pdc < 0.002:
                        prev_candle = close.iloc[-2]
                        if prev_candle < pdc <= curr_close:
                            buy_strength += 2
                            confirmations.append('PDC Retest Bullish')
                        elif prev_candle > pdc >= curr_close:
                            sell_strength += 2
                            confirmations.append('PDC Retest Bearish')
    except Exception:
        pass

    # ─── 52-week High Breakout ─────────────────────────────────────────────────
    try:
        if len(df) >= 252:
            week52_high = high.iloc[-252:].max()
            if abs(curr_close - week52_high) / week52_high < 0.005:
                vol_curr = volume.iloc[-1]
                if curr_close >= week52_high and vol_curr > 1.5 * avg_vol:
                    buy_strength += 4
                    confirmations.append(f'52-Week High Breakout (Vol: {vol_curr/avg_vol:.1f}x)')
    except Exception:
        pass

    # ─── Consolidation Breakout ────────────────────────────────────────────────
    try:
        recent = df.iloc[-10:]
        recent_range = recent['high'].max() - recent['low'].min()
        avg_range = (df['high'].iloc[-30:] - df['low'].iloc[-30:]).mean()

        if avg_range > 0 and recent_range < 0.30 * avg_range:
            box_high = recent['high'].max()
            box_low = recent['low'].min()
            if curr_close > box_high:
                buy_strength += 4
                confirmations.append(f'Consolidation Breakout Up (Box: {box_low:.2f}-{box_high:.2f})')
            elif curr_close < box_low:
                sell_strength += 4
                confirmations.append(f'Consolidation Breakout Down (Box: {box_low:.2f}-{box_high:.2f})')
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
