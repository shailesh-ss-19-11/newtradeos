import json
import os
from datetime import datetime, date
from decimal import Decimal
from typing import Any
import pytz
from sqlalchemy import text
from core.database import get_engine, init_db

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(BASE_DIR, 'config', 'config.json')
IST = pytz.timezone('Asia/Kolkata')


# ─── helpers ──────────────────────────────────────────────────────────────────

def _f(v) -> float | None:
    return float(v) if v is not None else None


def _row(mapping) -> dict:
    return dict(mapping)


def _trade_to_dict(r: dict) -> dict:
    return {
        'tradeId':                  r['trade_id'],
        'symbol':                   r['symbol'],
        'displaySymbol':            r['display_symbol'],
        'type':                     r['type'],
        'status':                   r['status'],
        'entryPrice':               _f(r['entry_price']),
        'stopLoss':                 _f(r['stop_loss']),
        'stopLossPercent':          _f(r['stop_loss_percent']),
        'target1':                  _f(r['target1']),
        'target2':                  _f(r['target2']),
        'target3':                  _f(r['target3']),
        'target4':                  _f(r['target4']),
        'target5':                  _f(r['target5']),
        'target1Pct':               _f(r['target1_percent']),
        'target2Pct':               _f(r['target2_percent']),
        'target3Pct':               _f(r['target3_percent']),
        'target1Hit':               r['target1_hit'],
        'target2Hit':               r['target2_hit'],
        'target3Hit':               r['target3_hit'],
        'targetHitLog':             r['target_hit_log'] or [],
        'positionSize':             r['position_size'],
        'capitalRequired':          _f(r['capital_required']),
        'maxLoss':                  _f(r['max_loss']),
        'riskReward':               _f(r['risk_reward']),
        'atr':                      _f(r['atr']),
        'confidence':               r['confidence'],
        'votes':                    r['votes'],
        'multiTimeframeAlignment':  r['multi_tf_alignment'],
        'strategies':               r['strategies'] or {},
        'optionsData':              r['options_data'],
        'isProfit':                 r['is_profit'],
        'profitLoss':               _f(r['profit_loss']),
        'profitLossPercent':        _f(r['profit_loss_pct']),
        'exitPrice':                _f(r['exit_price']),
        'exitTime':                 r['exit_time'].isoformat() if r['exit_time'] else None,
        'exitReason':               r['exit_reason'],
        'signalTime':               r['signal_time'].isoformat() if r['signal_time'] else None,
        'date':                     r['trade_date'].strftime('%Y-%m-%d') if r['trade_date'] else None,
        'telegramMessageId':        r['telegram_msg_id'],
        'notes':                    r['notes'],
    }


def _generate_trade_id(conn) -> str:
    today = datetime.now(IST).strftime('%Y%m%d')
    result = conn.execute(
        text("SELECT COUNT(*) FROM trades WHERE trade_id LIKE :prefix"),
        {"prefix": f"TRD-{today}-%"}
    )
    count = result.scalar() or 0
    return f"TRD-{today}-{count + 1:03d}"


# ─── init ─────────────────────────────────────────────────────────────────────

def init_data_files() -> None:
    init_db()
    print(f"[DB Storage] Initialized")


# ─── config ───────────────────────────────────────────────────────────────────

def load_config() -> dict:
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)


# ─── trades ───────────────────────────────────────────────────────────────────

