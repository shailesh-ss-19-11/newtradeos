import json
import os
from datetime import datetime
from typing import Any
import pytz
from filelock import FileLock

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
CONFIG_DIR = os.path.join(BASE_DIR, 'config')
IST = pytz.timezone('Asia/Kolkata')

TRADES_FILE = os.path.join(DATA_DIR, 'trades.json')
ERRORS_FILE = os.path.join(DATA_DIR, 'errors.json')
BACKTEST_FILE = os.path.join(DATA_DIR, 'backtest_results.json')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')

LOCK_TIMEOUT = 10


def _lock(filepath: str) -> FileLock:
    return FileLock(filepath + '.lock', timeout=LOCK_TIMEOUT)


def _read_json(filepath: str) -> Any:
    with open(filepath, 'r') as f:
        return json.load(f)


def _write_json(filepath: str, data: Any) -> None:
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def init_data_files() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(CONFIG_DIR, exist_ok=True)

    if not os.path.exists(TRADES_FILE):
        _write_json(TRADES_FILE, {
            "trades": [],
            "summary": {
                "totalTrades": 0, "activeTrades": 0, "closedTrades": 0,
                "profitableTrades": 0, "lossTrades": 0, "totalProfitLoss": 0.0,
                "winRate": 0.0, "averageProfitLoss": 0.0,
                "bestTrade": None, "worstTrade": None, "lastUpdated": ""
            }
        })

    if not os.path.exists(ERRORS_FILE):
        _write_json(ERRORS_FILE, {"errors": []})

    if not os.path.exists(BACKTEST_FILE):
        _write_json(BACKTEST_FILE, {})

    print(f"[FileStorage] Data files initialized at {DATA_DIR}")


def load_config() -> dict:
    with _lock(CONFIG_FILE):
        return _read_json(CONFIG_FILE)


def load_trades() -> dict:
    with _lock(TRADES_FILE):
        return _read_json(TRADES_FILE)


def get_active_trades() -> list:
    data = load_trades()
    return [t for t in data['trades'] if t.get('status') == 'ACTIVE']


def get_today_trades() -> list:
    today = datetime.now(IST).strftime('%Y-%m-%d')
    data = load_trades()
    return [t for t in data['trades'] if t.get('date') == today]


def get_today_pnl() -> float:
    today_trades = get_today_trades()
    return sum(
        t.get('profitLoss', 0) or 0
        for t in today_trades
        if t.get('status') == 'CLOSED' and t.get('profitLoss') is not None
    )


def _generate_trade_id(trades: list) -> str:
    today = datetime.now(IST).strftime('%Y%m%d')
    today_trades = [t for t in trades if t.get('tradeId', '').startswith(f'TRD-{today}')]
    seq = len(today_trades) + 1
    return f'TRD-{today}-{seq:03d}'


def _recalculate_summary(data: dict) -> dict:
    trades = data['trades']
    closed = [t for t in trades if t.get('status') == 'CLOSED']
    active = [t for t in trades if t.get('status') == 'ACTIVE']
    profitable = [t for t in closed if t.get('isProfit') is True]
    loss_trades = [t for t in closed if t.get('isProfit') is False]

    total_pnl = sum(t.get('profitLoss', 0) or 0 for t in closed)
    win_rate = (len(profitable) / len(closed) * 100) if closed else 0.0
    avg_pnl = total_pnl / len(closed) if closed else 0.0

    best = max(closed, key=lambda t: t.get('profitLoss', 0) or 0) if closed else None
    worst = min(closed, key=lambda t: t.get('profitLoss', 0) or 0) if closed else None

    data['summary'] = {
        "totalTrades": len(trades),
        "activeTrades": len(active),
        "closedTrades": len(closed),
        "profitableTrades": len(profitable),
        "lossTrades": len(loss_trades),
        "totalProfitLoss": round(total_pnl, 2),
        "winRate": round(win_rate, 2),
        "averageProfitLoss": round(avg_pnl, 2),
        "bestTrade": best['tradeId'] if best else None,
        "worstTrade": worst['tradeId'] if worst else None,
        "lastUpdated": datetime.now(IST).isoformat()
    }
    return data


