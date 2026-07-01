"""
Upstox instrument master loader and symbol mapping.

Converts Fyers-format symbols (NSE:RELIANCE-EQ) to Upstox instrument keys
(NSE_EQ|INE002A01018) by downloading Upstox's NSE instrument master on startup
and caching it for 24 hours.
"""

import gzip
import json
import time
import threading
import requests

_cache: dict = {}          # trading_symbol.upper() → instrument_key
_cache_loaded = False
_cache_ts = 0.0
_cache_ttl = 86400         # 24 hours
_lock = threading.Lock()

_MASTER_URL = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"

# Hard-coded index mappings: bare name after stripping 'NSE:' and '-INDEX'
_INDEX_MAP: dict[str, str] = {
    "NIFTY50":        "NSE_INDEX|Nifty 50",
    "NIFTY":          "NSE_INDEX|Nifty 50",
    "BANKNIFTY":      "NSE_INDEX|Nifty Bank",
    "FINNIFTY":       "NSE_INDEX|Nifty Fin Service",
    "MIDCPNIFTY":     "NSE_INDEX|Nifty Midcap Select",
    "NIFTYMIDCAP50":  "NSE_INDEX|Nifty Midcap 50",
    "NIFTYIT":        "NSE_INDEX|Nifty IT",
    "NIFTYAUTO":      "NSE_INDEX|Nifty Auto",
    "NIFTYPHARMA":    "NSE_INDEX|Nifty Pharma",
    "NIFTYFMCG":      "NSE_INDEX|Nifty FMCG",
    "NIFTYREALTY":    "NSE_INDEX|Nifty Realty",
    "NIFTYMETAL":     "NSE_INDEX|Nifty Metal",
    "NIFTYENERGY":    "NSE_INDEX|Nifty Energy",
    "NIFTYINFRA":     "NSE_INDEX|Nifty Infrastructure",
    "NIFTY100":       "NSE_INDEX|Nifty 100",
    "NIFTY200":       "NSE_INDEX|Nifty 200",
    "NIFTY500":       "NSE_INDEX|Nifty 500",
    "NIFTYNEXT50":    "NSE_INDEX|Nifty Next 50",
    "SENSEX":         "BSE_INDEX|SENSEX",
}


def _load() -> None:
    global _cache, _cache_loaded, _cache_ts
    try:
        resp = requests.get(_MASTER_URL, timeout=30)
        resp.raise_for_status()
        instruments = json.loads(gzip.decompress(resp.content))
        new_cache: dict = {}
        for inst in instruments:
            seg = inst.get("segment", "")
            ts  = inst.get("trading_symbol", "")
            ik  = inst.get("instrument_key", "")
            if seg in ("NSE_EQ", "NSE_INDEX") and ts and ik:
                new_cache[ts.upper()] = ik
        with _lock:
            _cache.update(new_cache)
            _cache_loaded = True
            _cache_ts = time.time()
        print(f"[UpstoxInstruments] Loaded {len(_cache)} instruments")
    except Exception as e:
        print(f"[UpstoxInstruments] Failed to load master: {e}")


def _ensure_loaded() -> None:
    if not _cache_loaded or (time.time() - _cache_ts > _cache_ttl):
        _load()


def fyers_to_upstox(fyers_symbol: str) -> str | None:
    """
    Convert a Fyers-format symbol to an Upstox instrument_key.

    Examples:
      NSE:RELIANCE-EQ    → NSE_EQ|INE002A01018
      NSE:NIFTY50-INDEX  → NSE_INDEX|Nifty 50
      NSE:BANKNIFTY-INDEX → NSE_INDEX|Nifty Bank
    """
    sym = fyers_symbol.strip()

    # Strip exchange prefix (NSE:, BSE:, etc.)
    if ":" in sym:
        sym = sym.split(":", 1)[1]

    if sym.endswith("-INDEX"):
        base = sym[:-6].upper()
        return _INDEX_MAP.get(base)

    if sym.endswith("-EQ"):
        base = sym[:-3].upper()
    else:
        base = sym.upper()

    _ensure_loaded()
    with _lock:
        return _cache.get(base)


def instrument_key_for_symbol(trading_symbol: str) -> str | None:
    """Look up instrument_key by plain trading symbol (e.g. 'RELIANCE')."""
    _ensure_loaded()
    with _lock:
        return _cache.get(trading_symbol.upper())


# Pre-load in background so first data request is fast
threading.Thread(target=_load, daemon=True).start()