def _compute_summary(trades: list) -> dict:
    closed = [t for t in trades if t.get('status') == 'CLOSED']
    active = [t for t in trades if t.get('status') == 'ACTIVE']
    profitable = [t for t in closed if t.get('isProfit') is True]
    loss_trades = [t for t in closed if t.get('isProfit') is False]
    total_pnl = sum(t.get('profitLoss', 0) or 0 for t in closed)
    win_rate = round(len(profitable) / len(closed) * 100, 2) if closed else 0.0
    avg_pnl = round(total_pnl / len(closed), 2) if closed else 0.0
    best = max(closed, key=lambda t: t.get('profitLoss', 0) or 0) if closed else None
    worst = min(closed, key=lambda t: t.get('profitLoss', 0) or 0) if closed else None
    return {
        "totalTrades": len(trades),
        "activeTrades": len(active),
        "closedTrades": len(closed),
        "profitableTrades": len(profitable),
        "lossTrades": len(loss_trades),
        "totalProfitLoss": round(total_pnl, 2),
        "winRate": win_rate,
        "averageProfitLoss": avg_pnl,
        "bestTrade": best['tradeId'] if best else None,
        "worstTrade": worst['tradeId'] if worst else None,
        "lastUpdated": datetime.now(IST).isoformat()
    }


def load_trades() -> dict:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT * FROM trades ORDER BY created_at DESC")).mappings()
        trades = [_trade_to_dict(_row(r)) for r in rows]
    return {"trades": trades, "summary": _compute_summary(trades)}


def get_active_trades() -> list:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT * FROM trades WHERE status = 'ACTIVE' ORDER BY signal_time DESC")
        ).mappings()
        return [_trade_to_dict(_row(r)) for r in rows]


def get_today_trades() -> list:
    today = datetime.now(IST).date()
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT * FROM trades WHERE trade_date = :d ORDER BY signal_time DESC"),
            {"d": today}
        ).mappings()
        return [_trade_to_dict(_row(r)) for r in rows]


def get_today_pnl() -> float:
    today = datetime.now(IST).date()
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT COALESCE(SUM(profit_loss), 0) FROM trades WHERE trade_date = :d AND status = 'CLOSED'"),
            {"d": today}
        )
        return float(result.scalar() or 0)


def _f(v):
    """Convert numpy scalar types to plain Python floats/ints for psycopg2."""
    if v is None:
        return None
    try:
        import numpy as np
        if isinstance(v, (np.floating, np.integer)):
            return v.item()
    except ImportError:
        pass
    return v


def save_signal(signal_dict: dict) -> str:
    engine = get_engine()
    with engine.begin() as conn:
        trade_id = _generate_trade_id(conn)
        sig_time = signal_dict.get('signalTime')
        trade_date = signal_dict.get('date')

        conn.execute(text("""
            INSERT INTO trades (
                trade_id, symbol, display_symbol, type, status,
                entry_price, stop_loss, stop_loss_percent,
                target1, target2, target3, target4, target5,
                target1_percent, target2_percent, target3_percent,
                position_size, capital_required, max_loss, risk_reward, atr,
                confidence, votes, multi_tf_alignment,
                strategies, options_data,
                signal_time, trade_date
            ) VALUES (
                :trade_id, :symbol, :display_symbol, :type, 'ACTIVE',
                :entry_price, :stop_loss, :stop_loss_percent,
                :t1, :t2, :t3, :t4, :t5,
                :t1pct, :t2pct, :t3pct,
                :position_size, :capital_required, :max_loss, :risk_reward, :atr,
                :confidence, :votes, :multi_tf,
                :strategies, :options_data,
                :signal_time, :trade_date
            )
        """), {
            "trade_id":         trade_id,
            "symbol":           signal_dict.get('symbol'),
            "display_symbol":   signal_dict.get('displaySymbol'),
            "type":             signal_dict.get('type'),
            "entry_price":      _f(signal_dict.get('entryPrice')),
            "stop_loss":        _f(signal_dict.get('stopLoss')),
            "stop_loss_percent": _f(signal_dict.get('stopLossPercent')),
            "t1":               _f(signal_dict.get('target1')),
            "t2":               _f(signal_dict.get('target2')),
            "t3":               _f(signal_dict.get('target3')),
            "t4":               _f(signal_dict.get('target4')),
            "t5":               _f(signal_dict.get('target5')),
            "t1pct":            _f(signal_dict.get('target1Pct')),
            "t2pct":            _f(signal_dict.get('target2Pct')),
            "t3pct":            _f(signal_dict.get('target3Pct')),
            "position_size":    _f(signal_dict.get('positionSize')),
            "capital_required": _f(signal_dict.get('capitalRequired')),
            "max_loss":         _f(signal_dict.get('maxLoss')),
            "risk_reward":      _f(signal_dict.get('riskReward')),
            "atr":              _f(signal_dict.get('atr')),
            "confidence":       signal_dict.get('confidence'),
            "votes":            _f(signal_dict.get('votesCount', signal_dict.get('votes', '0/8').split('/')[0])),
            "multi_tf":         signal_dict.get('multiTimeframeAlignment'),
            "strategies":       json.dumps(signal_dict.get('strategies', {})),
            "options_data":     json.dumps(signal_dict.get('optionsData')) if signal_dict.get('optionsData') else None,
            "signal_time":      sig_time,
            "trade_date":       trade_date,
        })
    return trade_id


