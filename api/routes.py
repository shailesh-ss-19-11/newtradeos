import subprocess
import sys
import os
import csv
import io
import json
import time
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, Response
import pytz

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db_storage import (
    load_trades,
    get_trade_by_id, get_trades_by_date, get_trades_by_symbol,
    get_active_trades, get_today_trades, get_today_pnl,
    update_trade, get_backtest_results, load_config,
    get_errors, get_daily_pnl_chart, get_strategy_stats, get_top_symbols
)
from auth.token_manager import is_token_valid

api_bp = Blueprint('api', __name__)
IST = pytz.timezone('Asia/Kolkata')


def _error(msg: str, code: int = 400):
    return jsonify({'error': msg}), code


def _is_market_open() -> bool:
    now = datetime.now(IST)
    if now.weekday() >= 5:
        return False
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return market_open <= now <= market_close


# ─── TRADES ───────────────────────────────────────────────────────────────────

@api_bp.route('/trades', methods=['GET'])
def get_trades():
    try:
        data = load_trades()
        trades = data['trades']

        status_filter = request.args.get('status', 'ALL').upper()
        symbol_filter = request.args.get('symbol', '').lower()
        date_filter = request.args.get('date', '')
        from_date = request.args.get('from_date', '')
        to_date = request.args.get('to_date', '')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))

        if status_filter != 'ALL':
            trades = [t for t in trades if t.get('status') == status_filter]

        if symbol_filter:
            trades = [
                t for t in trades
                if symbol_filter in (t.get('symbol', '') or '').lower()
                or symbol_filter in (t.get('displaySymbol', '') or '').lower()
            ]

        if date_filter:
            trades = [t for t in trades if t.get('date') == date_filter]

        if from_date:
            trades = [t for t in trades if t.get('date', '') >= from_date]

        if to_date:
            trades = [t for t in trades if t.get('date', '') <= to_date]

        trades_sorted = sorted(trades, key=lambda t: t.get('signalTime', ''), reverse=True)
        total = len(trades_sorted)
        start = (page - 1) * per_page
        end = start + per_page
        page_trades = trades_sorted[start:end]

        return jsonify({
            'trades': page_trades,
            'pagination': {
                'total': total,
                'page': page,
                'perPage': per_page,
                'totalPages': (total + per_page - 1) // per_page
            }
        })
    except Exception as e:
        return _error(str(e), 500)


@api_bp.route('/trades/<trade_id>', methods=['GET'])
def get_trade(trade_id):
    try:
        trade = get_trade_by_id(trade_id)
        if not trade:
            return _error(f'Trade {trade_id} not found', 404)
        return jsonify(trade)
    except Exception as e:
        return _error(str(e), 500)


@api_bp.route('/trades/date/<date>', methods=['GET'])
def get_trades_by_date_route(date):
    try:
        trades = get_trades_by_date(date)
        return jsonify({'trades': trades, 'total': len(trades), 'date': date})
    except Exception as e:
        return _error(str(e), 500)


@api_bp.route('/trades/symbol/<path:symbol>', methods=['GET'])
def get_trades_by_symbol_route(symbol):
    try:
        trades = get_trades_by_symbol(symbol)
        return jsonify({'trades': trades, 'total': len(trades), 'symbol': symbol})
    except Exception as e:
        return _error(str(e), 500)


@api_bp.route('/trades/<trade_id>/close', methods=['POST'])
def close_trade(trade_id):
    try:
        body = request.get_json() or {}
        exit_price = body.get('exitPrice')
        exit_reason = body.get('exitReason', 'MANUAL_CLOSE')

        if exit_price is None:
            return _error('exitPrice is required')

        trade = get_trade_by_id(trade_id)
        if not trade:
            return _error(f'Trade {trade_id} not found', 404)
        if trade.get('status') == 'CLOSED':
            return _error('Trade already closed')

        success = update_trade(trade_id, {
            'exitPrice': float(exit_price),
            'exitReason': exit_reason
        })

        if success:
            updated = get_trade_by_id(trade_id)
            return jsonify({'success': True, 'trade': updated})
        return _error('Failed to update trade', 500)
    except Exception as e:
        return _error(str(e), 500)


