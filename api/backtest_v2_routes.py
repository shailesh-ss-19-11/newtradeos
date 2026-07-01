import json
import threading
from datetime import datetime
from flask import Blueprint, request, jsonify
from sqlalchemy import text
from core.database import get_engine
from auth.user_auth import auth_required
from core.stock_universe import search_stocks, get_universe, UNIVERSES
from core.subscription_plans import check_backtest_limit, get_user_tier, get_plan

backtest_v2_bp = Blueprint('backtest_v2', __name__)

# In-memory job tracker for background backtest runs
_running_jobs: dict[int, dict] = {}


@backtest_v2_bp.route('/stocks/search', methods=['GET'])
def stocks_search():
    query = request.args.get('q', '').strip()
    if len(query) < 1:
        return jsonify({'results': []}), 200
    results = search_stocks(query, limit=15)
    return jsonify({'results': results}), 200


@backtest_v2_bp.route('/universe/<universe_key>', methods=['GET'])
def get_universe_list(universe_key):
    symbols = get_universe(universe_key.upper())
    return jsonify({'universe': universe_key.upper(), 'count': len(symbols), 'symbols': symbols}), 200


@backtest_v2_bp.route('/run', methods=['POST'])
@auth_required
def run_backtest():
    data        = request.get_json() or {}
    config      = data.get('config', {})
    strategy_id = data.get('strategyId')

    if not strategy_id:
        return jsonify({'error': 'strategyId is required'}), 400

    # Load the user strategy
    engine = get_engine()
    with engine.connect() as conn:
        strat_row = conn.execute(
            text("""
                SELECT id, name, description, strategy_type, parameters, timeframe, is_active
                FROM user_strategies
                WHERE id = :sid AND user_id = :uid
            """),
            {'sid': strategy_id, 'uid': request.user_id}
        ).fetchone()

    if not strat_row:
        return jsonify({'error': 'Strategy not found'}), 404
    if not strat_row.is_active:
        return jsonify({'error': 'Strategy is inactive'}), 400

    user_strategy = {
        'id':            strat_row.id,
        'name':          strat_row.name,
        'strategy_type': strat_row.strategy_type,
        'parameters':    strat_row.parameters or {},
        'timeframe':     strat_row.timeframe or 'D',
    }

    # Validate config
    errors = _validate_config(config)
    if errors:
        return jsonify({'errors': errors}), 400

    # Check subscription limits
    tier = get_user_tier(request.user_id)
    allowed, err_msg = check_backtest_limit(request.user_id, tier)
    if not allowed:
        return jsonify({'error': err_msg, 'upgrade': True}), 403

    plan = get_plan(tier)
    universe_key = config.get('universe', 'NIFTY50')
    if universe_key not in plan['allowed_universes']:
        return jsonify({
            'error': f'Universe {universe_key} is not available on your {plan["name"]} plan. Upgrade to access.',
            'upgrade': True,
        }), 403

    # Create backtest_run record
    with engine.begin() as conn:
        run_row = conn.execute(
            text("""
                INSERT INTO backtest_runs (user_id, strategy_id, config, status)
                VALUES (:uid, :sid, CAST(:cfg AS jsonb), 'running')
                RETURNING id
            """),
            {'uid': request.user_id, 'sid': strategy_id, 'cfg': json.dumps(config)}
        ).fetchone()

    run_id = run_row.id

    # Run in background thread
    def _run():
        try:
            from core.backtester_v2 import run_backtest_v2
            results = run_backtest_v2(config, user_strategy)

            with engine.begin() as conn:
                conn.execute(
                    text("""
                        UPDATE backtest_runs
                        SET status = 'completed', results = CAST(:res AS jsonb), completed_at = NOW()
                        WHERE id = :id
                    """),
                    {'res': json.dumps(results), 'id': run_id}
                )
            _running_jobs[run_id] = {'status': 'completed'}
        except Exception as e:
            with engine.begin() as conn:
                conn.execute(
                    text("UPDATE backtest_runs SET status = 'failed', error_message = :err WHERE id = :id"),
                    {'err': str(e), 'id': run_id}
                )
            _running_jobs[run_id] = {'status': 'failed', 'error': str(e)}

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    _running_jobs[run_id] = {'status': 'running'}

    return jsonify({'runId': run_id, 'status': 'running'}), 202


