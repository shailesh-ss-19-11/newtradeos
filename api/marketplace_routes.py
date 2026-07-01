from flask import Blueprint, request, jsonify
from sqlalchemy import text
from core.database import get_engine
from auth.user_auth import auth_required

marketplace_bp = Blueprint('marketplace', __name__)


@marketplace_bp.route('', methods=['GET'])
@auth_required
def browse():
    category = request.args.get('category', '').strip()
    engine   = get_engine()
    with engine.connect() as conn:
        where  = 'WHERE ms.is_published = TRUE'
        params = {}
        if category:
            where += ' AND ms.category = :cat'
            params['cat'] = category

        rows = conn.execute(
            text(f"""
                SELECT ms.id, ms.title, ms.description, ms.category,
                       ms.tier_required, ms.subscribers, ms.avg_win_rate,
                       ms.avg_pnl, ms.published_at,
                       u.name AS author_name,
                       us.strategy_type, us.timeframe,
                       EXISTS(
                           SELECT 1 FROM marketplace_subscriptions sub
                           WHERE sub.marketplace_strategy_id = ms.id AND sub.user_id = :uid
                       ) AS is_subscribed
                FROM marketplace_strategies ms
                JOIN users u ON u.id = ms.user_id
                JOIN user_strategies us ON us.id = ms.strategy_id
                {where}
                ORDER BY ms.subscribers DESC, ms.published_at DESC
                LIMIT 50
            """),
            {'uid': request.user_id, **params}
        ).fetchall()

    return jsonify({'strategies': [
        {
            'id':           r.id,
            'title':        r.title,
            'description':  r.description,
            'category':     r.category,
            'tierRequired': r.tier_required,
            'subscribers':  r.subscribers,
            'avgWinRate':   float(r.avg_win_rate) if r.avg_win_rate else None,
            'avgPnl':       float(r.avg_pnl) if r.avg_pnl else None,
            'publishedAt':  r.published_at.isoformat() if r.published_at else None,
            'authorName':   r.author_name,
            'strategyType': r.strategy_type,
            'timeframe':    r.timeframe,
            'isSubscribed': r.is_subscribed,
        }
        for r in rows
    ]}), 200


@marketplace_bp.route('/publish', methods=['POST'])
@auth_required
def publish():
    data        = request.get_json() or {}
    strategy_id = data.get('strategyId')
    title       = (data.get('title') or '').strip()
    description = (data.get('description') or '').strip()
    category    = (data.get('category') or 'general').strip()

    if not strategy_id or not title:
        return jsonify({'error': 'strategyId and title are required'}), 400

    engine = get_engine()
    with engine.connect() as conn:
        strat = conn.execute(
            text("SELECT id FROM user_strategies WHERE id = :id AND user_id = :uid"),
            {'id': strategy_id, 'uid': request.user_id}
        ).fetchone()

    if not strat:
        return jsonify({'error': 'Strategy not found'}), 404

    # Get best backtest results for this strategy
    with engine.connect() as conn:
        best = conn.execute(
            text("""
                SELECT
                    MAX((results->'summary'->>'winRate')::float) AS best_wr,
                    MAX((results->'summary'->>'totalPnL')::float) AS best_pnl
                FROM backtest_runs
                WHERE strategy_id = :sid AND status = 'completed' AND user_id = :uid
            """),
            {'sid': strategy_id, 'uid': request.user_id}
        ).fetchone()

    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT id FROM marketplace_strategies WHERE strategy_id = :sid AND user_id = :uid"),
            {'sid': strategy_id, 'uid': request.user_id}
        ).fetchone()

        if existing:
            conn.execute(
                text("""
                    UPDATE marketplace_strategies
                    SET title = :title, description = :desc, category = :cat,
                        avg_win_rate = :wr, avg_pnl = :pnl, is_published = TRUE,
                        published_at = NOW()
                    WHERE id = :id
                """),
                {'title': title, 'desc': description, 'cat': category,
                 'wr': best.best_wr, 'pnl': best.best_pnl, 'id': existing.id}
            )
            pub_id = existing.id
        else:
            row = conn.execute(
                text("""
                    INSERT INTO marketplace_strategies
                        (user_id, strategy_id, title, description, category, avg_win_rate, avg_pnl)
                    VALUES (:uid, :sid, :title, :desc, :cat, :wr, :pnl)
                    RETURNING id
                """),
                {'uid': request.user_id, 'sid': strategy_id,
                 'title': title, 'desc': description, 'cat': category,
                 'wr': best.best_wr, 'pnl': best.best_pnl}
            ).fetchone()
            pub_id = row.id

    return jsonify({'id': pub_id, 'message': 'Strategy published'}), 201


