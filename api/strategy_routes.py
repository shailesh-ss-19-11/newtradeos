import json
from flask import Blueprint, request, jsonify
from sqlalchemy import text
from core.database import get_engine
from auth.user_auth import auth_required
from core.strategy_engine import get_strategy_types
from core.subscription_plans import check_strategy_limit, get_user_tier

strategy_bp = Blueprint('strategy', __name__)


@strategy_bp.route('', methods=['GET'])
@auth_required
def list_strategies():
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT id, name, description, strategy_type, parameters,
                       timeframe, is_active, created_at, updated_at
                FROM user_strategies
                WHERE user_id = :uid
                ORDER BY created_at DESC
            """),
            {'uid': request.user_id}
        ).fetchall()

    strategies = [
        {
            'id':           r.id,
            'name':         r.name,
            'description':  r.description,
            'strategyType': r.strategy_type,
            'parameters':   r.parameters,
            'timeframe':    r.timeframe,
            'isActive':     r.is_active,
            'createdAt':    r.created_at.isoformat() if r.created_at else None,
            'updatedAt':    r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in rows
    ]
    return jsonify({'strategies': strategies}), 200


@strategy_bp.route('', methods=['POST'])
@auth_required
def create_strategy():
    data = request.get_json() or {}
    name          = (data.get('name') or '').strip()
    description   = (data.get('description') or '').strip()
    strategy_type = (data.get('strategyType') or '').strip()
    parameters    = data.get('parameters', {})
    timeframe     = data.get('timeframe', 'D')

    if not name:
        return jsonify({'error': 'Strategy name is required'}), 400

    valid_types = {s['type'] for s in get_strategy_types()}
    if strategy_type not in valid_types:
        return jsonify({'error': f'Invalid strategy type: {strategy_type}'}), 400

    tier = get_user_tier(request.user_id)
    allowed, err_msg = check_strategy_limit(request.user_id, tier)
    if not allowed:
        return jsonify({'error': err_msg, 'upgrade': True}), 403

    engine = get_engine()
    with engine.begin() as conn:
        row = conn.execute(
            text("""
                INSERT INTO user_strategies
                    (user_id, name, description, strategy_type, parameters, timeframe)
                VALUES (:uid, :name, :desc, :stype, CAST(:params AS jsonb), :tf)
                RETURNING id, name, description, strategy_type, parameters, timeframe, is_active, created_at
            """),
            {
                'uid': request.user_id, 'name': name, 'desc': description,
                'stype': strategy_type, 'params': json.dumps(parameters), 'tf': timeframe,
            }
        ).fetchone()

    return jsonify({
        'id':           row.id,
        'name':         row.name,
        'description':  row.description,
        'strategyType': row.strategy_type,
        'parameters':   row.parameters,
        'timeframe':    row.timeframe,
        'isActive':     row.is_active,
        'createdAt':    row.created_at.isoformat() if row.created_at else None,
    }), 201


@strategy_bp.route('/<int:strategy_id>', methods=['PUT'])
@auth_required
def update_strategy(strategy_id):
    data = request.get_json() or {}
    import json
    engine = get_engine()

    with engine.connect() as conn:
        existing = conn.execute(
            text("SELECT id FROM user_strategies WHERE id = :id AND user_id = :uid"),
            {'id': strategy_id, 'uid': request.user_id}
        ).fetchone()

    if not existing:
        return jsonify({'error': 'Strategy not found'}), 404

    name          = (data.get('name') or '').strip()
    description   = (data.get('description') or '').strip()
    strategy_type = (data.get('strategyType') or '').strip()
    parameters    = data.get('parameters', {})
    timeframe     = data.get('timeframe', 'D')
    is_active     = data.get('isActive', True)

    if not name:
        return jsonify({'error': 'Strategy name is required'}), 400

    valid_types = {s['type'] for s in get_strategy_types()}
    if strategy_type and strategy_type not in valid_types:
        return jsonify({'error': f'Invalid strategy type: {strategy_type}'}), 400

    with engine.begin() as conn:
        row = conn.execute(
            text("""
                UPDATE user_strategies
                SET name = :name, description = :desc, strategy_type = :stype,
                    parameters = CAST(:params AS jsonb), timeframe = :tf, is_active = :active,
                    updated_at = NOW()
                WHERE id = :id AND user_id = :uid
                RETURNING id, name, description, strategy_type, parameters, timeframe, is_active, updated_at
            """),
            {
                'name': name, 'desc': description, 'stype': strategy_type,
                'params': json.dumps(parameters), 'tf': timeframe, 'active': is_active,
                'id': strategy_id, 'uid': request.user_id,
            }
        ).fetchone()

    return jsonify({
        'id':           row.id,
        'name':         row.name,
        'description':  row.description,
        'strategyType': row.strategy_type,
        'parameters':   row.parameters,
        'timeframe':    row.timeframe,
        'isActive':     row.is_active,
        'updatedAt':    row.updated_at.isoformat() if row.updated_at else None,
    }), 200


@strategy_bp.route('/<int:strategy_id>', methods=['DELETE'])
@auth_required
def delete_strategy(strategy_id):
    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(
            text("DELETE FROM user_strategies WHERE id = :id AND user_id = :uid RETURNING id"),
            {'id': strategy_id, 'uid': request.user_id}
        ).fetchone()

    if not result:
        return jsonify({'error': 'Strategy not found'}), 404
    return jsonify({'message': 'Strategy deleted'}), 200


@strategy_bp.route('/types', methods=['GET'])
def strategy_types():
    return jsonify({'types': get_strategy_types()}), 200


@strategy_bp.route('/performance', methods=['GET'])
@auth_required
def strategies_performance():
    """Bulk aggregated backtest performance for all user strategies."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT
                    us.id,
                    COUNT(br.id) AS total_runs,
                    MAX(
                        CASE WHEN br.results IS NOT NULL
                        THEN (br.results -> 'summary' ->> 'totalPnL')::float
                        ELSE NULL END
                    ) AS best_pnl,
                    MAX(
                        CASE WHEN br.results IS NOT NULL
                        THEN (br.results -> 'summary' ->> 'winRate')::float
                        ELSE NULL END
                    ) AS best_win_rate,
                    MAX(br.created_at) AS last_run_at
                FROM user_strategies us
                LEFT JOIN backtest_runs br
                    ON br.strategy_id = us.id
                    AND br.user_id = :uid
                    AND br.status = 'completed'
                WHERE us.user_id = :uid
                GROUP BY us.id
            """),
            {'uid': request.user_id}
        ).fetchall()

    performance = {}
    for row in rows:
        performance[row.id] = {
            'totalRuns':    row.total_runs,
            'bestPnl':      round(row.best_pnl, 2) if row.best_pnl is not None else None,
            'bestWinRate':  round(row.best_win_rate, 2) if row.best_win_rate is not None else None,
            'lastRunAt':    row.last_run_at.isoformat() if row.last_run_at else None,
        }

    return jsonify({'performance': performance}), 200