@backtest_v2_bp.route('/status/<int:run_id>', methods=['GET'])
@auth_required
def backtest_status(run_id):
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT status, error_message, completed_at FROM backtest_runs WHERE id = :id AND user_id = :uid"),
            {'id': run_id, 'uid': request.user_id}
        ).fetchone()

    if not row:
        return jsonify({'error': 'Run not found'}), 404

    return jsonify({
        'runId':       run_id,
        'status':      row.status,
        'error':       row.error_message,
        'completedAt': row.completed_at.isoformat() if row.completed_at else None,
    }), 200


@backtest_v2_bp.route('/results/<int:run_id>', methods=['GET'])
@auth_required
def backtest_results(run_id):
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT br.status, br.results, br.error_message, br.config,
                       br.created_at, br.completed_at, us.name AS strategy_name
                FROM backtest_runs br
                LEFT JOIN user_strategies us ON br.strategy_id = us.id
                WHERE br.id = :id AND br.user_id = :uid
            """),
            {'id': run_id, 'uid': request.user_id}
        ).fetchone()

    if not row:
        return jsonify({'error': 'Run not found'}), 404
    if row.status == 'running':
        return jsonify({'status': 'running', 'runId': run_id}), 202
    if row.status == 'failed':
        return jsonify({'status': 'failed', 'error': row.error_message}), 200

    return jsonify({
        'status':       row.status,
        'strategyName': row.strategy_name,
        'config':       row.config,
        'results':      row.results,
        'createdAt':    row.created_at.isoformat() if row.created_at else None,
        'completedAt':  row.completed_at.isoformat() if row.completed_at else None,
    }), 200


@backtest_v2_bp.route('/history', methods=['GET'])
@auth_required
def backtest_history():
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT br.id, br.status, br.config, br.created_at, br.completed_at,
                       br.error_message, us.name AS strategy_name
                FROM backtest_runs br
                LEFT JOIN user_strategies us ON br.strategy_id = us.id
                WHERE br.user_id = :uid
                ORDER BY br.created_at DESC
                LIMIT 20
            """),
            {'uid': request.user_id}
        ).fetchall()

    history = [
        {
            'id':           r.id,
            'status':       r.status,
            'strategyName': r.strategy_name,
            'config':       r.config,
            'error':        r.error_message,
            'createdAt':    r.created_at.isoformat() if r.created_at else None,
            'completedAt':  r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in rows
    ]
    return jsonify({'history': history}), 200


@backtest_v2_bp.route('/results/<int:run_id>/export', methods=['GET'])
@auth_required
def export_csv(run_id):
    """Download backtest trade table as CSV."""
    import csv, io
    from flask import Response

    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT results, status FROM backtest_runs WHERE id = :id AND user_id = :uid"),
            {'id': run_id, 'uid': request.user_id}
        ).fetchone()

    if not row or row.status != 'completed':
        return jsonify({'error': 'Results not available'}), 404

    trades = (row.results or {}).get('trades', [])
    if not trades:
        return jsonify({'error': 'No trades in this backtest'}), 404

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=trades[0].keys())
    writer.writeheader()
    writer.writerows(trades)

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=backtest_{run_id}_trades.csv'}
    )


