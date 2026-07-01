"""
Correlation Guard — prevents adding a new position that is highly correlated
with an existing active position (avoids concentrated sector risk).

Uses a hardcoded sector/correlation map for common NSE stocks.
Returns True if trade is ALLOWED, False if blocked due to high correlation.
"""

# NSE sector buckets — stocks in same bucket are considered correlated
_SECTOR_MAP = {
    # Banking & Finance
    'HDFCBANK': 'BANK', 'ICICIBANK': 'BANK', 'KOTAKBANK': 'BANK',
    'AXISBANK': 'BANK', 'SBIN': 'BANK', 'INDUSINDBK': 'BANK',
    'BANDHANBNK': 'BANK', 'FEDERALBNK': 'BANK', 'IDFCFIRSTB': 'BANK',
    'BAJFINANCE': 'NBFC', 'BAJAJFINSV': 'NBFC', 'CHOLAFIN': 'NBFC',
    'MUTHOOTFIN': 'NBFC', 'HDFC': 'NBFC',

    # IT
    'TCS': 'IT', 'INFY': 'IT', 'WIPRO': 'IT', 'HCLTECH': 'IT',
    'TECHM': 'IT', 'LTIM': 'IT', 'MPHASIS': 'IT', 'PERSISTENT': 'IT',
    'COFORGE': 'IT',

    # Pharma
    'SUNPHARMA': 'PHARMA', 'DRREDDY': 'PHARMA', 'CIPLA': 'PHARMA',
    'DIVISLAB': 'PHARMA', 'BIOCON': 'PHARMA', 'AUROPHARMA': 'PHARMA',
    'TORNTPHARM': 'PHARMA',

    # FMCG
    'HINDUNILVR': 'FMCG', 'ITC': 'FMCG', 'NESTLEIND': 'FMCG',
    'BRITANNIA': 'FMCG', 'DABUR': 'FMCG', 'MARICO': 'FMCG',
    'GODREJCP': 'FMCG', 'COLPAL': 'FMCG',

    # Auto
    'MARUTI': 'AUTO', 'TATAMOTORS': 'AUTO', 'M&M': 'AUTO',
    'BAJAJ-AUTO': 'AUTO', 'HEROMOTOCO': 'AUTO', 'EICHERMOT': 'AUTO',
    'BOSCHLTD': 'AUTO', 'MOTHERSON': 'AUTO',

    # Metals & Mining
    'TATASTEEL': 'METALS', 'HINDALCO': 'METALS', 'JSWSTEEL': 'METALS',
    'VEDL': 'METALS', 'COALINDIA': 'METALS', 'NMDC': 'METALS',
    'SAIL': 'METALS',

    # Energy & Oil
    'RELIANCE': 'ENERGY', 'ONGC': 'ENERGY', 'IOC': 'ENERGY',
    'BPCL': 'ENERGY', 'GAIL': 'ENERGY', 'HINDPETRO': 'ENERGY',
    'POWERGRID': 'ENERGY', 'NTPC': 'ENERGY', 'ADANIPOWER': 'ENERGY',

    # Telecom
    'BHARTIARTL': 'TELECOM', 'IDEA': 'TELECOM',

    # Consumer/Retail
    'ASIANPAINT': 'CONSUMER', 'TITAN': 'CONSUMER',
    'DMART': 'CONSUMER', 'TRENT': 'CONSUMER',

    # Indices — always allowed (no sector conflict with equities)
    'NIFTY50': 'INDEX', 'NIFTYBANK': 'INDEX', 'FINNIFTY': 'INDEX', 'SENSEX': 'INDEX',
}

# Max positions per sector before blocking
_MAX_PER_SECTOR = 1


def _extract_ticker(symbol: str) -> str:
    """NSE:RELIANCE-EQ  →  RELIANCE"""
    s = symbol.upper()
    if ':' in s:
        s = s.split(':')[1]
    s = s.replace('-EQ', '').replace('-INDEX', '').replace('-BE', '')
    return s


def _get_sector(symbol: str) -> str:
    ticker = _extract_ticker(symbol)
    return _SECTOR_MAP.get(ticker, 'OTHER')


def is_allowed(new_symbol: str, active_trades: list) -> tuple:
    """
    Returns (allowed: bool, reason: str).
    Indices are always allowed.
    Equities blocked if same sector already has _MAX_PER_SECTOR active positions.
    """
    new_sector = _get_sector(new_symbol)

    # Indices never blocked by correlation
    if new_sector == 'INDEX':
        return True, 'INDEX — no correlation check'

    # Unknown sector — always allow
    if new_sector == 'OTHER':
        return True, 'Sector unknown — no correlation check'

    # Count active positions in same sector
    same_sector = [
        t for t in active_trades
        if t.get('status') == 'ACTIVE' and _get_sector(t.get('symbol', '')) == new_sector
    ]

    if len(same_sector) >= _MAX_PER_SECTOR:
        conflicting = [_extract_ticker(t['symbol']) for t in same_sector]
        return False, f"Sector {new_sector} already has {len(same_sector)} active position(s): {conflicting}"

    return True, f'Sector {new_sector} — OK'