@api_bp.route('/trades/<trade_id>/update', methods=['POST'])
def update_trade_route(trade_id):
    try:
        body = request.get_json() or {}
        protected_fields = {'tradeId', 'symbol', 'entryPrice', 'type', 'date', 'signalTime'}
        updates = {k: v for k, v in body.items() if k not in protected_fields}

        if not updates:
            return _error('No valid fields to update')

        trade = get_trade_by_id(trade_id)
        if not trade:
            return _error(f'Trade {trade_id} not found', 404)

        success = update_trade(trade_id, updates)
        if success:
            return jsonify({'success': True, 'updated': list(updates.keys())})
        return _error('Failed to update', 500)
    except Exception as e:
        return _error(str(e), 500)


# ─── SUMMARY ──────────────────────────────────────────────────────────────────

@api_bp.route('/summary', methods=['GET'])
def get_summary():
    try:
        data = load_trades()
        summary = data['summary']
        config = load_config()
        account_balance = config['trading']['accountBalance']

        active_trades = get_active_trades()
        capital_in_use = sum(t.get('capitalRequired', 0) or 0 for t in active_trades)

        today_str = datetime.now(IST).strftime('%Y-%m-%d')
        today_pnl = get_today_pnl()

        week_start = (datetime.now(IST) - timedelta(days=7)).strftime('%Y-%m-%d')
        month_start = (datetime.now(IST) - timedelta(days=30)).strftime('%Y-%m-%d')
        all_trades = data['trades']

        week_trades = [t for t in all_trades if t.get('date', '') >= week_start and t.get('status') == 'CLOSED']
        month_trades = [t for t in all_trades if t.get('date', '') >= month_start and t.get('status') == 'CLOSED']

        return jsonify({
            **summary,
            'todayPnL': round(today_pnl, 2),
            'weekPnL': round(sum(t.get('profitLoss', 0) or 0 for t in week_trades), 2),
            'monthPnL': round(sum(t.get('profitLoss', 0) or 0 for t in month_trades), 2),
            'currentActiveTrades': active_trades,
            'accountBalance': account_balance,
            'availableCapital': round(account_balance - capital_in_use, 2)
        })
    except Exception as e:
        return _error(str(e), 500)


@api_bp.route('/summary/date/<date>', methods=['GET'])
def daily_summary(date):
    try:
        day_trades = get_trades_by_date(date)
        closed = [t for t in day_trades if t.get('status') == 'CLOSED']
        wins = [t for t in closed if t.get('isProfit') is True]
        losses = [t for t in closed if t.get('isProfit') is False]
        total_pnl = sum(t.get('profitLoss', 0) or 0 for t in closed)
        win_rate = round(len(wins) / len(closed) * 100, 2) if closed else 0

        best = max(closed, key=lambda t: t.get('profitLoss', 0) or 0) if closed else None
        worst = min(closed, key=lambda t: t.get('profitLoss', 0) or 0) if closed else None

        return jsonify({
            'date': date,
            'totalSignals': len(day_trades),
            'wins': len(wins),
            'losses': len(losses),
            'totalPnL': round(total_pnl, 2),
            'winRate': win_rate,
            'bestTrade': best['tradeId'] if best else None,
            'worstTrade': worst['tradeId'] if worst else None
        })
    except Exception as e:
        return _error(str(e), 500)


@api_bp.route('/summary/weekly', methods=['GET'])
def weekly_summary():
    try:
        week_start = (datetime.now(IST) - timedelta(days=7)).strftime('%Y-%m-%d')
        today = datetime.now(IST).strftime('%Y-%m-%d')
        data = load_trades()
        week_trades = [
            t for t in data['trades']
            if week_start <= t.get('date', '') <= today and t.get('status') == 'CLOSED'
        ]
        wins = [t for t in week_trades if t.get('isProfit') is True]
        total_pnl = sum(t.get('profitLoss', 0) or 0 for t in week_trades)
        win_rate = round(len(wins) / len(week_trades) * 100, 2) if week_trades else 0

        return jsonify({
            'period': f'{week_start} to {today}',
            'totalTrades': len(week_trades),
            'wins': len(wins),
            'losses': len(week_trades) - len(wins),
            'totalPnL': round(total_pnl, 2),
            'winRate': win_rate
        })
    except Exception as e:
        return _error(str(e), 500)


