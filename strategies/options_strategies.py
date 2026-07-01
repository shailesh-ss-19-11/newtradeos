import pandas as pd
import numpy as np
from typing import Optional
from datetime import datetime
import pytz

IST = pytz.timezone('Asia/Kolkata')

INDEX_KEYWORDS = ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'SENSEX']


def _is_index(symbol: str) -> bool:
    return any(kw in symbol.upper() for kw in INDEX_KEYWORDS)


def _is_expiry_day() -> bool:
    now = datetime.now(IST)
    return now.weekday() == 3  # Thursday


def analyze(df: pd.DataFrame, symbol: str, options_data: Optional[dict] = None) -> dict:
    if not _is_index(symbol):
        return {'signal': 'NEUTRAL', 'strength': 0, 'confirmations': [], 'applicable': False}

    if options_data is None:
        return {'signal': 'NEUTRAL', 'strength': 0, 'confirmations': [], 'applicable': True,
                'error': 'No options data available'}

    close = df['close']
    curr_close = close.iloc[-1]

    buy_strength = 0
    sell_strength = 0
    confirmations = []

    max_pain = options_data.get('max_pain', 0)
    pcr = options_data.get('pcr', 0)
    ce_resistance = options_data.get('ce_resistance')
    pe_support = options_data.get('pe_support')
    ce_chain = options_data.get('ce_chain', {})
    pe_chain = options_data.get('pe_chain', {})

    confidence_multiplier = 1.0

    # ─── Max Pain ──────────────────────────────────────────────────────────────
    if max_pain and curr_close:
        diff_from_mp = curr_close - max_pain
        threshold = 100 if 'NIFTY50' in symbol.upper() or ('NIFTY' in symbol.upper() and 'BANK' not in symbol.upper()) else 150

        if diff_from_mp > threshold:
            sell_strength += 2
            confirmations.append(f'Price {diff_from_mp:.0f}pts above Max Pain ({max_pain})')
        elif diff_from_mp < -threshold:
            buy_strength += 2
            confirmations.append(f'Price {abs(diff_from_mp):.0f}pts below Max Pain ({max_pain})')

        if _is_expiry_day() and abs(diff_from_mp) < threshold * 0.5:
            confidence_multiplier = 0.7
            confirmations.append('Expiry Day: Pin Risk — reduced confidence')

    # ─── PCR Signal ────────────────────────────────────────────────────────────
    if pcr:
        if pcr > 1.5:
            buy_strength += 3
            confirmations.append(f'High PCR = Excessive Puts = Contrarian BUY ({pcr:.2f})')
        elif pcr < 0.7:
            sell_strength += 3
            confirmations.append(f'Low PCR = Excessive Calls = Contrarian SELL ({pcr:.2f})')
        elif 1.2 < pcr <= 1.5:
            buy_strength += 1
            confirmations.append(f'Mildly Bullish PCR ({pcr:.2f})')

    # ─── CE OI Resistance ──────────────────────────────────────────────────────
    if ce_resistance and curr_close:
        dist = abs(curr_close - ce_resistance) / curr_close
        if dist < 0.005:
            sell_strength += 3
            confirmations.append(f'Approaching CE OI Wall (Max OI at {ce_resistance})')

    # ─── PE OI Support ─────────────────────────────────────────────────────────
    if pe_support and curr_close:
        dist = abs(curr_close - pe_support) / curr_close
        if dist < 0.005:
            buy_strength += 3
            confirmations.append(f'Approaching PE OI Support (Max OI at {pe_support})')

    # ─── OI Change Analysis ────────────────────────────────────────────────────
    if ce_chain:
        try:
            ce_oi_changes = [v.get('oi_change', 0) or 0 for v in ce_chain.values()]
            total_ce_oi_change = sum(ce_oi_changes)
            close_change = curr_close - df['close'].iloc[-2]

            if total_ce_oi_change > 0 and close_change < 0:
                sell_strength += 2
                confirmations.append('CE OI Increasing + Price Falling = Bearish')
        except Exception:
            pass

    if pe_chain:
        try:
            pe_oi_changes = [v.get('oi_change', 0) or 0 for v in pe_chain.values()]
            total_pe_oi_change = sum(pe_oi_changes)
            close_change = curr_close - df['close'].iloc[-2]

            if total_pe_oi_change > 0 and close_change > 0:
                buy_strength += 2
                confirmations.append('PE OI Increasing + Price Rising = Bullish')
        except Exception:
            pass

    # ─── IV Skew ───────────────────────────────────────────────────────────────
    try:
        atm_iv = options_data.get('atm_iv', 0)
        if ce_chain and pe_chain and curr_close:
            atm_strike = min(
                list(ce_chain.keys()) + list(pe_chain.keys()),
                key=lambda s: abs(s - curr_close)
            )
            ce_iv = ce_chain.get(atm_strike, {}).get('iv', 0) or 0
            pe_iv = pe_chain.get(atm_strike, {}).get('iv', 0) or 0

            if pe_iv > 0 and ce_iv > 0:
                iv_diff_pct = (pe_iv - ce_iv) / ce_iv
                if iv_diff_pct > 0.15:
                    sell_strength += 1
                    confirmations.append(f'PE IV Skew (PE:{pe_iv:.1f} vs CE:{ce_iv:.1f}) = Bearish Sentiment')
                elif iv_diff_pct < -0.15:
                    buy_strength += 1
                    confirmations.append(f'CE IV Skew = Bullish Sentiment')
    except Exception:
        pass

    # ─── Options Trade Suggestion ───────────────────────────────────────────────
    trade_suggestion = None
    if curr_close:
        try:
            strikes = sorted(ce_chain.keys()) if ce_chain else []
            if strikes:
                atm_strike = min(strikes, key=lambda s: abs(s - curr_close))
                atm_idx = strikes.index(atm_strike)

                lot_size = _get_lot_size(symbol)

                if buy_strength > sell_strength:
                    otm_strike = strikes[min(atm_idx + 1, len(strikes) - 1)]
                    atm_premium = ce_chain.get(atm_strike, {}).get('ltp', 0)
                    otm_premium = ce_chain.get(otm_strike, {}).get('ltp', 0)
                    trade_suggestion = {
                        'direction': 'BUY',
                        'option_type': 'CE',
                        'atm_strike': atm_strike,
                        'atm_premium': atm_premium,
                        'otm_strike': otm_strike,
                        'otm_premium': otm_premium,
                        'lot_size': lot_size,
                        'recommendation': f'Buy {atm_strike}CE @ {atm_premium} or {otm_strike}CE @ {otm_premium}'
                    }
                elif sell_strength > buy_strength:
                    pe_strikes = sorted(pe_chain.keys())
                    atm_strike_pe = min(pe_strikes, key=lambda s: abs(s - curr_close))
                    atm_idx_pe = pe_strikes.index(atm_strike_pe)
                    otm_strike = pe_strikes[max(atm_idx_pe - 1, 0)]
                    atm_premium = pe_chain.get(atm_strike_pe, {}).get('ltp', 0)
                    otm_premium = pe_chain.get(otm_strike, {}).get('ltp', 0)
                    trade_suggestion = {
                        'direction': 'SELL',
                        'option_type': 'PE',
                        'atm_strike': atm_strike_pe,
                        'atm_premium': atm_premium,
                        'otm_strike': otm_strike,
                        'otm_premium': otm_premium,
                        'lot_size': lot_size,
                        'recommendation': f'Buy {atm_strike_pe}PE @ {atm_premium} or {otm_strike}PE @ {otm_premium}'
                    }
        except Exception:
            pass

    # ─── Final signal ──────────────────────────────────────────────────────────
    eff_buy = buy_strength * confidence_multiplier
    eff_sell = sell_strength * confidence_multiplier

    if eff_buy > eff_sell:
        signal = 'BUY'
        strength = buy_strength
    elif eff_sell > eff_buy:
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
        'applicable': True,
        'max_pain': max_pain,
        'pcr': pcr,
        'ce_resistance': ce_resistance,
        'pe_support': pe_support,
        'confidence_multiplier': confidence_multiplier,
        'trade_suggestion': trade_suggestion
    }


def _get_lot_size(symbol: str) -> int:
    sym_upper = symbol.upper()
    if 'NIFTYBANK' in sym_upper or 'BANKNIFTY' in sym_upper:
        return 30
    elif 'FINNIFTY' in sym_upper:
        return 65
    elif 'NIFTY' in sym_upper:
        return 75
    elif 'SENSEX' in sym_upper:
        return 20
    return 1