def save_signal(signal_dict: dict) -> str:
    with _lock(TRADES_FILE):
        data = _read_json(TRADES_FILE)
        trade_id = _generate_trade_id(data['trades'])
        trade = {
            "tradeId": trade_id,
            "symbol": signal_dict.get('symbol'),
            "displaySymbol": signal_dict.get('displaySymbol'),
            "type": signal_dict.get('type'),
            "entryPrice": signal_dict.get('entryPrice'),
            "stopLoss": signal_dict.get('stopLoss'),
            "stopLossPercent": signal_dict.get('stopLossPercent'),
            "target1": signal_dict.get('target1'),
            "target2": signal_dict.get('target2'),
            "target3": signal_dict.get('target3'),
            "target4": signal_dict.get('target4'),
            "target5": signal_dict.get('target5'),
            "target1Hit": False,
            "target2Hit": False,
            "target3Hit": False,
            "targetHitLog": [],
            "positionSize": signal_dict.get('positionSize'),
            "capitalRequired": signal_dict.get('capitalRequired'),
            "maxLoss": signal_dict.get('maxLoss'),
            "riskReward": signal_dict.get('riskReward'),
            "atr": signal_dict.get('atr'),
            "confidence": signal_dict.get('confidence'),
            "votes": signal_dict.get('votes'),
            "multiTimeframeAlignment": signal_dict.get('multiTimeframeAlignment'),
            "strategies": signal_dict.get('strategies', {}),
            "optionsData": signal_dict.get('optionsData'),
            "status": "ACTIVE",
            "isProfit": None,
            "profitLoss": None,
            "profitLossPercent": None,
            "exitPrice": None,
            "exitTime": None,
            "exitReason": None,
            "signalTime": signal_dict.get('signalTime'),
            "date": signal_dict.get('date'),
            "telegramMessageId": None
        }
        data['trades'].append(trade)
        data = _recalculate_summary(data)
        _write_json(TRADES_FILE, data)
        return trade_id


def update_trade(trade_id: str, updates: dict) -> bool:
    with _lock(TRADES_FILE):
        data = _read_json(TRADES_FILE)
        for i, trade in enumerate(data['trades']):
            if trade.get('tradeId') == trade_id:
                trade.update(updates)

                if updates.get('exitPrice') is not None:
                    entry = trade.get('entryPrice', 0)
                    exit_price = updates['exitPrice']
                    size = trade.get('positionSize', 0) or 0
                    if trade.get('type') == 'BUY':
                        pnl = (exit_price - entry) * size
                    else:
                        pnl = (entry - exit_price) * size
                    trade['profitLoss'] = round(pnl, 2)
                    trade['profitLossPercent'] = round((pnl / (entry * size)) * 100, 2) if entry * size else 0
                    trade['isProfit'] = pnl > 0
                    trade['status'] = 'CLOSED'
                    trade['exitTime'] = datetime.now(IST).isoformat()

                data['trades'][i] = trade
                data = _recalculate_summary(data)
                _write_json(TRADES_FILE, data)
                return True
    return False


def mark_target_hit(trade_id: str, target_number: int, price: float) -> bool:
    with _lock(TRADES_FILE):
        data = _read_json(TRADES_FILE)
        for i, trade in enumerate(data['trades']):
            if trade.get('tradeId') == trade_id:
                key = f'target{target_number}Hit'
                trade[key] = True
                if 'targetHitLog' not in trade:
                    trade['targetHitLog'] = []
                trade['targetHitLog'].append({
                    "target": target_number,
                    "price": price,
                    "time": datetime.now(IST).isoformat()
                })
                data['trades'][i] = trade
                _write_json(TRADES_FILE, data)
                return True
    return False


def save_error(error_dict: dict) -> None:
    error_dict['timestamp'] = datetime.now(IST).isoformat()
    try:
        with _lock(ERRORS_FILE):
            data = _read_json(ERRORS_FILE)
            data['errors'].append(error_dict)
            if len(data['errors']) > 500:
                data['errors'] = data['errors'][-500:]
            _write_json(ERRORS_FILE, data)
    except Exception as e:
        print(f"[FileStorage] Could not save error: {e}")


def get_trades_by_date(date_string: str) -> list:
    data = load_trades()
    return [t for t in data['trades'] if t.get('date') == date_string]


def get_trades_by_symbol(symbol: str) -> list:
    data = load_trades()
    symbol_lower = symbol.lower()
    return [
        t for t in data['trades']
        if symbol_lower in (t.get('symbol', '') or '').lower()
        or symbol_lower in (t.get('displaySymbol', '') or '').lower()
    ]


def get_backtest_results() -> dict:
    with _lock(BACKTEST_FILE):
        return _read_json(BACKTEST_FILE)


def save_backtest_results(results_dict: dict) -> None:
    with _lock(BACKTEST_FILE):
        _write_json(BACKTEST_FILE, results_dict)


def get_trade_by_id(trade_id: str) -> dict | None:
    data = load_trades()
    for t in data['trades']:
        if t.get('tradeId') == trade_id:
            return t
    return None
