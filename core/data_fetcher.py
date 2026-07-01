"""
Data fetcher backed by the Upstox Analytics API.

Public interface is identical to the previous Fyers-based version so all
callers (backtester, routes, scanner) work without modification.
The `fyers` parameter is accepted but ignored everywhere.
"""

import time
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import pytz

from auth.upstox_auth import get_upstox_headers, UPSTOX_BASE_URL
from core.upstox_instruments import fyers_to_upstox

IST = pytz.timezone("Asia/Kolkata")

_cache: dict = {}
_CACHE_TTL_SECONDS = 240

# ─── Resolution helpers ───────────────────────────────────────────────────────

# Maps Fyers resolution codes to (upstox_interval, resample_to_minutes|None).
# None means no resampling needed.
_RESOLUTION_MAP: dict[str, tuple[str, int | None]] = {
    "1":   ("1minute",  1),
    "2":   ("1minute",  2),
    "3":   ("1minute",  3),
    "5":   ("1minute",  5),
    "10":  ("30minute", None),   # closest is 30min; use as-is
    "15":  ("30minute", None),   # approximate (Upstox has no 15min bar)
    "20":  ("30minute", None),
    "30":  ("30minute", None),
    "60":  ("30minute", 60),
    "120": ("30minute", 120),
    "240": ("30minute", 240),
    "D":   ("day",      None),
    "W":   ("week",     None),
    "M":   ("month",    None),
}

# Default look-back (days) per resolution when days_back is not specified
_RESOLUTION_DAYS: dict[str, int] = {
    "1": 7, "2": 7, "3": 10, "5": 15, "10": 20,
    "15": 30, "20": 30, "30": 45, "60": 90,
    "120": 120, "240": 180, "D": 365, "W": 730, "M": 1095,
}

# Upstox imposes a per-request date-range limit per interval
_INTERVAL_MAX_DAYS: dict[str, int] = {
    "1minute":  30,
    "30minute": 365,
    "day":      365,
    "week":     3650,
    "month":    3650,
}


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _fetch_candles_raw(instrument_key: str, upstox_interval: str,
                       from_date: str, to_date: str) -> list:
    """
    Fetch raw candle lists from Upstox, paginating over date-range limits.
    Returns a flat list of candles in ascending time order.
    """
    headers = get_upstox_headers()
    if not headers:
        return []

    enc_key = requests.utils.quote(instrument_key, safe="")
    max_days = _INTERVAL_MAX_DAYS.get(upstox_interval, 365)

    from_dt = datetime.strptime(from_date, "%Y-%m-%d")
    to_dt   = datetime.strptime(to_date,   "%Y-%m-%d")

    all_candles: list = []
    chunk_end = to_dt

    while chunk_end >= from_dt:
        chunk_start = max(from_dt, chunk_end - timedelta(days=max_days))
        url = (
            f"{UPSTOX_BASE_URL}/v2/historical-candle/{enc_key}"
            f"/{upstox_interval}"
            f"/{chunk_end.strftime('%Y-%m-%d')}"
            f"/{chunk_start.strftime('%Y-%m-%d')}"
        )
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                candles = resp.json().get("data", {}).get("candles", [])
                all_candles = candles + all_candles  # prepend so result stays ascending
            elif resp.status_code == 429:
                time.sleep(2)
        except Exception:
            pass

        chunk_end = chunk_start - timedelta(days=1)

    return all_candles


def _candles_to_df(candles: list) -> Optional[pd.DataFrame]:
    """
    Convert Upstox candle list to a timezone-aware DataFrame.
    Upstox format: [timestamp_str, open, high, low, close, volume, oi]
    """
    if not candles:
        return None

    rows = []
    for c in candles:
        try:
            ts = pd.to_datetime(c[0]).tz_convert("Asia/Kolkata")
            rows.append({
                "datetime": ts,
                "open":     float(c[1]),
                "high":     float(c[2]),
                "low":      float(c[3]),
                "close":    float(c[4]),
                "volume":   float(c[5]),
            })
        except Exception:
            continue

    if not rows:
        return None

    df = pd.DataFrame(rows).set_index("datetime")
    df = df[["open", "high", "low", "close", "volume"]].astype(float)
    df.sort_index(inplace=True)
    return df


def _resample(df: pd.DataFrame, minutes: int) -> pd.DataFrame:
    rule = f"{minutes}min"
    return (
        df.resample(rule, label="left", closed="left")
        .agg({"open": "first", "high": "max", "low": "min",
              "close": "last", "volume": "sum"})
        .dropna()
    )


# ─── Public API ───────────────────────────────────────────────────────────────