@api_bp.route('/summary/monthly', methods=['GET'])
def monthly_summary():
    try:
        month_start = (datetime.now(IST) - timedelta(days=30)).strftime('%Y-%m-%d')
        today = datetime.now(IST).strftime('%Y-%m-%d')
        data = load_trades()
        month_trades = [
            t for t in data['trades']
            if month_start <= t.get('date', '') <= today and t.get('status') == 'CLOSED'
        ]
        wins = [t for t in month_trades if t.get('isProfit') is True]
        total_pnl = sum(t.get('profitLoss', 0) or 0 for t in month_trades)
        win_rate = round(len(wins) / len(month_trades) * 100, 2) if month_trades else 0

        return jsonify({
            'period': f'{month_start} to {today}',
            'totalTrades': len(month_trades),
            'wins': len(wins),
            'losses': len(month_trades) - len(wins),
            'totalPnL': round(total_pnl, 2),
            'winRate': win_rate
        })
    except Exception as e:
        return _error(str(e), 500)


# ─── BACKTEST ─────────────────────────────────────────────────────────────────

@api_bp.route('/backtest/results', methods=['GET'])
def backtest_results():
    try:
        results = get_backtest_results()
        return jsonify(results)
    except Exception as e:
        return _error(str(e), 500)


@api_bp.route('/backtest/run', methods=['POST'])
def run_backtest():
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        backtester_path = os.path.join(base_dir, 'core', 'backtester.py')
        subprocess.Popen(
            [sys.executable, backtester_path],
            cwd=base_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return jsonify({'status': 'started', 'message': 'Backtester running in background'})
    except Exception as e:
        return _error(str(e), 500)




# ─── OPTIONS ──────────────────────────────────────────────────────────────────

@api_bp.route('/options/<path:symbol>', methods=['GET'])
def get_option_chain(symbol):
    try:
        from core.data_fetcher import fetch_option_chain
        data = fetch_option_chain(symbol)
        if data is None:
            return _error('Failed to fetch option chain', 503)
        return jsonify(data)
    except Exception as e:
        return _error(str(e), 500)


# ─── MARKET ───────────────────────────────────────────────────────────────────

@api_bp.route('/market/status', methods=['GET'])
def market_status():
    try:
        now_ist = datetime.now(IST)
        is_open = _is_market_open()

        if not is_open:
            if now_ist.weekday() < 5:
                if now_ist.hour < 9 or (now_ist.hour == 9 and now_ist.minute < 15):
                    next_open = now_ist.replace(hour=9, minute=15, second=0, microsecond=0)
                else:
                    next_day = now_ist + timedelta(days=1)
                    while next_day.weekday() >= 5:
                        next_day += timedelta(days=1)
                    next_open = next_day.replace(hour=9, minute=15, second=0, microsecond=0)
            else:
                days_until_mon = (7 - now_ist.weekday()) % 7 or 7
                next_open = (now_ist + timedelta(days=days_until_mon)).replace(hour=9, minute=15, second=0, microsecond=0)
        else:
            next_open = None

        next_close = now_ist.replace(hour=15, minute=30, second=0, microsecond=0) if is_open else None

        return jsonify({
            'isOpen': is_open,
            'currentTime': now_ist.strftime('%H:%M:%S IST'),
            'currentDate': now_ist.strftime('%Y-%m-%d'),
            'nextOpen': next_open.isoformat() if next_open else None,
            'nextClose': next_close.isoformat() if next_close else None
        })
    except Exception as e:
        return _error(str(e), 500)


@api_bp.route('/market/quotes', methods=['GET'])
def market_quotes():
    try:
        symbols_param = request.args.get('symbols', '')
        if not symbols_param:
            return _error('symbols query param required')
        symbols = [s.strip() for s in symbols_param.split(',') if s.strip()]

        from core.data_fetcher import fetch_quotes
        quotes = fetch_quotes(symbols)
        return jsonify(quotes)
    except Exception as e:
        return _error(str(e), 500)


# ─── ERRORS ───────────────────────────────────────────────────────────────────

@api_bp.route('/errors', methods=['GET'])
def get_errors_route():
    try:
        limit = int(request.args.get('limit', 50))
        errors = get_errors(limit)
        return jsonify({'errors': errors, 'total': len(errors)})
    except Exception as e:
        return _error(str(e), 500)


# ─── ANALYTICS ────────────────────────────────────────────────────────────────

@api_bp.route('/analytics/pnl-chart', methods=['GET'])
def pnl_chart():
    try:
        days = int(request.args.get('days', 30))
        data = get_daily_pnl_chart(days)
        return jsonify(data)
    except Exception as e:
        return _error(str(e), 500)


@api_bp.route('/analytics/strategy-stats', methods=['GET'])
def strategy_stats():
    try:
        return jsonify(get_strategy_stats())
    except Exception as e:
        return _error(str(e), 500)


@api_bp.route('/analytics/top-symbols', methods=['GET'])
def top_symbols():
    try:
        limit = int(request.args.get('limit', 10))
        return jsonify(get_top_symbols(limit))
    except Exception as e:
        return _error(str(e), 500)


# ─── CSV EXPORT ───────────────────────────────────────────────────────────────

@api_bp.route('/trades/export', methods=['GET'])
def export_trades_csv():
    try:
        data   = load_trades()
        trades = data['trades']

        status_filter = request.args.get('status', 'ALL').upper()
        from_date     = request.args.get('from_date', '')
        to_date       = request.args.get('to_date', '')

        if status_filter != 'ALL':
            trades = [t for t in trades if t.get('status') == status_filter]
        if from_date:
            trades = [t for t in trades if t.get('date', '') >= from_date]
        if to_date:
            trades = [t for t in trades if t.get('date', '') <= to_date]

        trades = sorted(trades, key=lambda t: t.get('signalTime', ''), reverse=True)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'Trade ID', 'Date', 'Symbol', 'Type', 'Status',
            'Entry Price', 'Stop Loss', 'Target 1', 'Target 2', 'Target 3',
            'Exit Price', 'Exit Reason', 'P&L', 'P&L %',
            'Position Size', 'Capital Required', 'Risk:Reward',
            'Votes', 'Confidence', 'MTF Alignment', 'Market Regime', 'Signal Time'
        ])
        for t in trades:
            writer.writerow([
                t.get('tradeId', ''),
                t.get('date', ''),
                t.get('displaySymbol', ''),
                t.get('type', ''),
                t.get('status', ''),
                t.get('entryPrice', ''),
                t.get('stopLoss', ''),
                t.get('target1', ''),
                t.get('target2', ''),
                t.get('target3', ''),
                t.get('exitPrice', ''),
                t.get('exitReason', ''),
                t.get('profitLoss', ''),
                t.get('profitLossPercent', ''),
                t.get('positionSize', ''),
                t.get('capitalRequired', ''),
                t.get('riskReward', ''),
                t.get('votes', ''),
                t.get('confidence', ''),
                t.get('multiTimeframeAlignment', ''),
                t.get('marketRegime', ''),
                t.get('signalTime', ''),
            ])

        output.seek(0)
        filename = f"trades_{datetime.now(IST).strftime('%Y%m%d_%H%M%S')}.csv"
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
    except Exception as e:
        return _error(str(e), 500)


