import pandas as pd
import numpy as np
import pandas_ta as ta
from typing import Optional


def calculate(
    df: pd.DataFrame,
    signal_type: str,
    entry_price: float,
    support_levels: Optional[list] = None,
    account_balance: float = 500000,
    max_risk_pct: float = 0.01,
    max_capital_pct: float = 0.20,
) -> dict:
    if df is None or len(df) < 15:
        return {}

    close = df['close']
    high = df['high']
    low = df['low']

    # ATR 14
    atr_series = ta.atr(high, low, close, length=14)
    atr_val = float(atr_series.iloc[-1]) if atr_series is not None and len(atr_series) > 0 and not np.isnan(atr_series.iloc[-1]) else entry_price * 0.01

    # Stop loss calculation
    atr_stop_distance = atr_val * 1.5

    if signal_type == 'BUY':
        atr_stop = entry_price - atr_stop_distance
        # Check nearest support level below entry
        if support_levels:
            valid_supports = [s for s in support_levels if s < entry_price]
            if valid_supports:
                nearest_support = max(valid_supports)
                # Use whichever is closer to entry (tighter stop)
                support_stop = nearest_support * 0.998  # small buffer below support
                atr_stop = max(atr_stop, support_stop)  # max = closer to entry = tighter
        stop_loss = round(atr_stop, 2)
        risk_per_share = entry_price - stop_loss
    else:  # SELL
        atr_stop = entry_price + atr_stop_distance
        if support_levels:
            valid_resistances = [s for s in support_levels if s > entry_price]
            if valid_resistances:
                nearest_resistance = min(valid_resistances)
                resistance_stop = nearest_resistance * 1.002
                atr_stop = min(atr_stop, resistance_stop)  # min = closer to entry = tighter
        stop_loss = round(atr_stop, 2)
        risk_per_share = stop_loss - entry_price

    if risk_per_share <= 0:
        risk_per_share = atr_val

    # Targets at R multiples
    if signal_type == 'BUY':
        t1 = round(entry_price + risk_per_share * 1.5, 2)
        t2 = round(entry_price + risk_per_share * 2.5, 2)
        t3 = round(entry_price + risk_per_share * 4.0, 2)

        # Fibonacci extensions from swing
        lookback = min(50, len(df))
        swing_low = low.iloc[-lookback:].min()
        swing_high = high.iloc[-lookback:].max()
        diff = swing_high - swing_low
        t4 = round(swing_low + diff * 1.272, 2)
        t5 = round(swing_low + diff * 1.618, 2)
    else:
        t1 = round(entry_price - risk_per_share * 1.5, 2)
        t2 = round(entry_price - risk_per_share * 2.5, 2)
        t3 = round(entry_price - risk_per_share * 4.0, 2)

        lookback = min(50, len(df))
        swing_low = low.iloc[-lookback:].min()
        swing_high = high.iloc[-lookback:].max()
        diff = swing_high - swing_low
        t4 = round(swing_high - diff * 1.272, 2)
        t5 = round(swing_high - diff * 1.618, 2)

    # Position sizing — risk-based (1 % of account by default)
    max_loss_amount = account_balance * max_risk_pct
    position_size   = int(max_loss_amount / risk_per_share) if risk_per_share > 0 else 0

    # Hard cap: never deploy more than max_capital_pct of account in one position.
    # Prevents a tiny risk_per_share (tight stop near support) from producing an
    # absurdly large position that dwarfs the account balance.
    if entry_price > 0:
        max_qty_by_capital = int(account_balance * max_capital_pct / entry_price)
        if max_qty_by_capital > 0:
            position_size = min(position_size, max_qty_by_capital)

    if position_size < 1:
        position_size = 1

    capital_required = round(position_size * entry_price, 2)

    # Risk-reward measured to T2 (2.5R target) — T1 is always 1.5R by definition
    # so using T1 here would always return 1.5, making the Gate 8 check useless.
    if signal_type == 'BUY':
        risk_reward = round((t2 - entry_price) / risk_per_share, 2)
    else:
        risk_reward = round((entry_price - t2) / risk_per_share, 2)

    stop_loss_pct = round(abs(entry_price - stop_loss) / entry_price * 100, 2)

    # Target percentages from entry
    def pct_change(target: float) -> float:
        if signal_type == 'BUY':
            return round((target - entry_price) / entry_price * 100, 2)
        else:
            return round((entry_price - target) / entry_price * 100, 2)

    return {
        'entryPrice': round(entry_price, 2),
        'stopLoss': stop_loss,
        'stopLossPercent': stop_loss_pct,
        'target1': t1,
        'target2': t2,
        'target3': t3,
        'target4': t4,
        'target5': t5,
        'target1Pct': pct_change(t1),
        'target2Pct': pct_change(t2),
        'target3Pct': pct_change(t3),
        'positionSize': position_size,
        'capitalRequired': capital_required,
        'maxLoss': round(max_loss_amount, 2),
        'riskReward': risk_reward,
        'atr': round(atr_val, 2),
        'riskPerShare': round(risk_per_share, 2)
    }
