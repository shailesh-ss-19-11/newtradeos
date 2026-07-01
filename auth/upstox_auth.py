import os
import requests
from dotenv import load_dotenv

load_dotenv()

UPSTOX_BASE_URL = "https://api.upstox.com"


def get_upstox_token() -> str | None:
    return os.getenv('UPSTOX_ANALYTICS_TOKEN')


def get_upstox_headers() -> dict:
    token = get_upstox_token()
    if not token:
        print("[UpstoxAuth] UPSTOX_ANALYTICS_TOKEN not set in .env")
        return {}
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }


def verify_upstox_token() -> bool:
    """Make a lightweight API call to confirm the token is valid and log the result."""
    headers = get_upstox_headers()
    if not headers:
        return False
    try:
        resp = requests.get(
            f"{UPSTOX_BASE_URL}/v2/market-quote/ltp",
            headers=headers,
            params={"instrument_key": "NSE_INDEX|Nifty 50"},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            ltp = (data.get("data", {}) or {}).get("NSE_INDEX:Nifty 50", {}).get("last_price", "n/a")
            print(f"[UpstoxAuth] Token valid — Nifty 50 LTP: {ltp}")
            return True
        print(f"[UpstoxAuth] Token rejected: HTTP {resp.status_code} — {resp.text[:300]}")
        return False
    except Exception as e:
        print(f"[UpstoxAuth] Token verification error: {e}")
        return False