# ─── SCREENER ─────────────────────────────────────────────────────────────────

@api_bp.route('/screener', methods=['GET'])
def screener():
    """
    Returns live signal snapshot for all watchlist symbols.
    Reads the latest closed/active trade per symbol as a proxy for current signal.
    """
    try:
        from core.data_fetcher import fetch_quotes

        syms_cfg = load_config().get('symbols', {})
        symbols  = syms_cfg.get('equity', []) + syms_cfg.get('indices', [])

        quotes = {}
        for i in range(0, len(symbols), 50):
            try:
                q = fetch_quotes(symbols[i:i+50])
                quotes.update(q)
            except Exception:
                pass

        data        = load_trades()
        active_map  = {t['symbol']: t for t in data['trades'] if t.get('status') == 'ACTIVE'}

        rows = []
        for sym in symbols:
            q      = quotes.get(sym, {})
            active = active_map.get(sym)
            ltp    = q.get('ltp', 0) or 0
            chp    = q.get('changePct', 0) or 0
            vol    = q.get('vol', 0) or 0
            short  = sym.split(':')[1].replace('-EQ', '').replace('-INDEX', '') if ':' in sym else sym

            row = {
                'symbol':      sym,
                'displaySymbol': short,
                'ltp':         ltp,
                'changePct':   chp,
                'volume':      vol,
                'hasActive':   active is not None,
                'activeType':  active.get('type') if active else None,
                'confidence':  active.get('confidence') if active else None,
                'votes':       active.get('votes') if active else None,
                'entryPrice':  active.get('entryPrice') if active else None,
                'unrealizedPnl': None,
            }

            if active and ltp and active.get('entryPrice'):
                entry = float(active['entryPrice'])
                size  = int(active.get('positionSize', 0) or 0)
                pnl   = (ltp - entry) * size if active['type'] == 'BUY' else (entry - ltp) * size
                row['unrealizedPnl'] = round(pnl, 2)

            rows.append(row)

        return jsonify({'symbols': rows, 'total': len(rows)})
    except Exception as e:
        return _error(str(e), 500)


