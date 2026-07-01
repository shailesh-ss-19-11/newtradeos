import pandas as pd
import numpy as np
from typing import Optional


def _candle_metrics(row: pd.Series) -> dict:
    o, h, l, c = row['open'], row['high'], row['low'], row['close']
    body = abs(c - o)
    upper_wick = h - max(c, o)
    lower_wick = min(c, o) - l
    total_range = h - l
    return {
        'o': o, 'h': h, 'l': l, 'c': c,
        'body': body,
        'upper_wick': upper_wick,
        'lower_wick': lower_wick,
        'total_range': total_range,
        'is_green': c > o,
        'is_red': c < o,
        'mid_body': (max(c, o) + min(c, o)) / 2
    }


def analyze(df: pd.DataFrame) -> dict:
    if len(df) < 14:
        return {'signal': 'NEUTRAL', 'strength': 0, 'patterns': []}

    c1m = _candle_metrics(df.iloc[-3])
    c2m = _candle_metrics(df.iloc[-2])
    c3m = _candle_metrics(df.iloc[-1])

    closes = df['close'].values
    avg_body = float(np.mean(np.abs(df['close'].values[-14:] - df['open'].values[-14:])))
    if avg_body == 0:
        avg_body = 1e-9

    patterns = []

    def add(name: str, sig: str, strength: int) -> None:
        patterns.append({'name': name, 'signal': sig, 'strength': strength})

    # ─── SINGLE CANDLE PATTERNS (c3) ───────────────────────────────────────────

    r3 = c3m['total_range']
    b3 = c3m['body']
    uw3 = c3m['upper_wick']
    lw3 = c3m['lower_wick']

    if r3 > 0:
        is_doji = b3 < 0.10 * r3
        is_ll_doji = b3 < 0.05 * r3 and uw3 > 0.30 * r3 and lw3 > 0.30 * r3

        if is_ll_doji:
            add('Long-legged Doji', 'NEUTRAL', 1)
        elif is_doji:
            add('Doji', 'NEUTRAL', 1)

        is_dragonfly_doji = b3 < 0.05 * r3 and lw3 > 0.60 * r3 and uw3 < 0.05 * r3
        if is_dragonfly_doji:
            add('Dragonfly Doji', 'BUY', 2)

        is_gravestone_doji = b3 < 0.05 * r3 and uw3 > 0.60 * r3 and lw3 < 0.05 * r3
        if is_gravestone_doji:
            add('Gravestone Doji', 'SELL', 2)

        last5_descending = all(closes[-(i+1)] < closes[-(i+2)] for i in range(4))
        last5_ascending = all(closes[-(i+1)] > closes[-(i+2)] for i in range(4))

        is_hammer = (lw3 >= 2 * b3 and uw3 <= 0.3 * b3 and b3 > 0)
        if is_hammer and last5_descending:
            add('Hammer', 'BUY', 3)
        if is_hammer and last5_ascending:
            add('Hanging Man', 'SELL', 3)

        is_shooting_star = (uw3 >= 2 * b3 and lw3 <= 0.3 * b3)
        if is_shooting_star and last5_ascending:
            add('Shooting Star', 'SELL', 3)

        is_inv_hammer = (uw3 >= 2 * b3 and lw3 <= 0.3 * b3)
        if is_inv_hammer and last5_descending:
            add('Inverted Hammer', 'BUY', 2)

        is_bull_marubozu = c3m['is_green'] and uw3 < 0.02 * b3 and lw3 < 0.02 * b3 and b3 > 1.5 * avg_body
        if is_bull_marubozu:
            add('Bullish Marubozu', 'BUY', 4)

        is_bear_marubozu = c3m['is_red'] and uw3 < 0.02 * b3 and lw3 < 0.02 * b3 and b3 > 1.5 * avg_body
        if is_bear_marubozu:
            add('Bearish Marubozu', 'SELL', 4)

        is_spinning_top = b3 < 0.30 * r3 and uw3 > 0.20 * r3 and lw3 > 0.20 * r3
        if is_spinning_top and not is_doji:
            add('Spinning Top', 'NEUTRAL', 1)

    # ─── TWO CANDLE PATTERNS (c2, c3) ──────────────────────────────────────────

    b2 = c2m['body']

    is_c2_bear_marubozu = c2m['is_red'] and c2m['upper_wick'] < 0.02 * b2 and c2m['lower_wick'] < 0.02 * b2 and b2 > 1.5 * avg_body if b2 > 0 else False
    is_c2_bull_marubozu = c2m['is_green'] and c2m['upper_wick'] < 0.02 * b2 and c2m['lower_wick'] < 0.02 * b2 and b2 > 1.5 * avg_body if b2 > 0 else False

    bull_engulf = (c2m['is_red'] and c3m['is_green']
                   and c3m['o'] <= c2m['c'] and c3m['c'] >= c2m['o']
                   and b3 > b2)
    if bull_engulf:
        add('Bullish Engulfing', 'BUY', 4)

    bear_engulf = (c2m['is_green'] and c3m['is_red']
                   and c3m['o'] >= c2m['c'] and c3m['c'] <= c2m['o']
                   and b3 > b2)
    if bear_engulf:
        add('Bearish Engulfing', 'SELL', 4)

    if (c2m['is_red'] and c3m['is_green']
            and c3m['o'] < c2m['c']
            and c3m['c'] > c2m['mid_body'] and c3m['c'] < c2m['o']):
        add('Piercing Line', 'BUY', 3)

    if (c2m['is_green'] and c3m['is_red']
            and c3m['o'] > c2m['h']
            and c3m['c'] < c2m['mid_body'] and c3m['c'] > c2m['o']):
        add('Dark Cloud Cover', 'SELL', 3)

    bull_harami = (b2 > avg_body and c2m['is_red'] and c3m['is_green']
                   and c3m['o'] > c2m['c'] and c3m['c'] < c2m['o']
                   and b3 < 0.5 * b2)
    if bull_harami:
        add('Bullish Harami', 'BUY', 2)

    bear_harami = (b2 > avg_body and c2m['is_green'] and c3m['is_red']
                   and c3m['o'] < c2m['c'] and c3m['c'] > c2m['o']
                   and b3 < 0.5 * b2)
    if bear_harami:
        add('Bearish Harami', 'SELL', 2)

    if c3m['c'] > 0 and abs(c2m['l'] - c3m['l']) / c3m['c'] < 0.001 and c2m['is_red'] and c3m['is_green']:
        add('Tweezer Bottom', 'BUY', 3)

    if c3m['c'] > 0 and abs(c2m['h'] - c3m['h']) / c3m['c'] < 0.001 and c2m['is_green'] and c3m['is_red']:
        add('Tweezer Top', 'SELL', 3)

    if c2m['is_red'] and c3m['is_green'] and c3m['c'] > 0 and abs(c3m['c'] - c2m['c']) / c3m['c'] < 0.001:
        add('On Neck', 'SELL', 2)

    if is_c2_bear_marubozu and (b3 < 0.02 * b3 if b3 > 0 else False):
        pass
    kicking_bull = is_c2_bear_marubozu and c3m['is_green'] and c3m['o'] > c2m['o']
    if kicking_bull:
        add('Kicking Bullish', 'BUY', 5)

    kicking_bear = is_c2_bull_marubozu and c3m['is_red'] and c3m['o'] < c2m['o']
    if kicking_bear:
        add('Kicking Bearish', 'SELL', 5)

    # ─── THREE CANDLE PATTERNS (c1, c2, c3) ────────────────────────────────────

    b1 = c1m['body']

    morning_star = (b1 > avg_body and c1m['is_red']
                    and b2 < 0.30 * b1
                    and c3m['is_green'] and b3 > avg_body
                    and c3m['c'] > c1m['mid_body'])
    if morning_star:
        add('Morning Star', 'BUY', 5)

    evening_star = (b1 > avg_body and c1m['is_green']
                    and b2 < 0.30 * b1
                    and c3m['is_red'] and b3 > avg_body
                    and c3m['c'] < c1m['mid_body'])
    if evening_star:
        add('Evening Star', 'SELL', 5)

    is_c2_doji = b2 < 0.10 * c2m['total_range'] if c2m['total_range'] > 0 else False

    if b1 > avg_body and c1m['is_red'] and is_c2_doji and c3m['is_green'] and b3 > avg_body:
        add('Morning Doji Star', 'BUY', 5)

    if b1 > avg_body and c1m['is_green'] and is_c2_doji and c3m['is_red'] and b3 > avg_body:
        add('Evening Doji Star', 'SELL', 5)

    three_white = (c1m['is_green'] and c2m['is_green'] and c3m['is_green']
                   and c2m['c'] > c1m['c'] and c3m['c'] > c2m['c']
                   and c2m['o'] >= c1m['o'] and c2m['o'] <= c1m['c']
                   and c3m['o'] >= c2m['o'] and c3m['o'] <= c2m['c']
                   and b1 > avg_body and b2 > avg_body and b3 > avg_body)
    if three_white:
        add('Three White Soldiers', 'BUY', 5)

    three_black = (c1m['is_red'] and c2m['is_red'] and c3m['is_red']
                   and c2m['c'] < c1m['c'] and c3m['c'] < c2m['c']
                   and c2m['o'] <= c1m['o'] and c2m['o'] >= c1m['c']
                   and c3m['o'] <= c2m['o'] and c3m['o'] >= c2m['c']
                   and b1 > avg_body and b2 > avg_body and b3 > avg_body)
    if three_black:
        add('Three Black Crows', 'SELL', 5)

    c2_bull_harami_inside_c1 = (b1 > avg_body and c1m['is_red'] and c2m['is_green']
                                 and c2m['o'] > c1m['c'] and c2m['c'] < c1m['o']
                                 and b2 < 0.5 * b1)
    if c2_bull_harami_inside_c1 and c3m['is_green'] and c3m['c'] > c1m['o']:
        add('Three Inside Up', 'BUY', 4)

    c2_bear_harami_inside_c1 = (b1 > avg_body and c1m['is_green'] and c2m['is_red']
                                 and c2m['o'] < c1m['c'] and c2m['c'] > c1m['o']
                                 and b2 < 0.5 * b1)
    if c2_bear_harami_inside_c1 and c3m['is_red'] and c3m['c'] < c1m['o']:
        add('Three Inside Down', 'SELL', 4)

    c2_bull_engulf_c1 = (c1m['is_red'] and c2m['is_green']
                          and c2m['o'] <= c1m['c'] and c2m['c'] >= c1m['o']
                          and b2 > b1)
    if c2_bull_engulf_c1 and c3m['is_green'] and c3m['c'] > c2m['c']:
        add('Three Outside Up', 'BUY', 4)

    c2_bear_engulf_c1 = (c1m['is_green'] and c2m['is_red']
                          and c2m['o'] >= c1m['c'] and c2m['c'] <= c1m['o']
                          and b2 > b1)
    if c2_bear_engulf_c1 and c3m['is_red']:
        add('Three Outside Down', 'SELL', 4)

    abandoned_baby_bull = (c1m['is_red'] and is_c2_doji
                            and c2m['h'] < c1m['l']
                            and c3m['is_green'] and c3m['l'] > c2m['h'])
    if abandoned_baby_bull:
        add('Abandoned Baby Bull', 'BUY', 5)

    abandoned_baby_bear = (c1m['is_green'] and is_c2_doji
                            and c2m['l'] > c1m['h']
                            and c3m['is_red'] and c3m['h'] < c2m['l'])
    if abandoned_baby_bear:
        add('Abandoned Baby Bear', 'SELL', 5)

    upside_tasuki = (c1m['is_green'] and c2m['is_green']
                     and c2m['l'] > c1m['h']
                     and c3m['is_red']
                     and c3m['o'] < c2m['c'] and c3m['o'] > c2m['o']
                     and c3m['c'] > c1m['h'] and c3m['c'] < c2m['o'])
    if upside_tasuki:
        add('Upside Tasuki Gap', 'BUY', 3)

    downside_tasuki = (c1m['is_red'] and c2m['is_red']
                       and c2m['h'] < c1m['l']
                       and c3m['is_green']
                       and c3m['o'] > c2m['o'] and c3m['o'] < c2m['c']
                       and c3m['c'] < c1m['l'] and c3m['c'] > c2m['c'])
    if downside_tasuki:
        add('Downside Tasuki Gap', 'SELL', 3)

    # ─── TALLY AND FINAL SIGNAL ────────────────────────────────────────────────

    buy_strength = sum(p['strength'] for p in patterns if p['signal'] == 'BUY')
    sell_strength = sum(p['strength'] for p in patterns if p['signal'] == 'SELL')

    if buy_strength >= 3 and buy_strength > sell_strength:
        signal = 'BUY'
        strength = buy_strength
    elif sell_strength >= 3 and sell_strength > buy_strength:
        signal = 'SELL'
        strength = sell_strength
    else:
        signal = 'NEUTRAL'
        strength = max(buy_strength, sell_strength)

    return {
        'signal': signal,
        'strength': strength,
        'buy_strength': buy_strength,
        'sell_strength': sell_strength,
        'patterns': patterns,
        'confirmations': [p['name'] for p in patterns if p['signal'] == signal]
    }
