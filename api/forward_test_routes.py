"""
Forward Testing / Shadow Mode
Runs a strategy on the most recent market data and surfaces
current BUY signals — no orders placed.
"""
import threading
from flask import Blueprint, request, jsonify
from sqlalchemy import text
from core.database import get_engine
from auth.user_auth import auth_required

forward_bp = Blueprint('forward', __name__)


def _run_forward_test(user_id: int, strategy: dict, symbols: list, run_id: int):
    engine = get_engine()
    try:
        from core.strategy_engine import generate_signal
        from core.backtester_v2 import _fetch_data
        from datetime import date, timedelta
        import json

        to_date   = date.today()
        from_date = to_date - timedelta(days=90)

        signals_found = []
        for sym in symbols:
            try:
                df = _fetch_data(sym, from_date, to_date, strategy.get('timeframe', 'D'), None)
                if df is None or len(df) < 30:
                    continue
                sig = generate_signal(strategy['strategy_type'], strategy['parameters'], df)
                if sig in ('BUY', 'SELL'):
                    signals_found.append({
                        'symbol':    sym,
                        'signal':    sig,
                        'lastClose': float(df['close'].iloc[-1]),
                        'signalDate': str(df.index[-1].date() if hasattr(df.index[-1], 'date') else to_date),
                    })
            except Exception:
                continue

        with engine.begin() as conn:
            conn.execute(
                text("""
                    UPDATE backtest_runs
                    SET status = 'completed',
                        results = CAST(:res AS jsonb),
                        completed_at = NOW()
                    WHERE id = :id
                """),
                {'res': json.dumps({'signals': signals_found, 'scanned': len(symbols)}), 'id': run_id}
            )

    except Exception as e:
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE backtest_runs SET status='failed', error_message=:e WHERE id=:id"),
                {'e': str(e), 'id': run_id}
            )


@forward_bp.route('/run', methods=['POST'])
@auth_required
def run_forward():
    data        = request.get_json() or {}
    strategy_id = data.get('strategyId')
    universe    = (data.get('universe') or 'NIFTY50').upper()

    if not strategy_id:
        return jsonify({'error': 'strategyId is required'}), 400

    engine = get_engine()
    with engine.connect() as conn:
        strat = conn.execute(
            text("SELECT * FROM user_strategies WHERE id = :id AND user_id = :uid"),
            {'id': strategy_id, 'uid': request.user_id}
        ).fetchone()

    if not strat:
        return jsonify({'error': 'Strategy not found'}), 404

    from core.stock_universe import get_universe
    symbols = get_universe(universe) or []
    if not symbols:
        return jsonify({'error': f'Unknown universe: {universe}'}), 400

    import json
    strategy_dict = {
        'strategy_type': strat.strategy_type,
        'parameters':    strat.parameters or {},
        'timeframe':     strat.timeframe or 'D',
    }

    with engine.begin() as conn:
        row = conn.execute(
            text("""
                INSERT INTO backtest_runs (user_id, strategy_id, config, status)
                VALUES (:uid, :sid, CAST(:cfg AS jsonb), 'running')
                RETURNING id
            """),
            {
                'uid': request.user_id, 'sid': strategy_id,
                'cfg': json.dumps({'type': 'forward_test', 'universe': universe}),
            }
        ).fetchone()

    run_id = row.id
    threading.Thread(
        target=_run_forward_test,
        args=(request.user_id, strategy_dict, symbols, run_id),
        daemon=True
    ).start()

    return jsonify({'runId': run_id, 'status': 'running', 'scanning': len(symbols)}), 202


@forward_bp.route('/status/<int:run_id>', methods=['GET'])
@auth_required
def fwd_status(run_id):
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT status, results, error_message FROM backtest_runs WHERE id = :id AND user_id = :uid"),
            {'id': run_id, 'uid': request.user_id}
        ).fetchone()

    if not row:
        return jsonify({'error': 'Not found'}), 404

    if row.status == 'completed':
        return jsonify({'status': 'completed', **(row.results or {})}), 200

    return jsonify({'status': row.status, 'error': row.error_message}), 200