# ─── HEATMAP ──────────────────────────────────────────────────────────────────

@api_bp.route('/heatmap', methods=['GET'])
def heatmap():
    """
    Returns performance heat map data for all watchlist symbols.
    Each cell = total P&L + win rate for that symbol over the requested period.
    """
    try:
        days       = int(request.args.get('days', 30))
        from_date  = (datetime.now(IST) - timedelta(days=days)).strftime('%Y-%m-%d')
        data       = load_trades()
        syms_cfg   = load_config().get('symbols', {})
        all_syms   = syms_cfg.get('equity', []) + syms_cfg.get('indices', [])

        closed     = [t for t in data['trades']
                      if t.get('status') == 'CLOSED' and t.get('date', '') >= from_date]

        sym_stats  = {}
        for t in closed:
            sym = t.get('displaySymbol', '')
            if sym not in sym_stats:
                sym_stats[sym] = {'trades': 0, 'wins': 0, 'pnl': 0.0}
            sym_stats[sym]['trades'] += 1
            sym_stats[sym]['pnl']    += t.get('profitLoss', 0) or 0
            if t.get('isProfit'):
                sym_stats[sym]['wins'] += 1

        cells = []
        for sym_full in all_syms:
            short = sym_full.split(':')[1].replace('-EQ', '').replace('-INDEX', '') if ':' in sym_full else sym_full
            stats = sym_stats.get(short, {'trades': 0, 'wins': 0, 'pnl': 0.0})
            cells.append({
                'symbol':   short,
                'fullSymbol': sym_full,
                'trades':   stats['trades'],
                'wins':     stats['wins'],
                'pnl':      round(stats['pnl'], 2),
                'winRate':  round(stats['wins'] / stats['trades'] * 100, 1) if stats['trades'] else 0,
            })

        cells.sort(key=lambda x: x['pnl'], reverse=True)
        return jsonify({'cells': cells, 'days': days, 'total': len(cells)})
    except Exception as e:
        return _error(str(e), 500)


# ─── RISK REPORT ──────────────────────────────────────────────────────────────