@marketplace_bp.route('/<int:marketplace_id>/subscribe', methods=['POST'])
@auth_required
def subscribe(marketplace_id):
    engine = get_engine()
    with engine.connect() as conn:
        ms = conn.execute(
            text("SELECT strategy_id, title FROM marketplace_strategies WHERE id = :id AND is_published = TRUE"),
            {'id': marketplace_id}
        ).fetchone()

    if not ms:
        return jsonify({'error': 'Strategy not found'}), 404

    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT id FROM marketplace_subscriptions WHERE user_id = :uid AND marketplace_strategy_id = :mid"),
            {'uid': request.user_id, 'mid': marketplace_id}
        ).fetchone()

        if existing:
            return jsonify({'message': 'Already subscribed'}), 200

        # Copy the strategy to user's account
        original = conn.execute(
            text("SELECT * FROM user_strategies WHERE id = :id"),
            {'id': ms.strategy_id}
        ).fetchone()

        conn.execute(
            text("""
                INSERT INTO user_strategies
                    (user_id, name, description, strategy_type, parameters, timeframe)
                VALUES (:uid, :name, :desc, :stype, CAST(:params AS jsonb), :tf)
            """),
            {
                'uid': request.user_id,
                'name': f'{ms.title} (from Marketplace)',
                'desc': f'Subscribed from marketplace strategy #{marketplace_id}',
                'stype': original.strategy_type,
                'params': __import__('json').dumps(original.parameters or {}),
                'tf': original.timeframe,
            }
        )

        conn.execute(
            text("INSERT INTO marketplace_subscriptions (user_id, marketplace_strategy_id) VALUES (:uid, :mid)"),
            {'uid': request.user_id, 'mid': marketplace_id}
        )
        conn.execute(
            text("UPDATE marketplace_strategies SET subscribers = subscribers + 1 WHERE id = :id"),
            {'id': marketplace_id}
        )

    return jsonify({'message': 'Strategy added to your account'}), 200


@marketplace_bp.route('/<int:marketplace_id>/unpublish', methods=['POST'])
@auth_required
def unpublish(marketplace_id):
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE marketplace_strategies SET is_published = FALSE
                WHERE id = :id AND user_id = :uid
            """),
            {'id': marketplace_id, 'uid': request.user_id}
        )
    return jsonify({'message': 'Strategy unpublished'}), 200


@marketplace_bp.route('/mine', methods=['GET'])
@auth_required
def my_published():
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT ms.id, ms.title, ms.description, ms.category,
                       ms.subscribers, ms.avg_win_rate, ms.avg_pnl,
                       ms.is_published, ms.published_at,
                       us.name AS strategy_name
                FROM marketplace_strategies ms
                JOIN user_strategies us ON us.id = ms.strategy_id
                WHERE ms.user_id = :uid
                ORDER BY ms.published_at DESC
            """),
            {'uid': request.user_id}
        ).fetchall()

    return jsonify({'strategies': [
        {
            'id':           r.id, 'title': r.title,
            'description':  r.description, 'category': r.category,
            'subscribers':  r.subscribers,
            'avgWinRate':   float(r.avg_win_rate) if r.avg_win_rate else None,
            'avgPnl':       float(r.avg_pnl) if r.avg_pnl else None,
            'isPublished':  r.is_published,
            'publishedAt':  r.published_at.isoformat() if r.published_at else None,
            'strategyName': r.strategy_name,
        }
        for r in rows
    ]}), 200
