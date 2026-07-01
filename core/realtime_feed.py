"""
Real-time market feed using Upstox REST polling.

The Upstox Analytics Token supports the Market Quote API, so we poll
/v2/market-quote/ltp every ~1 second instead of using a WebSocket.
This avoids the protobuf dependency required by the Upstox WebSocket v3 feed.

Public interface is identical to the previous Fyers-based version.
"""

import time
import threading
import requests
from datetime import datetime
import pytz

from auth.upstox_auth import get_upstox_headers, UPSTOX_BASE_URL
from core.upstox_instruments import fyers_to_upstox

IST = pytz.timezone("Asia/Kolkata")

_latest_ticks: dict = {}
_feed_instance = None

_POLL_INTERVAL = 1.5   # seconds between REST calls during market hours
_BATCH_SIZE    = 100   # max instrument keys per request


def _is_market_hours() -> bool:
    now = datetime.now(IST)
    # NSE market: Mon-Fri, 09:15 – 15:30 IST
    if now.weekday() >= 5:
        return False
    t = now.hour * 60 + now.minute
    return 555 <= t <= 930   # 09:15 = 555, 15:30 = 930


class RealtimeFeed:
    def __init__(self, symbols: list):
        self.symbols: list = list(symbols)
        self._running = False
        self._thread: threading.Thread | None = None

    # ── lifecycle ────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        print(f"[RealtimeFeed] REST polling started ({len(self.symbols)} symbols)")

    def stop(self) -> None:
        self._running = False
        print("[RealtimeFeed] Stopped")

    # ── polling ──────────────────────────────────────────────────────────────

    def _poll_loop(self) -> None:
        while self._running:
            try:
                if not _is_market_hours():
                    time.sleep(60)
                    continue
                self._fetch_batch(self.symbols)
            except Exception as e:
                print(f"[RealtimeFeed] Poll error: {e}")
            time.sleep(_POLL_INTERVAL)

    def _fetch_batch(self, symbols: list) -> None:
        headers = get_upstox_headers()
        if not headers:
            return

        # Build instrument_key list and reverse map
        ik_list: list[str] = []
        ik_to_sym: dict[str, str] = {}
        for sym in symbols:
            ik = fyers_to_upstox(sym)
            if ik:
                ik_list.append(ik)
                ik_to_sym[ik] = sym

        if not ik_list:
            return

        # Process in batches to stay within URL-length limits
        for i in range(0, len(ik_list), _BATCH_SIZE):
            batch = ik_list[i : i + _BATCH_SIZE]
            try:
                resp = requests.get(
                    f"{UPSTOX_BASE_URL}/v2/market-quote/quotes",
                    headers=headers,
                    params={"instrument_key": ",".join(batch)},
                    timeout=5,
                )
                if resp.status_code != 200:
                    continue

                data = resp.json().get("data", {})
                for ik in batch:
                    item = data.get(ik) or data.get(ik.replace("|", ":"))
                    if not item:
                        continue
                    sym  = ik_to_sym[ik]
                    ohlc = item.get("ohlc", {})
                    depth = item.get("depth", {})
                    best_bid = (depth.get("buy",  [{}])[0].get("price", 0)
                                if depth.get("buy")  else 0)
                    best_ask = (depth.get("sell", [{}])[0].get("price", 0)
                                if depth.get("sell") else 0)
                    _latest_ticks[sym] = {
                        "ltp":       item.get("last_price",  0),
                        "open":      ohlc.get("open",        0),
                        "high":      ohlc.get("high",        0),
                        "low":       ohlc.get("low",         0),
                        "close":     ohlc.get("close",       0),
                        "volume":    item.get("volume",      0),
                        "oi":        item.get("oi",          0),
                        "bid":       best_bid,
                        "ask":       best_ask,
                        "change":    item.get("net_change",             0),
                        "changePct": item.get("net_change_percentage",  0),
                        "timestamp": datetime.now(IST).isoformat(),
                    }
            except Exception:
                pass

    # ── accessors ────────────────────────────────────────────────────────────

    def get_ltp(self, symbol: str) -> float:
        return _latest_ticks.get(symbol, {}).get("ltp", 0)

    def get_latest_data(self, symbol: str) -> dict:
        return _latest_ticks.get(symbol, {})

    def get_all_ticks(self) -> dict:
        return dict(_latest_ticks)

    def subscribe_symbols(self, new_symbols: list) -> None:
        for sym in new_symbols:
            if sym not in self.symbols:
                self.symbols.append(sym)


# ── module-level helpers (same interface as before) ───────────────────────────

def get_feed_instance(symbols: list = None) -> RealtimeFeed:
    global _feed_instance
    if _feed_instance is None and symbols:
        _feed_instance = RealtimeFeed(symbols)
    return _feed_instance


def get_ltp_from_feed(symbol: str) -> float:
    if _feed_instance:
        return _feed_instance.get_ltp(symbol)
    return 0