@api_bp.route('/analytics/risk-report', methods=['GET'])
def risk_report():
    """Monthly risk metrics: max drawdown, Sharpe ratio, consecutive losses."""
    try:
        days      = int(request.args.get('days', 30))
        from_date = (datetime.now(IST) - timedelta(days=days)).strftime('%Y-%m-%d')
        data      = load_trades()
        trades    = [t for t in data['trades']
                     if t.get('status') == 'CLOSED' and t.get('date', '') >= from_date]

        trades_sorted = sorted(trades, key=lambda t: t.get('signalTime', ''))
        pnls          = [t.get('profitLoss', 0) or 0 for t in trades_sorted]

        # Max drawdown
        peak = 0.0
        max_dd = 0.0
        cumulative = 0.0
        for p in pnls:
            cumulative += p
            if cumulative > peak:
                peak = cumulative
            dd = peak - cumulative
            if dd > max_dd:
                max_dd = dd

        # Sharpe ratio (simplified, daily)
        import statistics
        avg_pnl  = statistics.mean(pnls) if pnls else 0
        std_pnl  = statistics.stdev(pnls) if len(pnls) > 1 else 1
        sharpe   = round(avg_pnl / std_pnl * (252 ** 0.5), 2) if std_pnl else 0

        # Consecutive losses
        max_consec_loss = 0
        cur_consec      = 0
        for t in trades_sorted:
            if not t.get('isProfit'):
                cur_consec += 1
                max_consec_loss = max(max_consec_loss, cur_consec)
            else:
                cur_consec = 0

        total_pnl = sum(pnls)
        wins      = [t for t in trades if t.get('isProfit')]

        config          = load_config()
        account_balance = config['trading']['accountBalance']

        return jsonify({
            'period':            f'Last {days} days',
            'totalTrades':       len(trades),
            'totalPnL':          round(total_pnl, 2),
            'winRate':           round(len(wins) / len(trades) * 100, 2) if trades else 0,
            'maxDrawdown':       round(max_dd, 2),
            'maxDrawdownPct':    round(max_dd / account_balance * 100, 2) if account_balance else 0,
            'sharpeRatio':       sharpe,
            'maxConsecLosses':   max_consec_loss,
            'avgWin':            round(sum(t.get('profitLoss', 0) or 0 for t in wins) / len(wins), 2) if wins else 0,
            'avgLoss':           round(sum(t.get('profitLoss', 0) or 0 for t in trades if not t.get('isProfit')) / max(len(trades) - len(wins), 1), 2),
            'profitFactor':      round(
                sum(t.get('profitLoss', 0) or 0 for t in wins) /
                abs(sum(t.get('profitLoss', 0) or 0 for t in trades if not t.get('isProfit')) or 1), 2
            ),
        })
    except Exception as e:
        return _error(str(e), 500)


# ─── TRADING MODE ─────────────────────────────────────────────────────────────

@api_bp.route('/trading-mode', methods=['GET'])
def get_trading_mode():
    mode = os.getenv('TRADING_MODE', 'paper')
    return jsonify({'mode': mode, 'isPaper': mode == 'paper', 'isLive': mode == 'live'})


@api_bp.route('/trading-mode', methods=['POST'])
def set_trading_mode():
    body = request.get_json() or {}
    mode = body.get('mode', 'paper').lower()
    if mode not in ('paper', 'live'):
        return _error('mode must be "paper" or "live"')
    os.environ['TRADING_MODE'] = mode
    return jsonify({'mode': mode, 'message': f'Trading mode set to {mode}'})


# ─── HEALTH ───────────────────────────────────────────────────────────────────

@api_bp.route('/health', methods=['GET'])
def health():
    try:
        from scanner import last_scan_time
    except ImportError:
        last_scan_time = None

    return jsonify({
        'status': 'ok',
        'lastScanTime': last_scan_time,
        'activeTrades': len(get_active_trades()),
        'tokenValid': is_token_valid(),
        'marketOpen': _is_market_open(),
        'timestamp': datetime.now(IST).isoformat(),
        'version': '1.0.0'
    })


# ─── CHART DATA ───────────────────────────────────────────────────────────────