@backtest_v2_bp.route('/walk-forward', methods=['POST'])
@auth_required
def walk_forward():
    """Run walk-forward analysis: split period into N windows, each with in-sample + OOS."""
    import threading as _th
    data        = request.get_json() or {}
    strategy_id = data.get('strategyId')
    config      = data.get('config', {})
    n_windows   = int(data.get('nWindows', 3))
    oos_ratio   = float(data.get('oosRatio', 0.3))

    if not strategy_id:
        return jsonify({'error': 'strategyId is required'}), 400

    engine = get_engine()
    with engine.connect() as conn:
        strat = conn.execute(
            text("SELECT id, name, strategy_type, parameters, timeframe FROM user_strategies WHERE id = :id AND user_id = :uid"),
            {'id': strategy_id, 'uid': request.user_id}
        ).fetchone()

    if not strat:
        return jsonify({'error': 'Strategy not found'}), 404

    user_strategy = {
        'id': strat.id, 'name': strat.name,
        'strategy_type': strat.strategy_type,
        'parameters': strat.parameters or {},
        'timeframe': strat.timeframe or 'D',
    }

    with engine.begin() as conn:
        run_row = conn.execute(
            text("""
                INSERT INTO backtest_runs (user_id, strategy_id, config, status)
                VALUES (:uid, :sid, CAST(:cfg AS jsonb), 'running')
                RETURNING id
            """),
            {'uid': request.user_id, 'sid': strategy_id,
             'cfg': json.dumps({**config, 'type': 'walk_forward', 'nWindows': n_windows})}
        ).fetchone()

    run_id  = run_row.id
    user_id = request.user_id

    def _do_wf():
        try:
            from core.backtester_v2 import _fetch_data, _date_range, run_backtest_v2
            from datetime import datetime, timedelta
            import pandas as pd

            period   = config.get('period', '1Y')
            from_dt, to_dt = _date_range(period, config.get('from_date'), config.get('to_date'))
            total_days = (to_dt - from_dt).days
            window_days = total_days // n_windows

            window_results = []
            for i in range(n_windows):
                w_start = from_dt + timedelta(days=i * window_days)
                w_end   = from_dt + timedelta(days=(i + 1) * window_days)
                split   = w_start + timedelta(days=int(window_days * (1 - oos_ratio)))

                # IS config
                is_cfg = {**config, 'period': 'CUSTOM',
                          'from_date': w_start.strftime('%Y-%m-%d'),
                          'to_date':   split.strftime('%Y-%m-%d')}
                # OOS config
                oos_cfg = {**config, 'period': 'CUSTOM',
                           'from_date': split.strftime('%Y-%m-%d'),
                           'to_date':   w_end.strftime('%Y-%m-%d')}

                is_res  = run_backtest_v2(is_cfg,  user_strategy)
                oos_res = run_backtest_v2(oos_cfg, user_strategy)

                window_results.append({
                    'window':    i + 1,
                    'isFrom':    w_start.strftime('%Y-%m-%d'),
                    'isSplit':   split.strftime('%Y-%m-%d'),
                    'isTo':      w_end.strftime('%Y-%m-%d'),
                    'inSample':  is_res.get('summary', {}),
                    'outOfSample': oos_res.get('summary', {}),
                })

            oos_summaries = [w['outOfSample'] for w in window_results]
            avg_oos_winrate = sum(s.get('winRate', 0) for s in oos_summaries) / len(oos_summaries) if oos_summaries else 0
            avg_oos_pnl     = sum(s.get('totalPnL', 0) for s in oos_summaries) / len(oos_summaries) if oos_summaries else 0

            final = {
                'windows': window_results,
                'summary': {'avgOosWinRate': round(avg_oos_winrate, 2), 'avgOosPnL': round(avg_oos_pnl, 2), 'nWindows': n_windows},
            }

            with engine.begin() as conn:
                conn.execute(
                    text("UPDATE backtest_runs SET status='completed', results=CAST(:r AS jsonb), completed_at=NOW() WHERE id=:id"),
                    {'r': json.dumps(final), 'id': run_id}
                )
        except Exception as ex:
            with engine.begin() as conn:
                conn.execute(
                    text("UPDATE backtest_runs SET status='failed', error_message=:e WHERE id=:id"),
                    {'e': str(ex), 'id': run_id}
                )

    _th.Thread(target=_do_wf, daemon=True).start()
    return jsonify({'runId': run_id, 'status': 'running', 'type': 'walk_forward'}), 202


def _validate_config(config: dict) -> list[str]:
    errors = []
    if not config.get('universe'):
        errors.append('Universe is required')
    if config.get('universe') == 'INDIVIDUAL' and not config.get('symbol'):
        errors.append('Symbol is required for individual backtest')

    period = config.get('period', '1Y')
    if period == 'CUSTOM':
        from_date = config.get('from_date')
        to_date   = config.get('to_date')
        if not from_date or not to_date:
            errors.append('From date and to date are required for custom period')
        elif from_date >= to_date:
            errors.append('From date must be earlier than to date')

    capital = config.get('initial_capital', 100000)
    if not isinstance(capital, (int, float)) or capital <= 0:
        errors.append('Initial capital must be a positive number')

    max_pct = config.get('max_capital_per_trade_pct', 20)
    if not isinstance(max_pct, (int, float)) or max_pct <= 0 or max_pct > 100:
        errors.append('Max capital per trade must be between 0 and 100%')

    t1_enabled = config.get('t1_enabled', True)
    t2_enabled = config.get('t2_enabled', True)
    t3_enabled = config.get('t3_enabled', True)

    if t1_enabled and t2_enabled and t3_enabled:
        total = (config.get('t1_qty_pct', 30) + config.get('t2_qty_pct', 30) + config.get('t3_qty_pct', 40))
        if abs(total - 100) > 1:
            errors.append(f'T1 + T2 + T3 quantity allocation must total 100% (currently {total}%)')

    sl_pct = config.get('sl_pct', 2)
    if not isinstance(sl_pct, (int, float)) or sl_pct <= 0:
        errors.append('Stop loss % must be positive')

    return errors