def update_trade(trade_id: str, updates: dict) -> bool:
    try:
        engine = get_engine()
        with engine.begin() as conn:
            row = conn.execute(
                text("SELECT * FROM trades WHERE trade_id = :id"),
                {"id": trade_id}
            ).mappings().first()
            if not row:
                return False

            trade = _row(row)

            if updates.get('exitPrice') is not None:
                entry = float(trade['entry_price'] or 0)
                exit_price = float(updates['exitPrice'])
                size = int(trade['position_size'] or 0)
                if trade['type'] == 'BUY':
                    pnl = (exit_price - entry) * size
                else:
                    pnl = (entry - exit_price) * size
                updates['profitLoss'] = round(pnl, 2)
                updates['profitLossPercent'] = round((pnl / (entry * size)) * 100, 2) if entry * size else 0
                updates['isProfit'] = pnl > 0
                updates['status'] = 'CLOSED'
                updates['exitTime'] = datetime.now(IST).isoformat()

            field_map = {
                'status':            'status',
                'exitPrice':         'exit_price',
                'exitReason':        'exit_reason',
                'exitTime':          'exit_time',
                'profitLoss':        'profit_loss',
                'profitLossPercent': 'profit_loss_pct',
                'isProfit':          'is_profit',
                'telegramMessageId': 'telegram_msg_id',
                'positionSize':      'position_size',
                'notes':             'notes',
            }

            set_parts, params = [], {"id": trade_id}
            for key, val in updates.items():
                if key in field_map:
                    col = field_map[key]
                    set_parts.append(f"{col} = :{col}")
                    params[col] = val

            if not set_parts:
                return True

            result = conn.execute(
                text(f"UPDATE trades SET {', '.join(set_parts)} WHERE trade_id = :id"),
                params
            )
            return result.rowcount > 0
    except Exception:
        return False


def mark_target_hit(trade_id: str, target_number: int, price: float) -> bool:
    try:
        engine = get_engine()
        with engine.begin() as conn:
            row = conn.execute(
                text("SELECT target_hit_log FROM trades WHERE trade_id = :id"),
                {"id": trade_id}
            ).mappings().first()
            if not row:
                return False

            raw = row['target_hit_log']
            if isinstance(raw, str):
                log = json.loads(raw)
            else:
                log = list(raw or [])
            log.append({"target": target_number, "price": price, "time": datetime.now(IST).isoformat()})

            col = f"target{target_number}_hit"
            result = conn.execute(
                text(f"UPDATE trades SET {col} = TRUE, target_hit_log = :log WHERE trade_id = :id"),
                {"log": json.dumps(log), "id": trade_id}
            )
            return result.rowcount > 0
    except Exception:
        return False


def get_trade_by_id(trade_id: str) -> dict | None:
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM trades WHERE trade_id = :id"),
            {"id": trade_id}
        ).mappings().first()
        return _trade_to_dict(_row(row)) if row else None