@api_bp.route('/chart', methods=['GET'])
def get_chart():
    try:
        symbol     = request.args.get('symbol', '').strip()
        resolution = request.args.get('resolution', '15')
        days       = request.args.get('days', None)
        days       = int(days) if days else None
        if not symbol:
            return _error('symbol query param is required')

        from core.data_fetcher import fetch_historical, fetch_quotes

        df = fetch_historical(symbol, resolution, days_back=days)
        if df is None or df.empty:
            return _error('No data returned for this symbol. Check the symbol format.', 404)

        # EMA lines
        df['ema9']  = df['close'].ewm(span=9,  adjust=False).mean()
        df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()

        candles, volumes, ema9, ema21 = [], [], [], []
        for ts, row in df.iterrows():
            t = int(ts.timestamp())
            candles.append({'time': t, 'open': row['open'], 'high': row['high'], 'low': row['low'], 'close': row['close']})
            volumes.append({'time': t, 'value': row['volume'], 'color': '#00d4aa44' if row['close'] >= row['open'] else '#ef444444'})
            ema9.append( {'time': t, 'value': round(row['ema9'],  2)})
            ema21.append({'time': t, 'value': round(row['ema21'], 2)})

        # Live quote
        quote = {}
        try:
            q = fetch_quotes([symbol])
            quote = q.get(symbol, {})
        except Exception:
            pass

        return jsonify({
            'symbol':     symbol,
            'resolution': resolution,
            'candles':    candles,
            'volumes':    volumes,
            'ema9':       ema9,
            'ema21':      ema21,
            'quote':      quote,
        })
    except Exception as e:
        return _error(str(e), 500)


# ─── LIVE SSE STREAM ──────────────────────────────────────────────────────────

@api_bp.route('/live')
def live_stream():
    def generate():
        while True:
            try:
                active = get_active_trades()

                try:
                    from core.realtime_feed import get_ltp_from_feed
                    use_feed = True
                except Exception:
                    use_feed = False

                trades_out = []
                total_unrealized = 0.0
                total_capital = 0.0

                for t in active:
                    ltp = get_ltp_from_feed(t['symbol']) if use_feed else 0
                    entry = float(t.get('entryPrice') or 0)
                    size  = int(t.get('positionSize') or 0)
                    capital = float(t.get('capitalRequired') or 0)

                    if ltp and entry and size:
                        pnl = (ltp - entry) * size if t['type'] == 'BUY' else (entry - ltp) * size
                        pnl_pct = round(pnl / (entry * size) * 100, 2) if entry * size else 0
                    else:
                        pnl = 0.0
                        pnl_pct = 0.0

                    total_unrealized += pnl
                    total_capital    += capital

                    trades_out.append({
                        'tradeId':        t['tradeId'],
                        'displaySymbol':  t['displaySymbol'],
                        'type':           t['type'],
                        'entryPrice':     entry,
                        'stopLoss':       t.get('stopLoss'),
                        'target1':        t.get('target1'),
                        'positionSize':   size,
                        'capitalRequired': capital,
                        'confidence':     t.get('confidence'),
                        'votes':          t.get('votes'),
                        'currentPrice':   ltp,
                        'unrealizedPnl':  round(pnl, 2),
                        'unrealizedPct':  pnl_pct,
                        'signalTime':     t.get('signalTime'),
                    })

                payload = json.dumps({
                    'activeTrades':       trades_out,
                    'totalUnrealizedPnl': round(total_unrealized, 2),
                    'totalCapitalDeployed': round(total_capital, 2),
                    'tradeCount':         len(trades_out),
                    'timestamp':          datetime.now(IST).isoformat(),
                })
                yield f"data: {payload}\n\n"

            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

            time.sleep(2)

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control':    'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection':       'keep-alive',
        }
    )


# ─── TICK STREAM SSE ──────────────────────────────────────────────────────────