def fetch_historical(symbol: str, resolution: str,
                     days_back: Optional[int] = None,
                     fyers=None) -> Optional[pd.DataFrame]:
    """
    Fetch historical OHLCV from Upstox.
    `fyers` is accepted for backward-compatibility but ignored.
    """
    cache_key = f"{symbol}_{resolution}"
    now_ts = time.time()

    if cache_key in _cache:
        cached_df, cached_time = _cache[cache_key]
        if now_ts - cached_time < _CACHE_TTL_SECONDS:
            return cached_df

    instrument_key = fyers_to_upstox(symbol)
    if not instrument_key:
        return None

    if days_back is None:
        days_back = _RESOLUTION_DAYS.get(str(resolution), 30)

    now_ist  = datetime.now(IST)
    to_date  = now_ist.strftime("%Y-%m-%d")
    from_date = (now_ist - timedelta(days=days_back)).strftime("%Y-%m-%d")

    upstox_interval, resample_minutes = _RESOLUTION_MAP.get(str(resolution), ("day", None))

    raw = _fetch_candles_raw(instrument_key, upstox_interval, from_date, to_date)
    df  = _candles_to_df(raw)
    if df is None:
        return None

    # Resample where Upstox doesn't provide the requested granularity natively
    # e.g., 30min → 60min, 1min → 5min
    if resample_minutes is not None:
        base_min = 1 if upstox_interval == "1minute" else 30
        if resample_minutes != base_min:
            df = _resample(df, resample_minutes)

    _cache[cache_key] = (df, now_ts)
    return df


def fetch_quotes(symbols_list: list, fyers=None) -> dict:
    """
    Fetch live OHLCV quotes for a list of Fyers-format symbols.
    Returns a dict keyed by the original Fyers symbol.
    """
    if not symbols_list:
        return {}

    headers = get_upstox_headers()
    if not headers:
        return {}

    sym_to_ik: dict[str, str] = {}
    for sym in symbols_list:
        ik = fyers_to_upstox(sym)
        if ik:
            sym_to_ik[sym] = ik

    if not sym_to_ik:
        return {}

    ik_param = ",".join(sym_to_ik.values())
    try:
        resp = requests.get(
            f"{UPSTOX_BASE_URL}/v2/market-quote/quotes",
            headers=headers,
            params={"instrument_key": ik_param},
            timeout=10,
        )
        if resp.status_code != 200:
            return {}

        data = resp.json().get("data", {})
        result: dict = {}

        for sym, ik in sym_to_ik.items():
            # Upstox returns keys with ':' separator (NSE_EQ:INE002A01018)
            item = data.get(ik) or data.get(ik.replace("|", ":"))
            if not item:
                continue
            ohlc  = item.get("ohlc", {})
            depth = item.get("depth", {})
            best_bid = (depth.get("buy",  [{}])[0].get("price", 0)
                        if depth.get("buy")  else 0)
            best_ask = (depth.get("sell", [{}])[0].get("price", 0)
                        if depth.get("sell") else 0)
            result[sym] = {
                "ltp":       item.get("last_price",              0),
                "open":      ohlc.get("open",                    0),
                "high":      ohlc.get("high",                    0),
                "low":       ohlc.get("low",                     0),
                "close":     ohlc.get("close",                   0),
                "volume":    item.get("volume",                  0),
                "bid":       best_bid,
                "ask":       best_ask,
                "oi":        item.get("oi",                      0),
                "change":    item.get("net_change",              0),
                "changePct": item.get("net_change_percentage",   0),
            }

        return result

    except Exception as e:
        try:
            from core.db_storage import save_error
            save_error({"module": "data_fetcher.fetch_quotes", "message": str(e)})
        except Exception:
            pass
        return {}