def get_trades_by_date(date_string: str) -> list:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT * FROM trades WHERE trade_date = :d ORDER BY signal_time DESC"),
            {"d": date_string}
        ).mappings()
        return [_trade_to_dict(_row(r)) for r in rows]


def get_trades_by_symbol(symbol: str) -> list:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT * FROM trades WHERE LOWER(symbol) LIKE :s OR LOWER(display_symbol) LIKE :s ORDER BY signal_time DESC"),
            {"s": f"%{symbol.lower()}%"}
        ).mappings()
        return [_trade_to_dict(_row(r)) for r in rows]


# ─── errors ───────────────────────────────────────────────────────────────────

def save_error(error_dict: dict) -> None:
    try:
        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO errors (module, message, symbol) VALUES (:m, :msg, :s)"),
                {
                    "m":   error_dict.get('module', ''),
                    "msg": str(error_dict.get('message', '')),
                    "s":   error_dict.get('symbol', '')
                }
            )
            conn.execute(text("DELETE FROM errors WHERE id IN (SELECT id FROM errors ORDER BY id ASC LIMIT GREATEST(0, (SELECT COUNT(*) FROM errors) - 500))"))
    except Exception as e:
        print(f"[DB Storage] Could not save error: {e}")


def get_errors(limit: int = 50) -> list:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT * FROM errors ORDER BY timestamp DESC LIMIT :lim"),
            {"lim": limit}
        ).mappings()
        return [dict(r) for r in rows]


# ─── backtest ─────────────────────────────────────────────────────────────────

def get_backtest_results() -> dict:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT symbol, results FROM backtest_results")).mappings()
        return {r['symbol']: r['results'] for r in rows}


def save_backtest_results(results_dict: dict) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        for symbol, results in results_dict.items():
            conn.execute(text("""
                INSERT INTO backtest_results (symbol, results, run_date)
                VALUES (:s, :r, :d)
                ON CONFLICT (symbol) DO UPDATE SET results = :r, run_date = :d, created_at = NOW()
            """), {
                "s": symbol,
                "r": json.dumps(results),
                "d": datetime.now(IST).date()
            })


# ─── analytics ────────────────────────────────────────────────────────────────

def get_daily_pnl_chart(days: int = 30) -> list:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT
                trade_date::text AS date,
                COALESCE(SUM(profit_loss), 0)  AS pnl,
                COUNT(*)                        AS total,
                COUNT(*) FILTER (WHERE is_profit = TRUE)  AS wins,
                COUNT(*) FILTER (WHERE is_profit = FALSE) AS losses
            FROM trades
            WHERE status = 'CLOSED'
              AND trade_date >= CURRENT_DATE - :days
            GROUP BY trade_date
            ORDER BY trade_date ASC
        """), {"days": days}).mappings()
        return [dict(r) for r in rows]


def get_strategy_stats() -> list:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT
                jsonb_object_keys(strategies) AS strategy,
                COUNT(*) AS total_trades,
                COUNT(*) FILTER (WHERE is_profit = TRUE) AS wins
            FROM trades
            WHERE status = 'CLOSED'
            GROUP BY strategy
            ORDER BY total_trades DESC
        """)).mappings()
        return [dict(r) for r in rows]


def get_top_symbols(limit: int = 10) -> list:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT
                display_symbol,
                COUNT(*) AS trades,
                COALESCE(SUM(profit_loss), 0) AS total_pnl,
                COUNT(*) FILTER (WHERE is_profit = TRUE) AS wins,
                ROUND(COUNT(*) FILTER (WHERE is_profit = TRUE)::DECIMAL / NULLIF(COUNT(*), 0) * 100, 1) AS win_rate
            FROM trades
            WHERE status = 'CLOSED'
            GROUP BY display_symbol
            ORDER BY total_pnl DESC
            LIMIT :lim
        """), {"lim": limit}).mappings()
        return [dict(r) for r in rows]
