import json
import threading
from flask import Blueprint, request, jsonify
from sqlalchemy import text
from core.database import get_engine
from auth.user_auth import auth_required

optimizer_bp = Blueprint('optimizer', __name__)


def _run_optimization(run_id: int, user_id: int, strategy: dict, config: dict):
    """Background thread: grid search over parameter ranges."""
    engine = get_engine()

    try:
        from core.strategy_engine import generate_signal
        import pandas as pd
        import numpy as np

        symbol  = config.get('symbol', 'NSE:NIFTY50-INDEX')
        period  = config.get('period', '1Y')
        param_grid = config.get('paramGrid', {})

        from core.backtester_v2 import _fetch_data, _date_range
        from_date, to_date = _date_range(period, None, None)
        df = _fetch_data(symbol, from_date, to_date, strategy.get('timeframe', 'D'), None)

        if df is None or len(df) < 50:
            raise ValueError(f'Insufficient data for {symbol}')

        # Build parameter combinations
        import itertools
        keys   = list(param_grid.keys())
        values = [param_grid[k] for k in keys]  # each is a list of values

        results = []
        for combo in itertools.product(*values):
            params = dict(zip(keys, combo))
            params = {**strategy.get('parameters', {}), **params}

            # Simple signal-counting backtest
            signals = []
            for i in range(30, len(df)):
                sig = generate_signal(strategy['strategy_type'], params, df.iloc[:i])
                signals.append(sig)

            buy_signals = signals.count('BUY')
            # Count profitable trades (signal→entry next bar, hold 5 bars)
            wins, losses, total_ret = 0, 0, 0
            for i, sig in enumerate(signals):
                if sig == 'BUY':
                    entry_i = 30 + i + 1
                    exit_i  = entry_i + 5
                    if exit_i < len(df):
                        ret = (df['close'].iloc[exit_i] / df['close'].iloc[entry_i] - 1) * 100
                        total_ret += ret
                        if ret > 0:
                            wins += 1
                        else:
                            losses += 1

            total_trades = wins + losses
            win_rate  = (wins / total_trades * 100) if total_trades > 0 else 0
            avg_ret   = (total_ret / total_trades) if total_trades > 0 else 0

            results.append({
                'params':      params,
                'buySamples':  buy_signals,
                'totalTrades': total_trades,
                'wins':        wins,
                'losses':      losses,
                'winRate':     round(win_rate, 2),
                'avgReturn':   round(avg_ret, 4),
                'score':       round(win_rate * avg_ret, 4),
            })

        results.sort(key=lambda x: x['score'], reverse=True)

        with engine.begin() as conn:
            conn.execute(
                text("""
                    UPDATE optimizer_runs
                    SET status = 'completed', results = CAST(:res AS jsonb), completed_at = NOW()
                    WHERE id = :id
                """),
                {'res': json.dumps({'results': results[:100], 'totalCombos': len(results)}), 'id': run_id}
            )

    except Exception as e:
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE optimizer_runs SET status = 'failed', error_message = :err WHERE id = :id"),
                {'err': str(e), 'id': run_id}
            )


@optimizer_bp.route('/run', methods=['POST'])
@auth_required
def run_optimizer():
    data        = request.get_json() or {}
    strategy_id = data.get('strategyId')
    config      = data.get('config', {})

    if not strategy_id:
        return jsonify({'error': 'strategyId is required'}), 400

    param_grid = config.get('paramGrid', {})
    if not param_grid:
        return jsonify({'error': 'paramGrid is required (e.g. {"fast_period": [5,9,12], "slow_period": [20,26,50]})'}), 400

    engine = get_engine()
    with engine.connect() as conn:
        strat = conn.execute(
            text("SELECT id, name, strategy_type, parameters, timeframe FROM user_strategies WHERE id = :id AND user_id = :uid"),
            {'id': strategy_id, 'uid': request.user_id}
        ).fetchone()

    if not strat:
        return jsonify({'error': 'Strategy not found'}), 404

    strategy_dict = {
        'id': strat.id, 'name': strat.name,
        'strategy_type': strat.strategy_type,
        'parameters': strat.parameters or {},
        'timeframe': strat.timeframe,
    }

    with engine.begin() as conn:
        row = conn.execute(
            text("""
                INSERT INTO optimizer_runs (user_id, strategy_id, config, status)
                VALUES (:uid, :sid, CAST(:cfg AS jsonb), 'running')
                RETURNING id
            """),
            {'uid': request.user_id, 'sid': strategy_id, 'cfg': json.dumps(config)}
        ).fetchone()

    run_id = row.id
    t = threading.Thread(target=_run_optimization, args=(run_id, request.user_id, strategy_dict, config), daemon=True)
    t.start()

    return jsonify({'runId': run_id, 'status': 'running'}), 202


@optimizer_bp.route('/status/<int:run_id>', methods=['GET'])
@auth_required
def optimizer_status(run_id):
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT status, error_message FROM optimizer_runs WHERE id = :id AND user_id = :uid"),
            {'id': run_id, 'uid': request.user_id}
        ).fetchone()

    if not row:
        return jsonify({'error': 'Run not found'}), 404
    return jsonify({'status': row.status, 'error': row.error_message}), 200


@optimizer_bp.route('/results/<int:run_id>', methods=['GET'])
@auth_required
def optimizer_results(run_id):
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT status, results, error_message FROM optimizer_runs WHERE id = :id AND user_id = :uid"),
            {'id': run_id, 'uid': request.user_id}
        ).fetchone()

    if not row:
        return jsonify({'error': 'Run not found'}), 404
    if row.status != 'completed':
        return jsonify({'status': row.status, 'error': row.error_message}), 200
    return jsonify({'status': 'completed', **row.results}), 200


@optimizer_bp.route('/history', methods=['GET'])
@auth_required
def optimizer_history():
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT or2.id, or2.status, or2.created_at, or2.completed_at,
                       us.name AS strategy_name
                FROM optimizer_runs or2
                LEFT JOIN user_strategies us ON us.id = or2.strategy_id
                WHERE or2.user_id = :uid
                ORDER BY or2.created_at DESC LIMIT 20
            """),
            {'uid': request.user_id}
        ).fetchall()

    return jsonify({'runs': [
        {
            'id':           r.id, 'status': r.status,
            'strategyName': r.strategy_name,
            'createdAt':    r.created_at.isoformat() if r.created_at else None,
            'completedAt':  r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in rows
    ]}), 200