def fetch_option_chain(underlying_symbol: str,
                       strike_count: int = 10,
                       fyers=None) -> Optional[dict]:
    """Fetch option chain data from Upstox for the nearest expiry."""
    headers = get_upstox_headers()
    if not headers:
        return None

    instrument_key = fyers_to_upstox(underlying_symbol)
    if not instrument_key:
        return None

    try:
        # Step 1: get available expiry dates
        expiry_resp = requests.get(
            f"{UPSTOX_BASE_URL}/v2/option/contract",
            headers=headers,
            params={"instrument_key": instrument_key},
            timeout=10,
        )
        if expiry_resp.status_code != 200:
            return None

        expiries = expiry_resp.json().get("data", [])
        if not expiries:
            return None

        today = datetime.now(IST).date()
        nearest = min(
            expiries,
            key=lambda e: abs(
                (datetime.strptime(e["expiry"], "%Y-%m-%d").date() - today).days
            ),
        )
        expiry_date = nearest["expiry"]

        # Step 2: fetch chain for nearest expiry
        chain_resp = requests.get(
            f"{UPSTOX_BASE_URL}/v2/option/chain",
            headers=headers,
            params={"instrument_key": instrument_key, "expiry_date": expiry_date},
            timeout=10,
        )
        if chain_resp.status_code != 200:
            return None

        ce_chain: dict = {}
        pe_chain: dict = {}
        total_ce_oi = 0
        total_pe_oi = 0

        for item in chain_resp.json().get("data", []):
            strike  = item.get("strike_price", 0)
            ce_data = item.get("call_options", {})
            pe_data = item.get("put_options",  {})
            ce_md   = ce_data.get("market_data",   {})
            pe_md   = pe_data.get("market_data",   {})
            ce_grk  = ce_data.get("option_greeks", {})
            pe_grk  = pe_data.get("option_greeks", {})

            ce_oi = ce_md.get("oi", 0) or 0
            pe_oi = pe_md.get("oi", 0) or 0
            total_ce_oi += ce_oi
            total_pe_oi += pe_oi

            ce_chain[strike] = {
                "ltp":      ce_md.get("ltp",    0),
                "oi":       ce_oi,
                "oi_change": ce_md.get("oi_day_high", 0) - ce_md.get("oi_day_low", 0),
                "iv":       ce_grk.get("iv",    0),
                "bid":      0,
                "ask":      0,
                "volume":   ce_md.get("volume", 0),
            }
            pe_chain[strike] = {
                "ltp":      pe_md.get("ltp",    0),
                "oi":       pe_oi,
                "oi_change": pe_md.get("oi_day_high", 0) - pe_md.get("oi_day_low", 0),
                "iv":       pe_grk.get("iv",    0),
                "bid":      0,
                "ask":      0,
                "volume":   pe_md.get("volume", 0),
            }

        pcr          = round(total_pe_oi / total_ce_oi, 4) if total_ce_oi else 0.0
        max_pain     = _calculate_max_pain(ce_chain, pe_chain)
        ce_resistance = max(ce_chain, key=lambda s: ce_chain[s]["oi"]) if ce_chain else None
        pe_support    = max(pe_chain, key=lambda s: pe_chain[s]["oi"]) if pe_chain else None

        return {
            "underlying":    underlying_symbol,
            "ce_chain":      ce_chain,
            "pe_chain":      pe_chain,
            "total_ce_oi":   total_ce_oi,
            "total_pe_oi":   total_pe_oi,
            "pcr":           pcr,
            "max_pain":      max_pain,
            "ce_resistance": ce_resistance,
            "pe_support":    pe_support,
            "atm_iv":        _get_atm_iv(ce_chain, pe_chain, 0),
            "expiry_date":   expiry_date,
        }

    except Exception as e:
        try:
            from core.db_storage import save_error
            save_error({"module": "data_fetcher.fetch_option_chain",
                        "message": str(e), "symbol": underlying_symbol})
        except Exception:
            pass
        return None


def fetch_market_depth(symbol: str, fyers=None) -> Optional[dict]:
    """Fetch full market depth (5-level order book) from Upstox."""
    headers = get_upstox_headers()
    if not headers:
        return None

    instrument_key = fyers_to_upstox(symbol)
    if not instrument_key:
        return None

    enc_key = requests.utils.quote(instrument_key, safe="")
    try:
        resp = requests.get(
            f"{UPSTOX_BASE_URL}/v2/market-quote/full/{enc_key}",
            headers=headers,
            timeout=10,
        )
        if resp.status_code != 200:
            return None
        return resp.json().get("data", {})
    except Exception:
        return None


def clear_cache(symbol: str = None, resolution: str = None) -> None:
    if symbol and resolution:
        _cache.pop(f"{symbol}_{resolution}", None)
    elif symbol:
        for k in [k for k in _cache if k.startswith(f"{symbol}_")]:
            del _cache[k]
    else:
        _cache.clear()


# ─── Option chain helpers (same logic as before) ─────────────────────────────

def _calculate_max_pain(ce_chain: dict, pe_chain: dict) -> float:
    strikes = sorted(set(list(ce_chain) + list(pe_chain)))
    if not strikes:
        return 0.0
    min_pain = float("inf")
    max_pain_strike = strikes[0]
    for exp in strikes:
        pain = sum(max(0, exp - s) * ce_chain[s]["oi"] for s in ce_chain)
        pain += sum(max(0, s - exp) * pe_chain[s]["oi"] for s in pe_chain)
        if pain < min_pain:
            min_pain = pain
            max_pain_strike = exp
    return max_pain_strike


def _get_atm_iv(ce_chain: dict, pe_chain: dict, spot_price: float) -> float:
    if not spot_price or not ce_chain:
        return 0.0
    atm = min(ce_chain, key=lambda s: abs(s - spot_price))
    ce_iv = ce_chain.get(atm, {}).get("iv", 0) or 0
    pe_iv = pe_chain.get(atm, {}).get("iv", 0) or 0
    return round((ce_iv + pe_iv) / 2, 2) if (ce_iv and pe_iv) else (ce_iv or pe_iv)