@api_bp.route('/stream')
def tick_stream():
    symbol = request.args.get('symbol', '').strip()
    if not symbol:
        return _error('symbol query param required', 400)

    def generate():
        import requests as _req
        from core.upstox_instruments import fyers_to_upstox
        from core.realtime_feed import _is_market_hours
        from auth.upstox_auth import get_upstox_headers, UPSTOX_BASE_URL

        ik = fyers_to_upstox(symbol)

        while True:
            try:
                if ik and _is_market_hours():
                    headers = get_upstox_headers()
                    resp = _req.get(
                        f"{UPSTOX_BASE_URL}/v2/market-quote/quotes",
                        headers=headers,
                        params={"instrument_key": ik},
                        timeout=4,
                    )
                    if resp.status_code == 200:
                        data  = resp.json().get("data", {})
                        item  = data.get(ik) or data.get(ik.replace("|", ":"))
                        if item:
                            ohlc  = item.get("ohlc", {})
                            depth = item.get("depth", {})
                            bid   = (depth.get("buy",  [{}])[0].get("price", 0)
                                     if depth.get("buy")  else 0)
                            ask   = (depth.get("sell", [{}])[0].get("price", 0)
                                     if depth.get("sell") else 0)
                            tick  = {
                                "ltp":       item.get("last_price",              0),
                                "open":      ohlc.get("open",                    0),
                                "high":      ohlc.get("high",                    0),
                                "low":       ohlc.get("low",                     0),
                                "close":     ohlc.get("close",                   0),
                                "volume":    item.get("volume",                  0),
                                "oi":        item.get("oi",                      0),
                                "bid":       bid,
                                "ask":       ask,
                                "change":    item.get("net_change",              0),
                                "changePct": item.get("net_change_percentage",   0),
                            }
                            if tick["ltp"] > 0:
                                yield f"data: {json.dumps(tick)}\n\n"
                                time.sleep(1.5)
                                continue

                # Outside market hours or no data — keep connection alive silently
                yield ": heartbeat\n\n"

            except GeneratorExit:
                return
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

            time.sleep(1.5)

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control':     'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection':        'keep-alive',
        }
    )


# ─── DEBUG SCAN ───────────────────────────────────────────────────────────────

@api_bp.route('/scan/debug', methods=['GET'])
def debug_scan():
    """
    Dry-run scan on all watchlist symbols right now, ignoring market hours.
    Returns per-symbol rejection reasons. Does NOT save trades or send Telegram.
    Query params:
      symbol=RELIANCE  — scan a single symbol only
    """
    try:
        from core import combined_engine
        from core.db_storage import get_active_trades, get_today_pnl

        config = load_config()
        trading = config['trading']
        account_balance = float(os.getenv('ACCOUNT_BALANCE', trading['accountBalance']))
        active_trades   = get_active_trades()
        today_pnl       = get_today_pnl()

        single = request.args.get('symbol', '').strip()
        if single:
            # Normalise: add exchange prefix if missing
            if ':' not in single:
                single = f'NSE:{single.upper()}-EQ'
            symbols = [single]
        else:
            syms_cfg = load_config().get('symbols', {})
            symbols  = syms_cfg.get('equity', []) + syms_cfg.get('indices', [])

        results_out = []
        signals_found = []

        for sym in symbols:
            try:
                sig = combined_engine.run(
                    symbol=sym,
                    account_balance=account_balance,
                    max_risk_pct=trading['maxRiskPerTrade'],
                    min_strategies=trading['minStrategiesConfirmed'],
                    min_rr=trading['minRiskReward'],
                    active_trades=active_trades,
                    today_pnl=today_pnl,
                    max_daily_loss=trading['maxDailyLoss'],
                    force=True,
                    verbose=True,
                )
                if sig:
                    signals_found.append(sig)
                    results_out.append({
                        'symbol':  sym,
                        'result':  'SIGNAL',
                        'type':    sig['type'],
                        'votes':   sig['votes'],
                        'rr':      sig['riskReward'],
                        'conf':    sig['confidence'],
                        'entry':   sig['entryPrice'],
                        'sl':      sig['stopLoss'],
                        'target1': sig['target1'],
                    })
                else:
                    results_out.append({'symbol': sym, 'result': 'BLOCKED'})
            except Exception as e:
                results_out.append({'symbol': sym, 'result': 'ERROR', 'error': str(e)})

        return jsonify({
            'scanned':      len(symbols),
            'signals':      len(signals_found),
            'blocked':      sum(1 for r in results_out if r['result'] == 'BLOCKED'),
            'errors':       sum(1 for r in results_out if r['result'] == 'ERROR'),
            'activeTradesNow': len(active_trades),
            'todayPnl':     today_pnl,
            'results':      results_out,
        })
    except Exception as e:
        return _error(str(e), 500)
